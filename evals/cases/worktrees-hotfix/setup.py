import pathlib
import subprocess

app = pathlib.Path("app")
app.mkdir()
(app / "tax.py").write_text("def tax(amount, rate):\n    return round(amount * rate, 2)\n")
(app / "test_tax.py").write_text("from tax import tax\n\n\ndef test_tax():\n    assert tax(100, 0.2) == 20.0\n")
(app / "README.md").write_text("# app\n\nRun the tests with `python3 -m pytest -q`.\n")
git = ["git", "-C", "app", "-c", "user.name=dev", "-c", "user.email=dev@example.com"]
subprocess.run(git + ["init", "-q", "-b", "main"], check=True)
subprocess.run(git + ["add", "-A"], check=True)
subprocess.run(git + ["commit", "-q", "-m", "tax"], check=True)
(app / "report.py").write_text("from tax import tax\n\n\ndef report(lines):\n    return [tax(line, 0.2) for line in lines]\n")
with (app / "README.md").open("a") as readme:
    readme.write("\nWork in progress: monthly report.\n")
