import importlib.util
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "session-cost.py"
spec = importlib.util.spec_from_file_location("session_cost", SCRIPT)
session_cost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session_cost)


def assistant(message_id, blocks, usage=None):
    message = {"id": message_id, "content": blocks}
    if usage is not None:
        message["usage"] = usage
    return {"type": "assistant", "message": message}


def usage(fresh=0, read=0, write=0, out=0):
    return {"input_tokens": fresh, "cache_read_input_tokens": read, "cache_creation_input_tokens": write, "output_tokens": out}


def tool(name, **tool_input):
    return {"type": "tool_use", "name": name, "input": tool_input}


def image_result():
    return {"type": "user", "message": {"content": [{"type": "tool_result", "content": [{"type": "image"}, {"type": "text"}]}]}}


class MeasureTest(unittest.TestCase):
    def measure(self, lines):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "s.jsonl"
            path.write_text("\n".join(line if isinstance(line, str) else json.dumps(line) for line in lines))
            return session_cost.measure(path)

    def test_totals_and_peak(self):
        result = self.measure([
            assistant("a", [], usage(1, 100, 10, 5)),
            assistant("b", [], usage(2, 300, 20, 7)),
        ])
        self.assertEqual(result["turns"], 2)
        self.assertEqual(result["cache_read_input_tokens"], 400)
        self.assertEqual(result["output_tokens"], 12)
        self.assertEqual(result["peak_context"], 322)

    def test_split_message_counts_usage_once_and_every_tool(self):
        result = self.measure([
            assistant("a", [tool("Read", file_path="x")], usage(0, 100, 0, 5)),
            assistant("a", [tool("Bash", command="ls")], usage(0, 100, 0, 5)),
        ])
        self.assertEqual(result["turns"], 1)
        self.assertEqual(result["cache_read_input_tokens"], 100)
        self.assertEqual(result["tool_calls"], 2)

    def test_missing_usage_is_unknown(self):
        result = self.measure([assistant("a", [])])
        self.assertEqual(result["unknown_usage"], 1)
        self.assertEqual(result["turns"], 1)

    def test_malformed_lines_are_skipped(self):
        result = self.measure(["{not json", assistant("a", [], usage(out=3))])
        self.assertEqual(result["output_tokens"], 3)

    def test_images(self):
        result = self.measure([image_result(), image_result()])
        self.assertEqual(result["images"], 2)

    def test_wait_calls(self):
        result = self.measure([
            assistant("a", [tool("Bash", command="sleep 60; gh pr checks 1")], usage()),
            assistant("b", [tool("Monitor", command="x")], usage()),
            assistant("c", [tool("Bash", command="pytest")], usage()),
        ])
        self.assertEqual(result["wait_calls"], 2)

    def test_warnings(self):
        result = {"peak_context": 200_000, "images": 11, "wait_calls": 0, "unknown_usage": 0}
        self.assertEqual(len(session_cost.warnings(result)), 2)


if __name__ == "__main__":
    unittest.main()
