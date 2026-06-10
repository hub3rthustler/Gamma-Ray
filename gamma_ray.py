#!/usr/bin/env python3
"""
Gamma Ray - generator spersonalizowanych wordlist po polsku.

"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


POLISH_ASCII_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ź": "z", "ż": "z",
    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N",
    "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
})

PROFILE_FIELDS = (
    "names", "surnames", "nicknames", "cities", "pets",
    "companies", "hobbies", "teams", "schools", "keywords",
    "dates", "years", "numbers", "symbols",
)

LEET_TABLE = {
    # Podstawowe substytucje (ASCII)
    "a": ("@", "4"),
    "e": ("3",),
    "i": ("1", "!"),
    "l": ("1",),
    "o": ("0",),
    "s": ("5", "$"),
    "t": ("7",),
    "z": ("2",),
    # Polskie litery — transliteracja + leet
    "ą": ("@", "a"),   # ą → @ lub zwykłe a
    "ć": ("c",),       # ć → c
    "ę": ("3", "e"),   # ę → 3 lub e
    "ł": ("l", "1"),   # ł → l lub 1
    "ń": ("n",),       # ń → n
    "ó": ("0", "o"),   # ó → 0 lub o
    "ś": ("5", "s"),   # ś → 5 lub s
    "ź": ("2", "z"),   # ź → 2 lub z
    "ż": ("2", "z"),   # ż → 2 lub z
}


@dataclass(frozen=True)
class Options:
    min_len: int
    max_len: int
    max_count: int
    separators: tuple[str, ...]
    ascii_only: bool
    include_unicode: bool
    leet_level: str
    depth: int


def dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def normalize_space(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value


def compact_token(value: str) -> str:
    value = normalize_space(value)
    return re.sub(r"[\s/\\:;,'\"`]+", "", value)


def ascii_fold(value: str) -> str:
    return value.translate(POLISH_ASCII_MAP)


def case_variants(value: str) -> Iterator[str]:
    if not value:
        return
    yield value
    yield value.lower()
    yield value.upper()
    yield value.capitalize()
    if len(value) > 1:
        yield value[0].upper() + value[1:].lower()


MONTH_VARIANTS: dict[str, tuple[str, ...]] = {
    "01": ("styczen", "styczeń", "stycznia", "sty"),
    "02": ("luty", "lutego", "lut"),
    "03": ("marzec", "marca", "mar"),
    "04": ("kwiecien", "kwiecień", "kwietnia", "kwi"),
    "05": ("maj", "maja"),
    "06": ("czerwiec", "czerwca", "cze"),
    "07": ("lipiec", "lipca", "lip"),
    "08": ("sierpien", "sierpień", "sierpnia", "sie"),
    "09": ("wrzesien", "wrzesień", "wrzesnia", "września", "wrz"),
    "10": ("pazdziernik", "październik", "pazdziernika", "października", "paz", "paź"),
    "11": ("listopad", "listopada", "lis"),
    "12": ("grudzien", "grudzień", "grudnia", "gru"),
}


def _looks_like_date_parts(dd: str, mm: str, yyyy: str) -> bool:
    try:
        day = int(dd)
        month = int(mm)
        year = int(yyyy)
    except ValueError:
        return False
    return 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2099


def _date_candidates_from_parts(dd: str, mm: str, yyyy: str) -> Iterator[str]:
    if not _looks_like_date_parts(dd, mm, yyyy):
        return

    yy = yyyy[-2:]

    # Compact numeric variants.
    for candidate in (
        yyyy, yy,
        dd + mm + yyyy, dd + mm + yy,
        yyyy + mm + dd, yy + mm + dd,
        dd + mm, mm + yyyy, mm + yy,
    ):
        yield candidate

    # Numeric variants with common separators.
    for sep in (".", "-", "_"):
        yield sep.join((dd, mm, yyyy))
        yield sep.join((dd, mm, yy))
        yield sep.join((yyyy, mm, dd))
        yield sep.join((yy, mm, dd))

    # Polish month-name variants, useful for Polish personal wordlists.
    for month_name in MONTH_VARIANTS.get(mm, ()):
        yield f"{dd}{month_name}{yyyy}"
        yield f"{dd}{month_name}{yy}"
        yield f"{month_name}{yyyy}"
        yield f"{month_name}{yy}"
        yield f"{dd}_{month_name}_{yyyy}"
        yield f"{dd}-{month_name}-{yyyy}"


def date_variants(value: str) -> Iterator[str]:
    raw = normalize_space(value)
    if not raw:
        return

    compact = re.sub(r"\D+", "", raw)
    if compact:
        yield compact

    # YYYYMMDD or DDMMYYYY -> expanded numeric and Polish month variants.
    if re.fullmatch(r"\d{8}", compact):
        if compact[:2] in {"19", "20"}:
            yyyy, mm, dd = compact[:4], compact[4:6], compact[6:8]
        else:
            dd, mm, yyyy = compact[:2], compact[2:4], compact[4:8]
        yield from _date_candidates_from_parts(dd, mm, yyyy)

    # DDMMYY or YYMMDD -> compact short-date variants.
    if re.fullmatch(r"\d{6}", compact):
        dd, mm, yy = compact[:2], compact[2:4], compact[4:6]
        if 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31:
            for sep in ("", ".", "-", "_"):
                if sep:
                    yield sep.join((dd, mm, yy))
                else:
                    yield dd + mm + yy

    # Keep year-looking values.
    for year in re.findall(r"(?:19|20)\d{2}", raw):
        yield year
        yield year[-2:]


def token_variants(token: str, options: Options) -> list[str]:
    base = compact_token(token)
    if not base:
        return []

    variants: list[str] = []

    raw_family: list[str] = []

    # Domyślnie zachowuj polskie znaki diakrytyczne — pomijaj tylko przy --ascii-only.
    # Dawne zachowanie (wymóg --include-unicode) było błędem: wycinało polskie znaki
    # z wynikowej listy, przez co wordlista była niekompletna dla polskich haseł.
    if not options.ascii_only:
        raw_family.append(base)

    # Zawsze dodaj wariant ASCII (transliteracja ą→a, ó→o itp.) dla narzędzi
    # takich jak Hashcat, które mogą mieć problem z plikami UTF-8.
    folded = ascii_fold(base)
    if folded not in raw_family:
        raw_family.append(folded)

    for item in dedupe_keep_order(raw_family):
        variants.extend(case_variants(item))
        variants.extend(date_variants(item))

    if options.leet_level != "off":
        variants.extend(
            leet_variant
            for variant in list(variants)
            for leet_variant in leet_variants(variant, options.leet_level)
        )

    cleaned = []
    for item in variants:
        if not item:
            continue
        if options.ascii_only:
            item = ascii_fold(item)
            try:
                item.encode("ascii")
            except UnicodeEncodeError:
                continue
        cleaned.append(item)

    return dedupe_keep_order(cleaned)


def leet_variants(value: str, level: str = "light") -> Iterator[str]:
    """Generate controlled leet variants without exploding the wordlist size.

    Levels:
    - light: one substitution at a time, first replacement only.
    - medium: one or two substitutions, up to two replacements per character.
    - aggressive: up to three substitutions and all configured replacements.
    """
    if level == "off" or not value:
        return

    settings = {
        "light": {"max_changes": 1, "max_positions": 8, "max_replacements": 1, "limit": 40},
        "medium": {"max_changes": 2, "max_positions": 10, "max_replacements": 2, "limit": 160},
        "aggressive": {"max_changes": 3, "max_positions": 12, "max_replacements": 99, "limit": 500},
    }
    config = settings.get(level, settings["light"])

    positions: list[tuple[int, tuple[str, ...]]] = []
    for index, char in enumerate(value):
        replacements = LEET_TABLE.get(char.lower())
        if replacements:
            positions.append((index, replacements[: config["max_replacements"]]))
        if len(positions) >= config["max_positions"]:
            break

    seen: set[str] = set()
    produced = 0
    max_changes = min(config["max_changes"], len(positions))

    for changes_count in range(1, max_changes + 1):
        for selected_positions in itertools.combinations(positions, changes_count):
            indexes = [item[0] for item in selected_positions]
            replacement_sets = [item[1] for item in selected_positions]
            for replacements in itertools.product(*replacement_sets):
                chars = list(value)
                for index, replacement in zip(indexes, replacements):
                    chars[index] = replacement
                candidate = "".join(chars)
                if candidate == value or candidate in seen:
                    continue
                seen.add(candidate)
                yield candidate
                produced += 1
                if produced >= config["limit"]:
                    return


def load_profile(path: Path | None) -> list[str]:
    if path is None:
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Nie znaleziono profilu: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Profil JSON jest niepoprawny: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit("Profil musi być obiektem JSON, np. {\"names\": [\"Jan\"]}.")

    values: list[str] = []
    for field in PROFILE_FIELDS:
        raw = data.get(field, [])
        if isinstance(raw, str):
            values.append(raw)
        elif isinstance(raw, list):
            values.extend(str(item) for item in raw if item is not None)
        elif raw:
            raise SystemExit(f"Pole '{field}' musi być tekstem albo listą tekstów.")

    return values


def generate_candidates(seed_words: Iterable[str], options: Options) -> Iterator[str]:
    base_variants = dedupe_keep_order(
        variant
        for word in seed_words
        for variant in token_variants(word, options)
    )

    # 1-token candidates.
    for token in base_variants:
        yield token

    suffix_like = [x for x in base_variants if re.fullmatch(r"[0-9!@#$%^&*?.\-_]+", x)]
    word_like = [x for x in base_variants if x not in suffix_like]

    # Word + number/symbol/year and number/symbol/year + word.
    for word in word_like:
        for suffix in suffix_like:
            for sep in options.separators:
                yield f"{word}{sep}{suffix}"
                yield f"{suffix}{sep}{word}"

    # 2-token combinations, intentionally bounded.
    if options.depth >= 2:
        for left, right in itertools.permutations(word_like[:250], 2):
            if left.lower() == right.lower():
                continue
            for sep in options.separators:
                yield f"{left}{sep}{right}"

                # Add one short numeric/symbolic suffix when available.
                for suffix in suffix_like[:50]:
                    yield f"{left}{sep}{right}{suffix}"

            # Warianty camelCase — przydatne dla polskich haseł złożonych z imienia
            # i nazwiska, np. "janKowalski", "JanKowalski98".
            if left and right:
                camel = left.lower() + right[0].upper() + right[1:].lower()
                pascal = left[0].upper() + left[1:].lower() + right[0].upper() + right[1:].lower()
                yield camel
                yield pascal
                for suffix in suffix_like[:20]:
                    yield camel + suffix
                    yield pascal + suffix


def bounded_candidates(seed_words: Iterable[str], options: Options) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for candidate in generate_candidates(seed_words, options):
        if not (options.min_len <= len(candidate) <= options.max_len):
            continue
        if candidate in seen:
            continue

        seen.add(candidate)
        result.append(candidate)

        if len(result) >= options.max_count:
            break

    return result


def parse_separators(raw: str) -> tuple[str, ...]:
    # Example: "",.,_,- means empty separator + dot + underscore + dash.
    if raw.strip() == "":
        return ("",)

    values: list[str] = []
    for item in raw.split(","):
        if item == '""':
            values.append("")
        else:
            values.append(item)

    if "" not in values:
        values.insert(0, "")

    return tuple(dedupe_keep_order(values))


def write_wordlist(path: Path, candidates: Iterable[str], crlf: bool) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    newline = "\r\n" if crlf else "\n"
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        for candidate in candidates:
            handle.write(candidate + newline)
            count += 1
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gamma_ray",
        description="Defensywny generator spersonalizowanych wordlist po polsku.",
    )
    parser.add_argument("--profile", type=Path, help="Ścieżka do profilu JSON.")
    parser.add_argument("--word", action="append", default=[], help="Dodatkowe słowo bazowe. Można użyć wiele razy.")
    parser.add_argument("--output", type=Path, default=Path("out/wordlist.txt"), help="Plik wynikowy.")
    parser.add_argument("--min-len", type=int, default=4, help="Minimalna długość kandydatury.")
    parser.add_argument("--max-len", type=int, default=24, help="Maksymalna długość kandydatury.")
    parser.add_argument("--max-count", type=int, default=100_000, help="Maksymalna liczba kandydatur.")
    parser.add_argument("--separators", default='"",.,_,-', help='Separatory rozdzielone przecinkami, np. "\\"\\",.,_,-".')
    parser.add_argument("--ascii-only", action="store_true", help="Zapisuj wyłącznie warianty ASCII (pomija polskie znaki diakrytyczne).")
    parser.add_argument("--include-unicode", action="store_true", help="[Przestarzałe] Polskie znaki są teraz domyślnie włączone; użyj --ascii-only aby je wyłączyć.")
    parser.add_argument("--leet", action="store_true", help="Alias zgodności: włącza --leet-level light.")
    parser.add_argument(
        "--leet-level",
        choices=("off", "light", "medium", "aggressive"),
        default=None,
        help="Poziom mutacji leet: off, light, medium albo aggressive.",
    )
    parser.add_argument("--depth", type=int, choices=(1, 2), default=2, help="Głębokość łączenia tokenów.")
    parser.add_argument("--crlf", action="store_true", help="Użyj końców linii CRLF.")
    parser.add_argument("--quiet", action="store_true", help="Ogranicz komunikaty.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.min_len < 1:
        parser.error("--min-len musi być większe od 0")
    if args.max_len < args.min_len:
        parser.error("--max-len nie może być mniejsze niż --min-len")
    if args.max_count < 1:
        parser.error("--max-count musi być większe od 0")

    leet_level = args.leet_level if args.leet_level is not None else ("light" if args.leet else "off")

    options = Options(
        min_len=args.min_len,
        max_len=args.max_len,
        max_count=args.max_count,
        separators=parse_separators(args.separators),
        ascii_only=args.ascii_only,
        include_unicode=args.include_unicode,
        leet_level=leet_level,
        depth=args.depth,
    )

    seed_words = load_profile(args.profile) + args.word
    seed_words = dedupe_keep_order(normalize_space(str(word)) for word in seed_words if str(word).strip())

    if not seed_words:
        raise SystemExit("Brak słów wejściowych. Podaj --profile albo co najmniej jedno --word.")

    candidates = bounded_candidates(seed_words, options)
    count = write_wordlist(args.output, candidates, crlf=args.crlf)

    if not args.quiet:
        polish_count = sum(1 for c in candidates if any(ch in c for ch in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"))
        print(f"[OK] Zapisano {count} kandydatur do: {args.output}")
        if polish_count:
            print(f"[INFO] W tym {polish_count} z polskimi znakami diakrytycznymi ({polish_count*100//count}%).")
        print("[INFO] Używaj wyłącznie w legalnych testach bezpieczeństwa i odzyskiwaniu własnego dostępu.")

    return 0


def gui_main():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:
        raise SystemExit(
            "GUI mode nie jest dostępny w tej instalacji Pythona. "
            "Uruchom skrypt z argumentami lub sprawdź konfigurację Pythona.\n"
            f"Błąd: {exc}"
        )

    root = tk.Tk()
    root.title("Gamma Ray - Generator Wordlist")
    root.geometry("600x700")

    # Variables
    profile_var = tk.StringVar()
    words_var = tk.StringVar()
    output_var = tk.StringVar(value="out/wordlist.txt")
    min_len_var = tk.IntVar(value=4)
    max_len_var = tk.IntVar(value=24)
    max_count_var = tk.IntVar(value=100000)
    separators_var = tk.StringVar(value='"".,_,-')
    ascii_only_var = tk.BooleanVar()
    include_unicode_var = tk.BooleanVar()
    leet_level_var = tk.StringVar(value="off")
    depth_var = tk.IntVar(value=2)
    crlf_var = tk.BooleanVar()
    quiet_var = tk.BooleanVar()

    # Widgets
    ttk.Label(root, text="Plik profilu JSON:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(root, textvariable=profile_var, width=50).grid(row=0, column=1, padx=5, pady=5)
    ttk.Button(root, text="Wybierz", command=lambda: profile_var.set(filedialog.askopenfilename(filetypes=[("JSON files", "*.json")]))).grid(row=0, column=2, padx=5, pady=5)

    ttk.Label(root, text="Dodatkowe słowa (rozdzielone przecinkami):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(root, textvariable=words_var, width=50).grid(row=1, column=1, columnspan=2, padx=5, pady=5)

    ttk.Label(root, text="Plik wyjściowy:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(root, textvariable=output_var, width=50).grid(row=2, column=1, padx=5, pady=5)
    ttk.Button(root, text="Wybierz", command=lambda: output_var.set(filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")]))).grid(row=2, column=2, padx=5, pady=5)

    ttk.Label(root, text="Minimalna długość:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
    ttk.Spinbox(root, from_=1, to=100, textvariable=min_len_var).grid(row=3, column=1, sticky="w", padx=5, pady=5)

    ttk.Label(root, text="Maksymalna długość:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
    ttk.Spinbox(root, from_=1, to=100, textvariable=max_len_var).grid(row=4, column=1, sticky="w", padx=5, pady=5)

    ttk.Label(root, text="Maksymalna liczba kandydatur:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
    ttk.Spinbox(root, from_=1, to=1000000, textvariable=max_count_var).grid(row=5, column=1, sticky="w", padx=5, pady=5)

    ttk.Label(root, text="Separatory:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(root, textvariable=separators_var).grid(row=6, column=1, sticky="w", padx=5, pady=5)

    ttk.Checkbutton(root, text="Tylko ASCII", variable=ascii_only_var).grid(row=7, column=0, sticky="w", padx=5, pady=5)
    ttk.Checkbutton(root, text="Dołącz Unicode", variable=include_unicode_var).grid(row=7, column=1, sticky="w", padx=5, pady=5)
    ttk.Label(root, text="Poziom leet:").grid(row=8, column=0, sticky="w", padx=5, pady=5)
    ttk.Combobox(root, textvariable=leet_level_var, values=["off", "light", "medium", "aggressive"]).grid(row=8, column=1, sticky="w", padx=5, pady=5)
    ttk.Checkbutton(root, text="CRLF", variable=crlf_var).grid(row=9, column=0, sticky="w", padx=5, pady=5)
    ttk.Checkbutton(root, text="Cichy tryb", variable=quiet_var).grid(row=9, column=1, sticky="w", padx=5, pady=5)

    ttk.Label(root, text="Głębokość:").grid(row=10, column=0, sticky="w", padx=5, pady=5)
    ttk.Combobox(root, textvariable=depth_var, values=[1, 2]).grid(row=10, column=1, sticky="w", padx=5, pady=5)

    output_text = tk.Text(root, height=10, width=70)
    output_text.grid(row=11, column=0, columnspan=3, padx=5, pady=5)

    def generate():
        try:
            if min_len_var.get() > max_len_var.get():
                messagebox.showerror("Błąd", "Minimalna długość nie może być większa niż maksymalna.")
                return
            if max_count_var.get() < 1:
                messagebox.showerror("Błąd", "Maksymalna liczba musi być większa od 0.")
                return

            profile_path = Path(profile_var.get()) if profile_var.get() else None
            seed_words = load_profile(profile_path) + [w.strip() for w in words_var.get().split(",") if w.strip()]
            seed_words = dedupe_keep_order(normalize_space(str(word)) for word in seed_words if str(word).strip())

            if not seed_words:
                messagebox.showerror("Błąd", "Brak słów wejściowych. Podaj profil lub słowa.")
                return

            options = Options(
                min_len=min_len_var.get(),
                max_len=max_len_var.get(),
                max_count=max_count_var.get(),
                separators=parse_separators(separators_var.get()),
                ascii_only=ascii_only_var.get(),
                include_unicode=include_unicode_var.get(),
                leet_level=leet_level_var.get(),
                depth=depth_var.get(),
            )

            candidates = bounded_candidates(seed_words, options)
            count = write_wordlist(Path(output_var.get()), candidates, crlf=crlf_var.get())

            msg = f"Zapisano {count} kandydatur do: {output_var.get()}\nUżywaj wyłącznie w legalnych testach bezpieczeństwa."
            output_text.delete(1.0, tk.END)
            output_text.insert(tk.END, msg)
            messagebox.showinfo("Sukces", msg)

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    ttk.Button(root, text="Generuj Wordlist", command=generate).grid(row=12, column=0, columnspan=3, pady=10)

    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        gui_main()
    else:
        raise SystemExit(main())
