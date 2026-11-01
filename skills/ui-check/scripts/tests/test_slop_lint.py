import pathlib
import subprocess
import sys
import tempfile
import unittest

LINT = pathlib.Path(__file__).resolve().parents[1] / "slop-lint.py"

COMPONENT = """export function Card() {
  return (
    <div className="border-l-4 bg-gradient-to-r from-indigo-500 p-[13px] backdrop-blur">
      <p className="text-xs uppercase tracking-widest">Overview</p>
      <h2>Unlock seamless insights ✨</h2>
      <button title="Save">Save</button>
      <span style={{ color: '#7c3aed', padding: '14px' }}>new</span>
      <a href="#top" className="bg-primary text-primary-foreground">top</a>
    </div>
  )
}
"""

STYLES = """:root { --primary: #2563eb; --muted: hsl(220 10% 50%); }
#main { color: var(--primary); }
.ok { color: hsl(var(--primary)); background: var(--muted); }
.card { border-left: 4px solid red; box-shadow: 0 0 40px rgba(99, 102, 241, .5); }
.title { background: linear-gradient(90deg, red, blue); background-clip: text; }
"""


def run(cwd, *args):
    result = subprocess.run([sys.executable, "-I", str(LINT), *args], cwd=cwd, capture_output=True, text=True)
    found = {}
    for line in result.stdout.splitlines():
        parts = line.split(": ", 2)
        if len(parts) == 3 and parts[0].count(":") == 1:
            found.setdefault(parts[1], []).append(int(parts[0].rsplit(":", 1)[1]))
    return result, found


class SlopLintTest(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        (self.dir / "Card.tsx").write_text(COMPONENT)
        (self.dir / "app.css").write_text(STYLES)

    def test_finds_each_kind_in_a_component(self):
        result, found = run(self.dir, "Card.tsx")
        self.assertEqual(result.returncode, 1)
        expected = {
            "accent-stripe": [3], "gradient": [3], "purple": [3, 7], "palette-class": [3], "arbitrary-size": [3], "glass": [3],
            "eyebrow": [4], "stock-copy": [5], "emoji": [5], "native-tooltip": [6], "raw-colour": [7], "inline-style": [7],
        }
        self.assertEqual(found, expected)

    def test_token_definitions_and_selectors_are_not_raw_colours(self):
        _, found = run(self.dir, "app.css")
        self.assertEqual(found, {"raw-colour": [4], "glow": [4], "accent-stripe": [4], "gradient": [5], "gradient-text": [5]})

    def test_without_paths_it_reads_only_added_lines(self):
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        subprocess.run(["git", "add", "."], cwd=self.dir, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"], cwd=self.dir, check=True)
        with open(self.dir / "app.css", "a") as handle:
            handle.write(".new { color: #123456; }\n")
        (self.dir / "New.tsx").write_text('<p className="text-red-500">x</p>\n')
        result, found = run(self.dir)
        self.assertEqual(found, {"raw-colour": [6], "palette-class": [1]})
        self.assertIn("2 finding(s) in 2 file(s)", result.stdout)

    def test_design_rules_can_allow_a_kind_with_a_reason(self):
        (self.dir / "DESIGN.md").write_text("# Rules\n\nslop-lint allow gradient: the brand hero uses the logo gradient\n")
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        result, found = run(self.dir, "app.css")
        self.assertNotIn("gradient", found)
        self.assertIn("gradient-text", found)
        self.assertIn("allowed by DESIGN.md: gradient: the brand hero uses the logo gradient", result.stdout)

    def test_clean_file_passes(self):
        (self.dir / "Clean.tsx").write_text('<button className="bg-primary px-4 text-sm">Save</button>\n')
        result, found = run(self.dir, "Clean.tsx")
        self.assertEqual((result.returncode, found), (0, {}))


if __name__ == "__main__":
    unittest.main()
