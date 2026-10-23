import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "ste-check.py"
spec = importlib.util.spec_from_file_location("ste_check", SCRIPT)
ste_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ste_check)


def rules(text):
    return [item["rule"] for item in ste_check.check(text)]


class LengthTest(unittest.TestCase):
    def test_description_over_limit(self):
        sentence = " ".join(["word"] * 26) + "."
        self.assertEqual(rules(sentence), ["length"])

    def test_description_at_limit(self):
        sentence = " ".join(["word"] * 25) + "."
        self.assertEqual(rules(sentence), [])

    def test_procedure_step_uses_lower_limit(self):
        step = "1. " + " ".join(["word"] * 21) + "."
        self.assertEqual(rules(step), ["length"])

    def test_bullet_is_description(self):
        bullet = "- " + " ".join(["word"] * 21) + "."
        self.assertEqual(rules(bullet), [])

    def test_inline_code_counts_as_one_word(self):
        sentence = " ".join(["word"] * 24) + " `python3 -I -m unittest discover -s tests`."
        self.assertEqual(rules(sentence), [])


class StructureTest(unittest.TestCase):
    def test_paragraph_over_six_sentences(self):
        paragraph = " ".join(["This is short."] * 7)
        self.assertEqual(rules(paragraph), ["paragraph"])

    def test_six_sentences_pass(self):
        paragraph = " ".join(["This is short."] * 6)
        self.assertEqual(rules(paragraph), [])

    def test_semicolon(self):
        self.assertEqual(rules("Stop the pump; then open the valve."), ["semicolon"])

    def test_fenced_code_is_skipped(self):
        text = "```\nx = 1; y = 2\nrunning; tested\n```\n"
        self.assertEqual(rules(text), [])

    def test_table_cells_are_checked_alone(self):
        text = "| a | b |\n|---|---|\n| Stop the pump. | Open the valve. |\n"
        self.assertEqual(rules(text), [])


class ScopeTest(unittest.TestCase):
    def test_frontmatter_is_skipped(self):
        text = "---\ndescription: " + " ".join(["word"] * 30) + ".\n---\nShort text.\n"
        self.assertEqual(rules(text), [])

    def test_blockquote_is_skipped(self):
        self.assertEqual(rules("> The pump was stopped; it was set up."), [])

    def test_quoted_words_are_skipped(self):
        self.assertEqual(rules('Replace "set up the server" with one verb.'), [])


class WordTest(unittest.TestCase):
    def test_phrasal_verb(self):
        self.assertEqual(rules("Set up the server."), ["phrasal-verb"])

    def test_ing_verb(self):
        self.assertEqual(rules("The script is checking the file."), ["ing-form"])

    def test_ing_exceptions(self):
        self.assertEqual(rules("Nothing happens during the test."), [])

    def test_ing_nouns(self):
        self.assertEqual(rules("Read the warning and the setting."), [])

    def test_passive(self):
        self.assertEqual(rules("The file was deleted."), ["passive"])

    def test_active(self):
        self.assertEqual(rules("The script deletes the file."), [])


if __name__ == "__main__":
    unittest.main()
