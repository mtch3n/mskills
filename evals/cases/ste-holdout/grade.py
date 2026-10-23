import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from lib import ste_metrics

FACTS = {
    "minute-limit": "The limit is 600 requests per minute for each API key.",
    "burst": "Bursts of up to 100 requests in one second are tolerated if the per-minute average stays under the limit.",
    "429": "Over the limit, the gateway returns 429 responses with a Retry-After header.",
    "retry-after": "Callers are expected to honor Retry-After and not retry at once.",
    "suspension": "Repeated violations in a 15-minute window can cause a temporary suspension of the key for one hour by the abuse-detection service.",
    "raised-limit": "Keys with a legitimate high-volume use, such as bulk exports, can get a raised limit of up to 3,000 requests per minute.",
    "review": "A raised limit needs a written request that the API team reviews.",
    "write-cap": "Raised limits never apply to write endpoints, which stay at 60 requests per minute.",
}

STRENGTH = (
    "Compared with the original, the rewrite keeps the strength of each statement: 'can lead to' and 'might be granted' "
    "stay possibilities and do not become certain, expectations stay expectations, and limits such as 'up to', 'only after' "
    "and 'never' are kept."
)


def grade(run):
    path = run.workdir / "docs" / "rate-limits.md"
    text = path.read_text() if path.exists() else ""
    original = (pathlib.Path(__file__).parent / "fixture" / "docs" / "rate-limits.md").read_text()
    metrics = ste_metrics(text)
    grades = [{"name": "ste-errors", "passed": metrics["errors_per_100_words"] <= 1.0, "weight": 2, "metrics": metrics}]
    criteria = {name: f"The rewritten document says this: {fact}" for name, fact in FACTS.items()}
    criteria["strength-kept"] = STRENGTH
    verdicts = run.judge(criteria, f"ORIGINAL DOCUMENT:\n{original}\n\nREWRITTEN DOCUMENT (grade this one):\n{text}")
    for name, verdict in verdicts.items():
        grades.append({"name": name, "passed": verdict["passed"], "weight": 2 if name == "strength-kept" else 1, "detail": verdict["reason"]})
    return grades
