import functools
import os
import http.server
import pathlib

PORT = int(os.environ.get("EVAL_PORT", "8765"))
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(pathlib.Path(__file__).parent / "site"))
print(f"serving site on http://127.0.0.1:{PORT}", flush=True)
http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
