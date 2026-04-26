# 🇵🇱 Gamma Ray

> Estetyczny, prosty i defensywny generator spersonalizowanych wordlist po polsku — inspirowany ideą Mentalist, ale napisany od zera w Pythonie i przygotowany pod portfolio/CV.

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-blue">
  <img alt="Hashcat compatible" src="https://img.shields.io/badge/Hashcat-wordlist%20ready-orange">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
  <img alt="Ethical use" src="https://img.shields.io/badge/Use-defensive%20only-brightgreen">
</p>

## ✨ Co to robi?

**Gamma Ray** generuje kandydatury haseł na podstawie profilu osoby, organizacji lub konta, które masz prawo audytować. Program tworzy warianty z polskimi znakami, transliteracją ASCII, zmianą wielkości liter, separatorami, datami, latami, liczbami i prostymi mutacjami typu `a -> @`.

Wynik jest zapisywany jako zwykły plik tekstowy: **jedna kandydatura na jedną linię**, czyli format przyjazny dla narzędzi typu Hashcat.

## 🧭 Zastosowania zgodne z prawem

Nie używaj tego projektu do atakowania cudzych kont, usług, skrzynek pocztowych, sieci ani hashy, do których nie masz upoważnienia.

## 🚀 Szybki start

Uruchom bez argumentów dla interfejsu graficznego:

```bash
python3 gamma_ray.py
```

Lub użyj linii komend:

```bash
python3 gamma_ray.py \
  --profile config/sample_profile.json \
  --output out/wordlist.txt \
  --min-len 6 \
  --max-len 16 \
  --max-count 50000
```

Podgląd pierwszych wyników:

```bash
head -n 20 out/wordlist.txt
```

## 🧩 Przykładowy profil

Plik wejściowy to zwykły JSON:

```json
{
  "names": ["Jan", "Janek"],
  "surnames": ["Kowalski"],
  "nicknames": ["jkowal"],
  "cities": ["Kraków"],
  "pets": ["Burek"],
  "hobbies": ["rower", "gitara"],
  "keywords": ["firma", "projekt"],
  "dates": ["1998-04-12", "12.04.1998"],
  "years": ["1998", "2024", "2025"],
  "numbers": ["123", "321"],
  "symbols": ["!", "@", "#"]
}
```

## � Szczegółowe wymagania dla pliku wejściowego

Plik wejściowy musi być prawidłowym plikiem JSON zawierającym obiekt (słownik) z kluczami, których wartościami są tablice stringów. Wszystkie pola są **opcjonalne**, ale dla generowania sensownych wyników zaleca się wypełnienie przynajmniej kilku pól.

### Obsługiwane klucze i ich formaty:

- **`names`**: Tablica stringów zawierających imiona lub imiona. Przykład: `["Jan", "Anna"]`.
- **`surnames`**: Tablica stringów zawierających nazwiska. Przykład: `["Kowalski", "Nowak"]`.
- **`nicknames`**: Tablica stringów zawierających pseudonimy, nicki lub nazwy użytkowników. Przykład: `["jkowal", "anna123"]`.
- **`cities`**: Tablica stringów zawierających nazwy miast lub miejsc. Przykład: `["Kraków", "Warszawa"]`.
- **`pets`**: Tablica stringów zawierających imiona zwierząt domowych. Przykład: `["Burek", "Mruczek"]`.
- **`hobbies`**: Tablica stringów zawierających hobby lub zainteresowania. Przykład: `["rower", "gitara", "programowanie"]`.
- **`keywords`**: Tablica stringów zawierających słowa kluczowe związane z osobą lub organizacją. Przykład: `["firma", "projekt", "szkoła"]`.
- **`dates`**: Tablica stringów zawierających daty w formatach `YYYY-MM-DD` (np. `"1998-04-12"`) lub `DD.MM.YYYY` (np. `"12.04.1998"`). Program automatycznie rozpozna i przetworzy te formaty.
- **`years`**: Tablica stringów zawierających lata jako czterocyfrowe liczby. Przykład: `["1998", "2024"]`.
- **`numbers`**: Tablica stringów zawierających liczby lub sekwencje cyfr, które mogą być częścią haseł. Przykład: `["123", "456", "007"]`.
- **`symbols`**: Tablica stringów zawierających symbole lub znaki specjalne do dodania do haseł. Przykład: `["!", "@", "#", "$"]`.

### Dodatkowe uwagi:

- **Wielkość liter**: Program automatycznie generuje warianty wielkości liter dla wszystkich tokenów, więc nie musisz się martwić o to w pliku wejściowym.
- **Polskie znaki**: Jeśli używasz polskich znaków (np. `ą`, `ć`, `ę`), program może generować warianty z transliteracją ASCII (np. `Krakow` zamiast `Kraków`) oraz oryginalne wersje UTF-8, w zależności od opcji.
- **Puste wartości**: Puste stringi (`""`) lub null wartości są ignorowane podczas przetwarzania.
- **Duplikaty**: Program automatycznie usuwa duplikaty z wyników, więc nie musisz się martwić o powtarzające się wartości w tablicach.
- **Rozmiar pliku**: Plik JSON powinien być rozsądnie mały (kilka KB), ponieważ jest wczytywany do pamięci.

Jeśli plik wejściowy nie jest prawidłowym JSON lub zawiera nieobsługiwane typy danych (np. liczby zamiast stringów w tablicach), program wyświetli błąd i zakończy działanie.

Uruchom `python3 gamma_ray.py` bez argumentów, aby otworzyć interfejs graficzny.

Opcje linii komend:

```text
--profile PATH          ścieżka do profilu JSON
--word TEXT             dodatkowe słowo bazowe; można podać wiele razy
--output PATH           plik wynikowy
--min-len N             minimalna długość kandydatury
--max-len N             maksymalna długość kandydatury
--max-count N           limit liczby kandydatur
--separators LIST       separatory, np. "",.,_,-
--ascii-only            wymuś wyłącznie warianty ASCII
--include-unicode       dołącz warianty z polskimi znakami UTF-8
--leet                  włącz proste zamiany typu a->@, e->3
--depth 1|2             głębokość łączenia tokenów
--crlf                  zapisuj linie w stylu Windows CRLF
--quiet                 mniej komunikatów
```

## 🧠 Jak działa generator?

Pipeline:

1. Wczytanie profilu JSON i słów z CLI.
2. Czyszczenie pustych wartości oraz duplikatów.
3. Normalizacja polskich znaków, np. `Kraków -> Krakow`.
4. Tworzenie wariantów wielkości liter: `jan`, `Jan`, `JAN`.
5. Łączenie tokenów separatorami: `jan1998`, `jan_1998`, `Jan!`.
6. Opcjonalne mutacje leet.
7. Filtrowanie po długości.
8. Deduplicacja z zachowaniem kolejności.
9. Zapis do pliku kompatybilnego z użyciem jako wordlista.

## 🧪 Test

```bash
python3 -m unittest discover -s tests
```

## 📁 Struktura projektu

```text
gamma_ray/
├── gamma_ray.py
├── config/
│   └── sample_profile.json
├── tests/
│   └── test_generator.py
├── README.md
├── ETHICS.md
├── SECURITY.md
├── requirements.txt
├── pyproject.toml
├── .gitignore
└── LICENSE
```

## 🛡️ Ograniczenia i dobre praktyki

- Używaj możliwie małych, trafnych profili — duże listy szybko rosną kombinatorycznie.
- Nie wrzucaj do repo prywatnych danych osób, klientów ani wynikowych wordlist.
- Do portfolio używaj fikcyjnego profilu demonstracyjnego.
- Dla realnych audytów przechowuj dane wejściowe poza repozytorium.

## 🗺️ Roadmap

- [x] interfejs graficzny (GUI)
- [ ] eksport statystyk do JSON,
- [ ] tryb interaktywny TUI,
- [ ] profile branżowe dla audytu firmowego,
- [ ] generowanie reguł Hashcat `.rule`,
- [ ] integracja z pipeline CI do testów jakości słownika.

## 📄 Licencja

MIT — patrz plik [`LICENSE`](LICENSE).
