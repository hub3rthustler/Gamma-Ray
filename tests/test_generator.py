import tempfile
import unittest
from pathlib import Path

import gamma_ray


class GammaRayTests(unittest.TestCase):
    def test_ascii_fold_polish_chars(self):
        self.assertEqual(gamma_ray.ascii_fold("Zażółć gęślą jaźń"), "Zazolc gesla jazn")

    def test_date_variants(self):
        variants = set(gamma_ray.date_variants("1998-04-12"))
        self.assertIn("1998", variants)
        self.assertIn("98", variants)
        self.assertIn("12041998", variants)

    def test_bounded_generation(self):
        options = gamma_ray.Options(
            min_len=4,
            max_len=16,
            max_count=100,
            separators=("", "_"),
            ascii_only=True,
            include_unicode=False,
            leet=True,
            depth=2,
        )
        candidates = gamma_ray.bounded_candidates(["Kraków", "1998", "!"], options)
        self.assertTrue(any("Krakow" in item or "krakow" in item for item in candidates))
        self.assertLessEqual(len(candidates), 100)

    def test_write_wordlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wordlist.txt"
            count = gamma_ray.write_wordlist(path, ["test1", "test2"], crlf=False)
            self.assertEqual(count, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), "test1\ntest2\n")


if __name__ == "__main__":
    unittest.main()
