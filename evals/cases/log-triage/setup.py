import datetime
import pathlib
import random

random.seed(7)
moment = datetime.datetime(2026, 10, 20)
services = ["api", "worker", "scheduler", "billing", "search", "auth"]
infos = [
    "request completed in {ms} ms",
    "cache hit ratio {r}%",
    "processed batch of {n} items",
    "heartbeat ok",
    "connection pool size {n}/50",
    "flushed {n} metrics",
]
planted = {
    11000: [("WARN", "worker", "disk usage on /var/lib/jobs at 91%")],
    14200: [("WARN", "worker", "disk usage on /var/lib/jobs at 99%")],
    14800: [("ERROR", "worker", "nightly-export: write failed: No space left on device (/var/lib/jobs/export-20261020.tmp)")],
    15000: [("ERROR", "billing", "TLS handshake failed for payments.internal:443: certificate has expired (notAfter=2026-10-19T23:59:59Z)")],
    15050: [("ERROR", "worker", "nightly-export: step 'invoice-sync' failed: billing client error: TLS handshake failed")],
    16010: [("ERROR", "scheduler", "job nightly-export FAILED after 3 failing steps: write-archive, invoice-sync, load-orders")],
}
for attempt in range(4):
    planted[16000 + attempt] = [("ERROR", "worker", f"nightly-export: db error: too many connections for role 'export_ro' (limit 5) attempt {attempt + 1}")]
lines = []


def add(level, service, message):
    lines.append(f"{moment.isoformat()}Z {level:5} [{service}] {message}")


for index in range(20000):
    moment += datetime.timedelta(milliseconds=random.randint(50, 900))
    if index == 6000:
        for attempt in range(3):
            add("ERROR", "search", f"upstream timeout talking to es-2 (attempt {attempt + 1}/3)")
        add("INFO", "search", "es-2 reachable again, retry succeeded")
        continue
    for entry in planted.get(index, []):
        add(*entry)
    message = random.choice(infos).format(ms=random.randint(3, 400), r=random.randint(60, 99), n=random.randint(1, 50))
    add(random.choice(["INFO"] * 9 + ["DEBUG"]), random.choice(services), message)
pathlib.Path("logs").mkdir(exist_ok=True)
pathlib.Path("logs/app.log").write_text("\n".join(lines) + "\n")
