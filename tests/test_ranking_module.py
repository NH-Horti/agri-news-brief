import sys
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ranking import sort_key_major_first


@dataclass
class _Article:
    score: float
    press: str
    domain: str
    pub_dt_kst: datetime


class TestRankingModule(unittest.TestCase):
    def test_sort_key_major_first_shape(self):
        a = _Article(
            score=12.5,
            press="press",
            domain="example.com",
            pub_dt_kst=datetime(2026, 3, 7, 11, 0, 0),
        )

        key = sort_key_major_first(a, lambda press, dom: 3)

        self.assertEqual(key[0], 12.5)
        self.assertEqual(key[1], 3)
        self.assertEqual(key[2], datetime(2026, 3, 7, 11, 0, 0))


if __name__ == "__main__":
    unittest.main()