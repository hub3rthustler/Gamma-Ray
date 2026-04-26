# SECURITY.md

## Zgłaszanie problemów

Jeżeli znajdziesz błąd bezpieczeństwa w projekcie, zgłoś go prywatnie właścicielowi repozytorium zamiast publikować gotowy exploit.

## Zakres

Projekt:

- nie łączy się z siecią,
- nie pobiera danych z zewnętrznych usług,
- nie uruchamia Hashcat,
- nie łamie hashy,
- zapisuje wyłącznie lokalny plik tekstowy z kandydaturami.

## Zalecenia

- Nie przechowuj realnych profili w repozytorium.
- Dodaj katalog `out/` do `.gitignore`.
- Dla audytów firmowych trzymaj dane wejściowe w bezpiecznej lokalizacji.
