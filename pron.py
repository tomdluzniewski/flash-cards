#!/usr/bin/env python3
"""Pobiera wymowę (IPA + nagranie mp3) dla pojedynczych słów z bazy.

Użycie:  python3 pron.py <baza> [--force]

Źródła:
  1. pojedyncze słowa – Wiktionary (IPA) + Wikimedia Commons (nagranie lektora, mp3);
     preferowany akcent brytyjski (RP / UK), w razie braku amerykański, potem dowolny;
  2. zwroty oraz słowa, dla których nie ma nagrania lektora – Google TTS (głos en-GB).

Wynik:   data/<baza>.pron.json  – { "to sue": {"word": "sue", "ipa": "/suː/", "audio": "audio/sue.mp3"},
                                    "to skip town": {"audio": "audio/tts/to-skip-town.mp3", "tts": true}, ... }
         data/audio/<słowo>.mp3      – nagrania lektora (współdzielone między bazami)
         data/audio/tts/<zwrot>.mp3  – nagrania syntezatora
Wpisy bez żadnego audio zapisywane są jako {"missing": true}; --force odpytuje wszystko od nowa.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import DATA_DIR, load_words  # noqa: E402

AUDIO_DIR = os.path.join(DATA_DIR, "audio")
TTS_DIR = os.path.join(AUDIO_DIR, "tts")
TTS_URL = "https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en-GB&q="
UA = "memorize-vocab/1.0 (local language-learning app; python-urllib)"
DELAY = 1.5  # odstęp między zapytaniami do Wikimedia
UK_TAGS = ("RP", "UK", "GB", "British", "England", "Received")
US_TAGS = ("GA", "US", "GenAm", "American")


class RateLimited(Exception):
    pass


def get(url, binary=False, tries=4):
    """GET z ponawianiem po HTTP 429 (limit Wikimedia). Po wyczerpaniu prób rzuca RateLimited."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            time.sleep(DELAY)
            return data if binary else json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = 20 * (i + 1)
            print(f"    (limit zapytań, czekam {wait}s)")
            time.sleep(wait)
    raise RateLimited(url)


def headword(variant):
    """'to sue' -> 'sue', 'an incumbent' -> 'incumbent'; zwroty wielowyrazowe -> None."""
    w = variant.strip().lower()
    w = re.sub(r"^(to|a|an|the)\s+", "", w)
    w = re.sub(r"[.!?,]+$", "", w).strip()
    if re.fullmatch(r"[a-z][a-z'\-]*", w):
        return w
    return None


def base_forms(word):
    """Formy do sprawdzenia, gdy hasła brak: liczba mnoga, -ed, -ing, -ly → forma podstawowa."""
    forms = [word]
    if word.endswith("ies"):
        forms.append(word[:-3] + "y")
    if word.endswith("es"):
        forms.append(word[:-2])
    if word.endswith("s"):
        forms.append(word[:-1])
    if word.endswith("ed"):
        forms += [word[:-2], word[:-1], word[:-3]]
    if word.endswith("ing"):
        forms += [word[:-3], word[:-3] + "e"]
    if word.endswith("ly"):
        forms.append(word[:-2])
    return list(dict.fromkeys(f for f in forms if len(f) > 2))


def english_pron_section(wikitext):
    i = wikitext.find("==English==")
    if i < 0:
        return ""
    sec = wikitext[i:]
    m = re.search(r"\n==[^=]", sec)
    if m:
        sec = sec[:m.start()]
    return sec


def rank(accent, tags_pref):
    """0 = preferowany akcent, 1 = drugi wybór, 2 = reszta."""
    for score, tags in enumerate(tags_pref):
        if any(t.lower() in accent.lower() for t in tags):
            return score
    return len(tags_pref)


def parse_pron(section):
    ipas, audios = [], []
    for m in re.finditer(r"\{\{IPA\|en\|([^}]*)\}\}", section):
        parts = m.group(1).split("|")
        accent = next((p[2:] for p in parts if p.startswith("a=")), "")
        texts = [p for p in parts if p.startswith("/") or p.startswith("[")]
        if texts:
            ipas.append((rank(accent, (UK_TAGS, US_TAGS)), texts[0]))
    for m in re.finditer(r"\{\{audio\|en\|([^}]*)\}\}", section):
        parts = m.group(1).split("|")
        accent = next((p[2:] for p in parts if p.startswith("a=")), "")
        fname = parts[0].strip()
        # pliki bez tagu: zgadnij akcent z nazwy (En-uk-..., En-us-...)
        if not accent:
            accent = "UK" if re.match(r"(?i)en-uk", fname) else "US" if re.match(r"(?i)en-us", fname) else ""
        audios.append((rank(accent, (UK_TAGS, US_TAGS)), fname))
    ipas.sort(key=lambda x: x[0])
    audios.sort(key=lambda x: x[0])
    return (ipas[0][1] if ipas else None), (audios[0][1] if audios else None)


def wiktionary(word):
    """Zwraca (ipa, plik_audio); (None, None) gdy hasła nie ma. Błędy sieci propaguje."""
    url = ("https://en.wiktionary.org/w/api.php?action=parse&prop=wikitext&format=json&formatversion=2&page="
           + urllib.parse.quote(word))
    d = get(url)
    if "parse" not in d:
        return None, None
    return parse_pron(english_pron_section(d["parse"]["wikitext"]))


def commons_mp3_url(fname):
    url = ("https://commons.wikimedia.org/w/api.php?action=query&prop=videoinfo&viprop=url|derivatives"
           "&format=json&formatversion=2&titles=" + urllib.parse.quote("File:" + fname))
    d = get(url)
    try:
        vi = d["query"]["pages"][0]["videoinfo"][0]
    except (KeyError, IndexError):
        return None
    for dv in vi.get("derivatives", []):
        if dv.get("type", "").startswith("audio/mpeg"):
            return dv["src"]
    if fname.lower().endswith(".mp3"):
        return vi.get("url")
    return None


def download(url, tries=3):
    """Commons transkoduje mp3 na żądanie – pierwsza próba bywa 404, więc ponawiamy."""
    for i in range(tries):
        try:
            data = get(url, binary=True)
            if data:
                return data
        except RateLimited:
            raise
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80] or "x"


def google_tts(text):
    """Pobiera mp3 z syntezatora Google (en-GB). Zwraca ścieżkę względem data/ lub None."""
    path = os.path.join(TTS_DIR, slug(text) + ".mp3")
    if not os.path.exists(path):
        req = urllib.request.Request(TTS_URL + urllib.parse.quote(text), headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
        except Exception:
            return None
        if not data or not r.headers.get("Content-Type", "").startswith("audio"):
            return None
        with open(path, "wb") as f:
            f.write(data)
        time.sleep(0.5)
    return "audio/tts/" + os.path.basename(path)


def wiktionary_entry(v, word):
    """Nagranie lektora + IPA z Wiktionary dla pojedynczego słowa. Zwraca słownik (może być pusty)."""
    entry = {}
    ipa = audio_file = None
    for form in base_forms(word):
        ipa, audio_file = wiktionary(form)
        if ipa or audio_file:
            word = form
            break
    if not (ipa or audio_file):
        return entry
    entry["word"] = word
    if word != headword(v):
        entry["base"] = word  # wymowa formy podstawowej (np. deployed → deploy)
    if ipa:
        entry["ipa"] = ipa
    if audio_file:
        mp3_path = os.path.join(AUDIO_DIR, word + ".mp3")
        if not os.path.exists(mp3_path):
            try:
                src = commons_mp3_url(audio_file)
                data = download(src) if src else None
            except RateLimited:
                raise
            except Exception:
                data = None
            if data:
                with open(mp3_path, "wb") as f:
                    f.write(data)
        if os.path.exists(mp3_path):
            entry["audio"] = "audio/" + word + ".mp3"
    return entry


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    name = args[0]
    words = load_words(name)
    os.makedirs(TTS_DIR, exist_ok=True)
    pron_path = os.path.join(DATA_DIR, name + ".pron.json")
    pron = {}
    if os.path.exists(pron_path) and not force:
        with open(pron_path, encoding="utf-8") as f:
            pron = json.load(f)

    variants = []
    for w in words:
        for v in w["en"].split("/"):
            v = v.strip()
            prev = pron.get(v)
            if v and not (prev and (prev.get("audio") or prev.get("missing"))):
                variants.append(v)
    variants = list(dict.fromkeys(variants))
    print(f"{name}: {len(variants)} nowych wpisów do sprawdzenia")

    limited = False
    for i, v in enumerate(variants, 1):
        word = headword(v)
        entry = dict(pron.get(v) or {})
        if word and not limited:
            try:
                entry.update(wiktionary_entry(v, word))
            except RateLimited:
                limited = True
                print("  Wikimedia odrzuca zapytania – słowa bez nagrania lektora dostaną na razie syntezator;"
                      " uruchom skrypt ponownie za kilka minut.")
            except Exception as e:
                print(f"    (błąd Wiktionary: {e})")
        if "audio" not in entry:
            tts = google_tts(v)
            if tts:
                entry["audio"] = tts
                entry["tts"] = True
        if "audio" not in entry and "ipa" not in entry:
            entry = {"missing": True}
        pron[v] = entry
        status = ("🔊 " if entry.get("audio") and not entry.get("tts") else "🤖 " if entry.get("tts") else "   ") \
                 + (entry.get("ipa") or "")
        print(f"  [{i}/{len(variants)}] {v:45s} {status}")
        with open(pron_path, "w", encoding="utf-8") as f:
            json.dump(pron, f, ensure_ascii=False, indent=1, sort_keys=True)

    native = sum(1 for e in pron.values() if e.get("audio") and not e.get("tts"))
    tts = sum(1 for e in pron.values() if e.get("tts"))
    missing = sum(1 for e in pron.values() if e.get("missing"))
    print(f"Gotowe: {native} nagrań lektora, {tts} z syntezatora, {missing} bez audio ({os.path.relpath(pron_path)})")


if __name__ == "__main__":
    main()
