import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from lib import ste_metrics

FACTS = {
    "backup-check": "The on-call engineer is advised to check that the nightly backup job finished before a production deploy.",
    "backup-timing": "The backup job usually finishes around 02:30 UTC and sometimes takes longer on the first day of the month.",
    "rollback-risk": "Rolling back a schema migration without a fresh backup can lose up to 24 hours of order data.",
    "ops-notice": "The on-call engineer is advised to tell the #ops channel so that support is not surprised.",
    "canary-rollback": "If the canary pod health check fails in the first 10 minutes, the deploy is stopped and rolled back.",
    "blip-exception": "Small 5xx blips under 0.5% that clear by themselves can be ignored, but only while p95 latency stays below 800 ms.",
    "escalation": "Problems larger than that exception are escalated to the platform team.",
    "traffic-split": "Only the platform team can change the traffic split, because it owns the load balancer config.",
    "flag-duration": "Feature flags turned on for the release stay in place for at least 48 hours, after which the owning team can remove them.",
    "billing-flag": "A flag that guards a billing change needs finance sign-off before it is removed.",
}

STRENGTH = (
    "Compared with the original, the rewrite keeps the strength of each statement: advice stays advice and is not "
    "turned into a hard requirement, requirements stay requirements, 'usually' stays a typical case, and limits "
    "such as 'only', 'at least' and 'up to' are kept."
)


def grade(run):
    path = run.workdir / "docs" / "deploy-notes.md"
    text = path.read_text() if path.exists() else ""
    original = (pathlib.Path(__file__).parent / "fixture" / "docs" / "deploy-notes.md").read_text()
    metrics = ste_metrics(text)
    grades = [{"name": "ste-errors", "passed": metrics["errors_per_100_words"] <= 1.0, "weight": 2, "metrics": metrics}]
    criteria = {name: f"The rewritten document says this: {fact}" for name, fact in FACTS.items()}
    criteria["strength-kept"] = STRENGTH
    verdicts = run.judge(criteria, f"ORIGINAL DOCUMENT:\n{original}\n\nREWRITTEN DOCUMENT (grade this one):\n{text}")
    for name, verdict in verdicts.items():
        weight = 2 if name == "strength-kept" else 1
        grades.append({"name": name, "passed": verdict["passed"], "weight": weight, "detail": verdict["reason"]})
    return grades
