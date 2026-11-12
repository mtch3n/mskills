import json
import pathlib
import subprocess
import sys
import unittest

HOOK = pathlib.Path(__file__).resolve().parents[1] / "agent-model.py"


def run(payload):
    result = subprocess.run([sys.executable, "-I", str(HOOK)], input=json.dumps(payload), capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout) if result.stdout.strip() else None


class AgentModelHookTest(unittest.TestCase):
    def test_denies_a_subagent_without_a_model(self):
        out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "prompt": "scan"}})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("haiku", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_allows_a_subagent_with_a_model(self):
        self.assertIsNone(run({"tool_name": "Agent", "tool_input": {"prompt": "scan", "model": "haiku"}}))

    def test_allows_a_fork_without_a_model(self):
        self.assertIsNone(run({"tool_name": "Agent", "tool_input": {"subagent_type": "fork", "prompt": "go"}}))

    def test_ignores_other_tools_and_bad_input(self):
        self.assertIsNone(run({"tool_name": "Bash", "tool_input": {"command": "ls"}}))
        result = subprocess.run([sys.executable, "-I", str(HOOK)], input="not json", capture_output=True, text=True, timeout=30)
        self.assertEqual((result.returncode, result.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
