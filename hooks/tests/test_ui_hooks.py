import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HOOKS = pathlib.Path(__file__).resolve().parents[1]


def hook(name, payload):
    result = subprocess.run([sys.executable, "-I", str(HOOKS / name)], input=json.dumps(payload), capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout) if result.stdout.strip() else None


def tool(name, **data):
    return {"type": "assistant", "timestamp": "2026-10-31T10:00:00Z", "message": {"content": [{"type": "tool_use", "name": name, "input": data}]}}


class BaselineHookTest(unittest.TestCase):
    def test_measures_the_named_page_before_the_work(self):
        folder = pathlib.Path(tempfile.mkdtemp())
        (folder / "app.css").write_text(".wide { width: 900px; height: 20px; } button:focus { outline: none; }\n")
        (folder / "team.html").write_text("<!doctype html><html lang='en'><head><meta name='viewport' content='width=device-width'><title>t</title><link rel='stylesheet' href='app.css'></head><body><main><h1>Team</h1><div class='wide'></div></main></body></html>")
        (folder / "other.html").write_text("<!doctype html><html><body>x</body></html>")
        out = hook("ui-baseline.py", {"prompt": "We ship the Team page tomorrow. Polish it.", "cwd": str(folder), "session_id": f"b-{folder.name}"})
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("team.html @ 390px overflow-x", context)
        self.assertNotIn("other.html", context)
        self.assertIn("focus-removed", context)
        self.assertIn("app.css:1 .wide", context)

    def test_skips_named_bugs_and_agent_messages(self):
        folder = pathlib.Path(tempfile.mkdtemp())
        (folder / "team.html").write_text("<p>x</p>")
        for prompt in ["the Copy button on the team page is cut off", "<agent-message>polish the team page</agent-message>", "polish the release notes"]:
            self.assertIsNone(hook("ui-baseline.py", {"prompt": prompt, "cwd": str(folder), "session_id": "s"}), prompt)


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

    def test_ignores_messages_from_other_agents(self):
        report = 'Another Claude session sent a message:\n<agent-message from="a1">[Subagent hand-back] the Copy button is cut off and the table headers do not line up</agent-message>'
        self.assertIsNone(self.context(report))

    def test_ignores_other_prompts(self):
        for prompt in [
            "run the eval with claude code", "add a page to the docs", "don't commit yet", "the test still fails",
            "i think the issue is the model does not like the input from the plugin post stop hook, it looks like it will stop instead of fixing",
            "why did you change the page again, I said do not touch the docs", "never push to main",
        ]:
            self.assertIsNone(self.context(prompt), prompt)


if __name__ == "__main__":
    unittest.main()
