import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import csvstat


class SummarizeTest(unittest.TestCase):
    def test_mean(self):
        result = csvstat.summarize(["a"], [["1"], ["3"]], "a")
        self.assertEqual(result["mean"], 2)


if __name__ == "__main__":
    unittest.main()
