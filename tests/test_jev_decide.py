import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "jev_decide.py"
spec = importlib.util.spec_from_file_location("jev_decide", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class JevDecisionTests(unittest.TestCase):
    def test_compile_all_primitives(self):
        payload = {
            "state": "hello",
            "decisions": {
                "route": {
                    "kind": "choice",
                    "question": "Where?",
                    "options": {"a": "A", "b": "B"},
                },
                "score": {
                    "kind": "score",
                    "question": "How much?",
                    "levels": ["low", "high"],
                },
                "flag": {"kind": "probability", "question": "Is it true?"},
            },
        }
        request = module.compile_request(payload)
        self.assertEqual(request["questions"]["route"]["type"], "choice")
        self.assertEqual(request["questions"]["score"]["type"], "score")
        self.assertEqual(request["questions"]["flag"]["type"], "noul")

    def test_probability_review_band(self):
        payload = {
            "state": "x",
            "decisions": {"flag": {"kind": "probability", "question": "True?"}},
            "policy": {"flag": {"yes_at": 0.8, "no_at": 0.2, "on_uncertain": "review"}},
        }
        policy = module.validate_policy(payload)
        response = {"model": "jev-test", "answers": {"flag": {"type": "noul", "noul": 0.55}}}
        normalized = module.normalize_response(payload, response, policy)
        self.assertEqual(normalized["decisions"]["flag"]["status"], "review")
        self.assertIsNone(normalized["decisions"]["flag"]["value"])

    def test_choice_confidence_gate(self):
        payload = {
            "state": "x",
            "decisions": {
                "route": {
                    "kind": "choice",
                    "question": "Where?",
                    "options": {"a": "A", "b": "B"},
                }
            },
            "policy": {"route": {"min_confidence": 0.7, "on_uncertain": "review"}},
        }
        policy = module.validate_policy(payload)
        response = {
            "model": "jev-test",
            "answers": {
                "route": {
                    "type": "choice",
                    "choice": "a",
                    "confidence": 0.6,
                    "probabilities": {"a": 0.6, "b": 0.4},
                }
            },
        }
        normalized = module.normalize_response(payload, response, policy)
        self.assertEqual(normalized["decisions"]["route"]["status"], "review")


if __name__ == "__main__":
    unittest.main()
