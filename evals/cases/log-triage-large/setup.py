import datetime
import pathlib
import random

random.seed(11)
services = ["api", "worker", "scheduler", "billing", "search", "auth"]
infos = [
    "request completed in {ms} ms",
    "cache hit ratio {r}%",
    "processed batch of {n} items",
    "heartbeat ok",
    "connection pool size {n}/50",
    "flushed {n} metrics",
]
trace = [
    "Traceback (most recent call last):",
    '  File "/srv/search/client.py", line {n}, in query',
    "    response = self._session.post(url, json=body, timeout=self.timeout)",
    '  File "/srv/search/http.py", line 88, in post',
    "    raise UpstreamTimeout(host)",
    "search.errors.UpstreamTimeout: es-2:9200 did not answer in 2000 ms",
] + [f'  File "/srv/lib/frame{depth}.py", line {depth * 7}, in call' for depth in range(12)]


def write(name, count, planted, noise):
    moment = datetime.datetime(2026, 10, 20)
    lines = []

    def add(level, service, message):
        lines.append(f"{moment.isoformat()}Z {level:5} [{service}] {message}")

    for index in range(count):
        moment += datetime.timedelta(milliseconds=random.randint(20, 400))
        for entry in planted.get(index, []):
            add(*entry)
        if index % noise == 0:
            add("ERROR", "search", f"upstream timeout talking to es-2 (attempt {random.randint(1, 3)}/3), retry succeeded")
            for line in trace:
                lines.append(line.format(n=random.randint(10, 400)))
        elif index % 97 == 0:
            add("WARN", "api", f"slow request GET /products took {random.randint(800, 3000)} ms")
        message = random.choice(infos).format(ms=random.randint(3, 400), r=random.randint(60, 99), n=random.randint(1, 50))
        add(random.choice(["INFO"] * 9 + ["DEBUG"]), random.choice(services), message)
    pathlib.Path("logs", name).write_text("\n".join(lines) + "\n")


pathlib.Path("logs").mkdir(exist_ok=True)
app = {
    100: [("INFO", "scheduler", "config loaded: export.workers=12 (was 4), export.batch_size=500000 (was 50000)")],
    41000: [("WARN", "worker", "disk usage on /var/lib/jobs at 91%")],
    77000: [("WARN", "worker", "disk usage on /var/lib/jobs at 99%")],
    78500: [("ERROR", "worker", "nightly-export: write failed: No space left on device (/var/lib/jobs/export-20261020.tmp)")],
    79000: [("ERROR", "billing", "TLS handshake failed for payments.internal:443: certificate has expired (notAfter=2026-10-19T23:59:59Z)")],
    79040: [("ERROR", "worker", "nightly-export: step 'invoice-sync' failed: billing client error: TLS handshake failed")],
    96000: [("ERROR", "scheduler", "job nightly-export FAILED after 4 failing steps: write-archive, invoice-sync, load-orders, build-chunks")],
}
write("app.log", 100000, app, 60)
worker = {
    20000 + attempt: [("ERROR", "worker", f"nightly-export: db error: too many connections for role 'export_ro' (limit 5) attempt {attempt + 1}")]
    for attempt in range(4)
}
worker[52000] = [("ERROR", "worker", "nightly-export: chunk builder pid 4411 killed by signal 9 (OOMKilled, memory limit 2Gi) while building chunk 3 of 7")]
write("worker.log", 60000, worker, 45)
