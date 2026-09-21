# Memorize

Prosta strona do nauki słówek i zwrotów angielskich, oparta na plikach płaskich.

## Uruchomienie

    python3 server.py          # domyślnie port 8000
    python3 server.py 9000     # inny port

Potem otwórz http://localhost:8000

## Bazy słówek

Każda baza to plik `data/<nazwa>.txt`, jedna para w linii:

    po polsku ; in English

- separator: `;` (albo tabulator),
- linie puste i zaczynające się od `#` są pomijane,
- kilka poprawnych odpowiedzi rozdziel ukośnikiem: `samochód ; car / automobile`.

Statystyki (ile razy dane słowo poszło źle/dobrze) trafiają do `data/<nazwa>.stats.json`.
Słowa z większą liczbą pomyłek losowane są częściej; można je wyzerować z ekranu wyboru bazy.

## Wymowa

    python3 pron.py <baza>

pobiera nagrania (mp3, akcent brytyjski) dla wszystkich odpowiedzi w bazie:
- pojedyncze słowa (`to sue` → `sue`, `an incumbent` → `incumbent`) – nagranie lektora i zapis IPA z Wiktionary,
- zwroty i słowa bez nagrania lektora – syntezator Google (en-GB).

Wynik ląduje w `data/<baza>.pron.json`, `data/audio/*.mp3` (lektor) i `data/audio/tts/*.mp3` (syntezator).
Skrypt pyta tylko o nowe wpisy; `--force` odpytuje wszystko od nowa.

Po odsłonięciu odpowiedzi nagranie gra od razu; przycisk 🔊 (klawisz `P`) powtarza je. Gdy nagrania nie ma
(np. słowo dodane do bazy przed uruchomieniem `pron.py`), czyta synteza mowy przeglądarki głosem en-GB –
na macOS warto pobrać głos „Daniel (Enhanced)” w Ustawienia → Dostępność → Treść mówiona.

## Rozszerzanie bazy z transkrypcji (Claude Code)

    /vocab msnbc ~/Downloads/transkrypcja.txt

Skill `.claude/skills/vocab` wybiera z tekstu idiomy, kolokacje i słownictwo, dopisuje blok z datą na koniec
`data/msnbc.txt` (pomijając duplikaty) i uruchamia `pron.py`.

## Tryby

- **Przełącznik „W myślach” wyłączony** — wpisujesz odpowiedź, `Enter` sprawdza (bez rozróżniania wielkości liter),
  program pokazuje poprawną odpowiedź i sam ocenia; `Enter` zatwierdza ocenę, a przyciskami ✓/✗ możesz ją zmienić
  (np. przy literówce).
- **Przełącznik włączony** — `Enter` pokazuje odpowiedź, potem `Enter` = dobrze, `N` = źle (lub przyciski ✓/✗).
- `P` — odtwórz wymowę pokazanej odpowiedzi.
