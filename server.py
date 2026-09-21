#!/usr/bin/env python3
"""Prosty serwer do nauki słówek oparty na plikach płaskich.

Bazy słówek: data/<nazwa>.txt   — jedna para na linię: "polski ; english"
Statystyki:  data/<nazwa>.stats.json — liczba złych/dobrych odpowiedzi na słowo
"""
import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")


def parse_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    sep = "\t" if "\t" in line else ";"
    if sep not in line:
        return None
    pl, en = line.split(sep, 1)
    pl, en = pl.strip(), en.strip()
    if not pl or not en:
        return None
    return pl, en


def load_words(name):
    with open(os.path.join(DATA_DIR, name + ".txt"), encoding="utf-8") as f:
        pairs = [p for p in (parse_line(l) for l in f) if p]
    return [{"pl": pl, "en": en} for pl, en in pairs]


def stats_path(name):
    return os.path.join(DATA_DIR, name + ".stats.json")


def load_stats(name):
    try:
        with open(stats_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_stats(name, stats):
    tmp = stats_path(name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, stats_path(name))


def load_pron(name):
    try:
        with open(os.path.join(DATA_DIR, name + ".pron.json"), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def list_dbs():
    dbs = []
    for fn in sorted(os.listdir(DATA_DIR)):
        if fn.endswith(".txt"):
            name = fn[:-4]
            dbs.append({"name": name, "count": len(load_words(name))})
    return dbs


def safe_name(name):
    name = unquote(name)
    if not name or "/" in name or ".." in name:
        return None
    if not os.path.isfile(os.path.join(DATA_DIR, name + ".txt")):
        return None
    return name


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"
            return super().do_GET()
        if self.path == "/api/dbs":
            return self.send_json(list_dbs())
        if self.path.startswith("/api/db/"):
            name = safe_name(self.path[len("/api/db/"):])
            if not name:
                return self.send_json({"error": "not found"}, 404)
            stats = load_stats(name)
            pron = load_pron(name)
            words = load_words(name)
            for w in words:
                s = stats.get(w["pl"] + " ; " + w["en"], {})
                w["wrong"] = s.get("wrong", 0)
                w["correct"] = s.get("correct", 0)
                # wymowa pierwszego wariantu odpowiedzi, dla którego ją mamy
                for v in w["en"].split("/"):
                    p = pron.get(v.strip())
                    if p and not p.get("missing"):
                        w["ipa"] = (p.get("ipa") or "") + (f" ({p['base']})" if p.get("base") else "")
                        w["audio"] = "/data/" + p["audio"] if p.get("audio") else None
                        break
            return self.send_json({"name": name, "words": words})
        if self.path.startswith("/api/"):
            return self.send_json({"error": "not found"}, 404)
        return super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self.send_json({"error": "bad json"}, 400)

        if self.path.startswith("/api/db/") and self.path.endswith("/answer"):
            name = safe_name(self.path[len("/api/db/"):-len("/answer")])
            if not name:
                return self.send_json({"error": "not found"}, 404)
            key = str(payload.get("pl", "")) + " ; " + str(payload.get("en", ""))
            stats = load_stats(name)
            entry = stats.setdefault(key, {"wrong": 0, "correct": 0})
            entry["correct" if payload.get("ok") else "wrong"] += 1
            save_stats(name, stats)
            return self.send_json(entry)

        if self.path.startswith("/api/db/") and self.path.endswith("/reset"):
            name = safe_name(self.path[len("/api/db/"):-len("/reset")])
            if not name:
                return self.send_json({"error": "not found"}, 404)
            save_stats(name, {})
            return self.send_json({"ok": True})

        return self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Memorize: http://localhost:{PORT}  (bazy w {DATA_DIR})")
    try:
        HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
