import json
import pathlib
import subprocess
import sys
import unittest

HOOK = pathlib.Path(__file__).resolve().parents[1] / "finish-guard.py"


def run(payload):
    result = subprocess.run([sys.executable, "-I", str(HOOK)], input=json.dumps(payload), capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout) if result.stdout.strip() else None


def stop(reply, active=False):
    return run({"hook_event_name": "Stop", "stop_hook_active": active, "last_assistant_message": reply})


class FinishGuardTest(unittest.TestCase):
    def test_blocks_an_offer_to_do_more_work(self):
        for reply in [
            "I fixed the parser.\n\nWant me to also update the tests?",
            "Two options remain.\n\nShould I use the adapter or the wrapper?",
            "Done with step 1.\n\nLet me know if you'd like me to continue.",
            "第一步完成。\n\n要我繼續做第二步嗎？",
        ]:
            self.assertEqual(stop(reply)["decision"], "block", reply)

    def test_allows_a_question_about_an_outward_action(self):
        for reply in [
            "All tests pass.\n\nShould I push the branch and open the PR?",
            "The plan is ready.\n\nWant me to deploy it to production?",
            "Do you want me to delete the old volumes?",
            "要我推送到 main 嗎？",
        ]:
            self.assertIsNone(stop(reply), reply)

    def test_allows_a_plain_report(self):
        self.assertIsNone(stop("Should I? No. I fixed it.\n\nThe suite passes: 212 tests, 0 failures."))

    def test_blocks_only_once(self):
        self.assertIsNone(stop("Want me to also update the tests?", active=True))

    def test_ignores_bad_input(self):
        result = subprocess.run([sys.executable, "-I", str(HOOK)], input="not json", capture_output=True, text=True, timeout=30)
        self.assertEqual((result.returncode, result.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
