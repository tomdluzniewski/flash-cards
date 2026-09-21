---
name: vocab
description: Z transkrypcji lub dowolnego tekstu po angielsku wybiera słówka i sformułowania warte nauki, dopisuje je do wskazanej bazy w data/<baza>.txt i pobiera wymowę (pron.py). Użycie - /vocab <baza> <ścieżka do pliku z tekstem> albo /vocab <baza> i tekst wklejony w wiadomości.
argument-hint: <baza> [ścieżka-do-transkrypcji]
---

# /vocab — transkrypcja → baza słówek

Argumenty: `$ARGUMENTS` (pierwszy token = nazwa bazy, reszta = opcjonalna ścieżka do pliku z tekstem;
jeśli ścieżki nie ma, tekst jest wklejony w wiadomości użytkownika).

## Kroki

1. **Wczytaj kontekst.**
   - `data/<baza>.txt` — jeśli istnieje, wczytaj w całości: będziesz unikać duplikatów (porównuj po stronie angielskiej,
     bez rozróżniania wielkości liter i bez wiodącego `to`/`a`/`an`/`the`). Jeśli nie istnieje, utwórz go z nagłówkiem
     `# Baza: <baza> — ...` i linią z formatem (wzoruj się na `data/msnbc.txt`).
   - Tekst źródłowy (plik lub treść wiadomości). Może być zaśmiecony znacznikami czasu z YouTube (`0:088 sekund…`) — ignoruj je.

2. **Wybierz materiał do nauki.** Zwykle 60–150 pozycji na ~30 minut transkrypcji. Bierz:
   - idiomy i wyrażenia potoczne (`to skip town`, `it doesn't pass the smell test`, `small potatoes`),
   - czasowniki frazowe i kolokacje (`to double down`, `to rack up`, `to take a toll on someone`),
   - słownictwo tematyczne wymagające zapamiętania (polityka, prawo, wojsko, gospodarka…),
   - typowe zwroty konwersacyjne / telewizyjne (`joining me now is`, `where's your head at on this`).
   Pomijaj słowa, które użytkownik na pewno zna (podstawowe słownictwo) oraz nazwy własne.
   Popraw literówki z automatycznej transkrypcji (np. `Hegsth` → to nazwisko, pomiń; `alumnest` → `an alumnus`).

3. **Format wpisów** — jedna para w linii: `po polsku ; in English`
   - czasowniki w bezokoliczniku z `to` (`pozwać ; to sue`), rzeczowniki policzalne z `a/an` (`urzędujący (polityk) ; an incumbent`),
   - kilka poprawnych odpowiedzi rozdziel ukośnikiem: `skrajnie republikański stan ; a ruby red state / a deep red state`,
   - gdy polskie tłumaczenie jest wieloznaczne, dodaj podpowiedź w nawiasie po polskiej stronie,
   - żadnych średników w części polskiej i żadnych ukośników w części angielskiej poza rozdzielaniem wariantów,
   - polskie tłumaczenie ma być naturalne (tak, jak powiedziałby to Polak), nie dosłowne.

4. **Dopisz do bazy** na końcu pliku blok:
   ```
   # ===== RRRR-MM-DD: krótki opis tematu/odcinka =====
   # --- podtemat 1 ---
   ...
   # --- podtemat 2 ---
   ...
   ```
   Użyj dzisiejszej daty; pogrupuj tematycznie w 2–4 podsekcje.

5. **Zweryfikuj**: `python3 -c "import server; w=server.load_words('<baza>'); print(len(w))"` oraz sprawdź brak duplikatów
   po stronie angielskiej w całym pliku (`collections.Counter`). Usuń duplikaty, które sam dodałeś.

6. **Pobierz wymowę**: `python3 pron.py <baza>` (IPA + mp3 dla pojedynczych słów; zwroty czyta synteza mowy w przeglądarce).
   Trwa ok. 0,5–1 s na słowo — uruchom w tle, jeśli słów jest dużo.

7. **Podsumuj** w 3–5 zdaniach: ile pozycji dodano, ile pominięto jako duplikaty, ile słów ma nagranie, i podaj kilka
   przykładów najciekawszych zwrotów. Nie wklejaj całej listy.
