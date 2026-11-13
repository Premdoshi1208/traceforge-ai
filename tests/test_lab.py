"""Executed scenario and safety regression tests; no inference is mocked as production."""
import asyncio
import os
import unittest
from unittest.mock import patch

from incident_lab.scenarios import SCENARIOS, get_scenario, healthy_source, scenario_source
from verification.policy import validate_patch
from verification.runner import run_reproduction, verify_patch


class FixtureVerificationTests(unittest.TestCase):
    def test_all_bugs_reproduce_for_expected_reason(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                result = run_reproduction(scenario["id"])
                self.assertEqual(result["exit_code"], 1)
                self.assertIn(scenario["expected_failure"], result["output"])

    @patch.dict(os.environ, {"TRACEFORGE_ALLOW_LOCAL_EXECUTION": "1"})
    def test_healthy_fixes_pass_reproduction_and_regression(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                result = verify_patch(scenario["id"], healthy_source(scenario["id"]))
                self.assertTrue(result["verified"])
                self.assertEqual(result["before"]["exit_code"], 1)
                self.assertEqual(result["after"]["exit_code"], 0)
                self.assertEqual(result["regression"]["exit_code"], 0)

    @patch.dict(os.environ, {"TRACEFORGE_ALLOW_LOCAL_EXECUTION": "1"})
    def test_unchanged_bug_is_never_verified(self):
        result = verify_patch("discount", scenario_source("discount"))
        self.assertFalse(result["verified"])
        self.assertNotEqual(result["after"]["exit_code"], 0)

    @patch.dict(os.environ, {"TRACEFORGE_ALLOW_LOCAL_EXECUTION": "1"})
    def test_reproduction_pass_without_regression_pass_is_not_verified(self):
        source = 'def calculate_total(subtotal, discount_percent):\n    return 90.0\n'
        result = verify_patch("discount", source)
        self.assertEqual(result["after"]["exit_code"], 0)
        self.assertNotEqual(result["regression"]["exit_code"], 0)
        self.assertFalse(result["verified"])

    @patch.dict(os.environ, {"TRACEFORGE_ALLOW_LOCAL_EXECUTION": "0"})
    def test_local_candidate_execution_requires_opt_in(self):
        with self.assertRaises(PermissionError):
            verify_patch("discount", healthy_source("discount"))

    def test_diff_is_scoped_to_fixture(self):
        result = validate_patch("discount", healthy_source("discount"))
        self.assertEqual(result["path"], "incident_lab/fixtures/discount/service.py")
        self.assertIn("--- a/incident_lab/fixtures/discount/service.py", result["diff"])
        self.assertIn("+++ b/incident_lab/fixtures/discount/service.py", result["diff"])

    def test_unknown_scenario_and_path_traversal_rejected(self):
        for scenario in ("../../.env", "custom-repo", "", "discount/../retry"):
            with self.subTest(scenario=scenario):
                with self.assertRaises(ValueError):
                    get_scenario(scenario)

    def test_imports_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_patch("discount", "import os\n" + healthy_source("discount"))

    def test_prompt_injection_cannot_add_tool_capability(self):
        malicious = 'def calculate_total(subtotal, discount_percent):\n    return __import__("os").environ\n'
        with self.assertRaises(ValueError):
            validate_patch("discount", malicious)

    def test_attributes_and_object_graph_escape_are_rejected(self):
        malicious = 'def calculate_total(subtotal, discount_percent):\n    return subtotal.__class__.__bases__\n'
        with self.assertRaises(ValueError):
            validate_patch("discount", malicious)

    def test_file_and_network_operations_are_rejected(self):
        for expr in ('open(".env")', 'eval(discount_percent)', 'exec(discount_percent)', 'globals()'):
            with self.subTest(expression=expr):
                with self.assertRaises(ValueError):
                    validate_patch("discount", f"def calculate_total(subtotal, discount_percent):\n    return {expr}\n")

    def test_signature_replacement_rejected(self):
        with self.assertRaises(ValueError):
            validate_patch("discount", "def calculate_total(subtotal, discount_percent, extra=None):\n    return 90\n")

    def test_decorators_rejected(self):
        with self.assertRaises(ValueError):
            validate_patch("discount", "@print\n" + healthy_source("discount"))

    def test_oversize_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_patch("discount", "#" * 8193)


class ActualTelemetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_scenarios_emit_real_failure_telemetry(self):
        from incident_lab.runtime import observe
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                result = await observe(scenario["id"])
                self.assertEqual(result["metrics"]["baseline_errors"], 0)
                self.assertEqual(result["metrics"]["requests"], 3)
                self.assertEqual(result["metrics"]["errors"], 3)
                self.assertTrue(any(row["level"] == "ERROR" for row in result["logs"]))
                trace_ids = {row["trace_id"] for row in result["responses"]}
                self.assertEqual(len(trace_ids), 4)
                self.assertTrue(all(span["trace_id"] in trace_ids for span in result["traces"]))
                self.assertTrue(all(span["duration_ms"] >= 0 for span in result["traces"]))
                if scenario["id"] == "retry":
                    self.assertEqual(result["metrics"]["downstream_requests"], 12)

    async def test_runs_are_isolated_and_reset(self):
        from incident_lab.runtime import observe
        first, second = await asyncio.gather(observe("discount"), observe("inventory"))
        self.assertEqual(first["scenario_id"], "discount")
        self.assertEqual(second["scenario_id"], "inventory")
        self.assertTrue(all("TypeError" in row["body"]["error"] for row in first["responses"] if row["phase"] == "fault"))
        self.assertTrue(all("KeyError" in row["body"]["error"] for row in second["responses"] if row["phase"] == "fault"))


if __name__ == "__main__":
    unittest.main()
