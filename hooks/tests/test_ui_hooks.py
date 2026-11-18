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


def repo():
    folder = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", str(folder)], check=True)
    return folder


class LintHookTest(unittest.TestCase):
    def test_reports_only_the_lines_just_written(self):
        folder = repo()
        page = folder / "Card.tsx"
        page.write_text('<p className="text-gray-500">old</p>\n<div className="bg-gradient-to-r from-indigo-500">new</div>\n')
        out = hook("ui-lint.py", {"cwd": str(folder), "tool_input": {"file_path": str(page), "new_string": '<div className="bg-gradient-to-r from-indigo-500">new</div>'}})
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("gradient", context)
        self.assertNotIn("text-gray-500", context)
        self.assertIsNone(hook("ui-lint.py", {"cwd": str(folder), "tool_input": {"file_path": str(page), "new_string": "<p>fine</p>"}}))

    def test_a_short_line_does_not_match_older_lines(self):
        folder = repo()
        style = folder / "app.css"
        style.write_text(".old { color: #123456; }\n.new { margin: 0; }\n")
        self.assertIsNone(hook("ui-lint.py", {"cwd": str(folder), "tool_input": {"file_path": str(style), "new_string": ".new { margin: 0; }\n}"}}))

    def test_finds_a_change_to_part_of_a_line(self):
        folder = repo()
        page = folder / "Badge.tsx"
        page.write_text('<span className="bg-red-500 px-2">Paid</span>\n<span className="bg-red-500 px-2">Due</span>\n')
        out = hook("ui-lint.py", {"cwd": str(folder), "tool_input": {"file_path": str(page), "old_string": "bg-primary px-2\">Due", "new_string": "bg-red-500 px-2\">Due"}})
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Badge.tsx:2: palette-class", context)
        self.assertNotIn("Badge.tsx:1:", context)

    def test_skips_files_outside_a_git_repository(self):
        page = pathlib.Path(tempfile.mkdtemp()) / "report.html"
        page.write_text('<div style="background: linear-gradient(red, blue)">x</div>\n')
        self.assertIsNone(hook("ui-lint.py", {"cwd": str(page.parent), "tool_input": {"file_path": str(page), "content": page.read_text()}}))


if __name__ == "__main__":
    unittest.main()
