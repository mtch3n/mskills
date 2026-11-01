import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

HOOKS = pathlib.Path(__file__).resolve().parents[1]


def hook(name, payload):
    result = subprocess.run([sys.executable, "-I", str(HOOKS / name)], input=json.dumps(payload), capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout) if result.stdout.strip() else None


def tool(name, **data):
    return {"type": "assistant", "timestamp": "2026-10-31T10:00:00Z", "message": {"content": [{"type": "tool_use", "name": name, "input": data}]}}


class StopHookTest(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.css = self.dir / "app.css"
        self.css.write_text(".card { border-left: 4px solid red; }\n")
        self.start = {"type": "user", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 60))}

    def stop(self, *events, active=False):
        transcript = self.dir / "t.jsonl"
        transcript.write_text("\n".join(json.dumps(e) for e in [self.start, *events]) + "\n")
        return hook("ui-stop.py", {"transcript_path": str(transcript), "cwd": str(self.dir), "stop_hook_active": active, "session_id": f"test-{self.dir.name}"})

    def test_blocks_after_an_unmeasured_ui_edit_and_runs_the_lint(self):
        out = self.stop(tool("Edit", file_path=str(self.css)))
        self.assertEqual(out["decision"], "block")
        self.assertIn(str(self.css), out["reason"])
        self.assertIn("accent-stripe", out["reason"])

    def test_blocks_after_a_sed_edit(self):
        out = self.stop(tool("Bash", command="sed -i 's/12px/16px/' app.css"))
        self.assertEqual(out["decision"], "block")

    def test_passes_when_measured_after_the_last_edit(self):
        self.assertIsNone(self.stop(tool("Edit", file_path=str(self.css)), tool("Bash", command="uv run --script /x/ui-check.py app.html")))

    def test_blocks_when_edited_again_after_the_measurement(self):
        out = self.stop(tool("Edit", file_path=str(self.css)), tool("Bash", command="uv run --script /x/ui-check.py a.html"), tool("Write", file_path=str(self.css)))
        self.assertEqual(out["decision"], "block")

    def test_passes_for_reads_non_ui_files_and_old_files(self):
        old = self.dir / "old.css"
        old.write_text("a{}\n")
        os.utime(old, (time.time() - 3600, time.time() - 3600))
        self.assertIsNone(self.stop(tool("Bash", command="cat app.css"), tool("Edit", file_path=str(self.dir / "main.py")), tool("Edit", file_path=str(old))))

    def test_measures_the_page_that_uses_the_changed_style(self):
        self.css.write_text(".wide { width: 900px; height: 20px; background: #eee; }\n")
        (self.dir / "index.html").write_text("<!doctype html><html><head><meta name='viewport' content='width=device-width'><link rel='stylesheet' href='app.css'></head><body><div class='wide'></div></body></html>")
        out = self.stop(tool("Edit", file_path=str(self.css)))
        self.assertEqual(out["decision"], "block")
        self.assertIn("index.html", out["reason"])
        self.assertIn("F index.html @ 390px overflow-x", out["reason"])
        self.assertIsNone(self.stop(tool("Edit", file_path=str(self.css))))

    def test_clean_page_passes_without_a_block(self):
        self.css.write_text("body { margin: 0; font: 16px/1.5 Arial, sans-serif; }\n")
        (self.dir / "index.html").write_text("<!doctype html><html lang='en'><head><meta name='viewport' content='width=device-width'><title>a</title><link rel='stylesheet' href='app.css'></head><body><main><h1>Files</h1><p>Two files.</p></main></body></html>")
        self.assertIsNone(self.stop(tool("Edit", file_path=str(self.css))))

    def test_skips_test_fixtures(self):
        fixture = self.dir / "tests" / "pages" / "defects.css"
        fixture.parent.mkdir(parents=True)
        fixture.write_text(".a { border-left: 4px solid red; }\n")
        self.assertIsNone(self.stop(tool("Edit", file_path=str(fixture))))

    def test_does_not_block_twice(self):
        self.assertIsNone(self.stop(tool("Edit", file_path=str(self.css)), active=True))


class LintHookTest(unittest.TestCase):
    def test_reports_only_the_lines_just_written(self):
        folder = pathlib.Path(tempfile.mkdtemp())
        page = folder / "Card.tsx"
        page.write_text('<p className="text-gray-500">old</p>\n<div className="bg-gradient-to-r from-indigo-500">new</div>\n')
        out = hook("ui-lint.py", {"cwd": str(folder), "tool_input": {"file_path": str(page), "new_string": '<div className="bg-gradient-to-r from-indigo-500">new</div>'}})
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("gradient", context)
        self.assertNotIn("text-gray-500", context)
        self.assertIsNone(hook("ui-lint.py", {"cwd": str(folder), "tool_input": {"file_path": str(page), "new_string": "<p>fine</p>"}}))

    def test_a_short_line_does_not_match_older_lines(self):
        folder = pathlib.Path(tempfile.mkdtemp())
        style = folder / "app.css"
        style.write_text(".old { color: #123456; }\n.new { margin: 0; }\n")
        self.assertIsNone(hook("ui-lint.py", {"cwd": str(folder), "tool_input": {"file_path": str(style), "new_string": ".new { margin: 0; }\n}"}}))


class CorrectionHookTest(unittest.TestCase):
    def context(self, prompt):
        out = hook("ui-correction.py", {"prompt": prompt})
        return out and out["hookSpecificOutput"]["additionalContext"]

    def test_adds_steps_for_ui_corrections(self):
        for prompt in [
            "the table headers still don't line up",
            "I said no card inside a card, the settings page looks bad",
            "why is the button 2px off again",
            "too much padding on mobile",
            "On the Team page the role chips look uneven, and on my phone the Copy button in the invite box is gone. Fix it.",
            "the dropdown is cut off on the settings page",
        ]:
            self.assertIn("design rules file", self.context(prompt) or "", prompt)

    def test_copy_corrections_add_the_words_step(self):
        for prompt in ["too verbose", "remove this text, not useful", "the page reads like a text book"]:
            self.assertIn("about the words", self.context(prompt) or "", prompt)
        self.assertNotIn("about the words", self.context("the table headers still don't line up"))

    def test_ignores_other_prompts(self):
        for prompt in ["run the eval with claude code", "add a page to the docs", "don't commit yet", "the test still fails"]:
            self.assertIsNone(self.context(prompt), prompt)


if __name__ == "__main__":
    unittest.main()
