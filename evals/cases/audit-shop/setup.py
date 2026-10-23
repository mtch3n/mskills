import pathlib
import uuid

name = f"serve_{uuid.uuid4().hex[:8]}.py"
pathlib.Path("server.py").rename(name)
readme = pathlib.Path("README.md")
readme.write_text(readme.read_text().replace("server.py", name))
