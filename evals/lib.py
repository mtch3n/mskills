import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ste_check", ROOT / "skills" / "ste100" / "scripts" / "ste-check.py")
ste_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ste_check)


def ste_metrics(text):
    findings = ste_check.check(text)
    words = max(len(text.split()), 1)
    errors = sum(1 for item in findings if item["level"] == "error")
    return {
        "words": words,
        "ste_errors": errors,
        "ste_warnings": len(findings) - errors,
        "errors_per_100_words": round(100 * errors / words, 2),
    }
