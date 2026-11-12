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

STRENGTH = {
    "strength-limit": "Staying under 600 requests per minute stays an expectation for clients.",
    "strength-retry": "Honoring Retry-After stays an expectation or advice for callers, and immediate retries stay discouraged.",
    "strength-suspension": "Suspension after repeated violations stays a possibility and is not certain.",
    "strength-raised": "A raised limit stays a possibility that can be granted and is not a right.",
}

NOTE = "Judge only this statement. A sentence that starts with a verb is a command. 'We recommend' is advice. In STE, 'can' is the correct word for a possibility and does not make it stronger."


def grade(run):
    path = run.workdir / "docs" / "rate-limits.md"
    text = path.read_text() if path.exists() else ""
    original = (pathlib.Path(__file__).parent / "fixture" / "docs" / "rate-limits.md").read_text()
    metrics = ste_metrics(text)
    grades = [{"name": "ste-errors", "passed": metrics["errors_per_100_words"] <= 1.0, "weight": 2, "metrics": metrics}]
    criteria = {name: f"The rewritten document says this: {fact}" for name, fact in FACTS.items()}
    criteria.update({name: f"Compared with the original: {statement} {NOTE}" for name, statement in STRENGTH.items()})
    verdicts = run.judge(criteria, f"ORIGINAL DOCUMENT:\n{original}\n\nREWRITTEN DOCUMENT (grade this one):\n{text}")
    for name, verdict in verdicts.items():
        grades.append({"name": name, "passed": verdict["passed"], "weight": 1, "detail": verdict["reason"]})
    return grades
