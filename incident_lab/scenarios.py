"""Curated, executable incident fixtures. Never accept arbitrary repository paths."""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCENARIOS = [
    {
        "id": "discount",
        "title": "Broken Orders Deployment",
        "description": "A checkout discount arrives as a JSON string. The new order calculation raises TypeError and returns HTTP 500.",
        "service": "orders",
        "severity": "SEV-2",
        "expected_failure": "TypeError",
        "path": "incident_lab/fixtures/discount/service.py",
        "classification": "input-type-regression",
    },
    {
        "id": "retry",
        "title": "Payment Retry Storm",
        "description": "An off-by-one retry boundary exceeds the payment provider's request budget and ends in a gateway timeout.",
        "service": "payments",
        "severity": "SEV-2",
        "expected_failure": "payment attempts exceeded the configured budget",
        "path": "incident_lab/fixtures/retry/service.py",
        "classification": "retry-budget-regression",
    },
    {
        "id": "inventory",
        "title": "Inventory Contract Drift",
        "description": "Inventory returns a nested stock response while order validation still expects the original flat contract.",
        "service": "inventory",
        "severity": "SEV-2",
        "expected_failure": "KeyError",
        "path": "incident_lab/fixtures/inventory/service.py",
        "classification": "response-contract-regression",
    },
]


def get_scenario(scenario_id: str) -> dict:
    for scenario in SCENARIOS:
        if scenario["id"] == scenario_id:
            return dict(scenario)
    raise ValueError("Unknown controlled scenario")


def scenario_directory(scenario_id: str) -> Path:
    get_scenario(scenario_id)
    return FIXTURES / scenario_id


def scenario_source(scenario_id: str) -> str:
    return (scenario_directory(scenario_id) / "service.py").read_text()


def scenario_tests(scenario_id: str) -> str:
    return (scenario_directory(scenario_id) / "test_reproduction.py").read_text()


def healthy_source(scenario_id: str) -> str:
    """Evaluation oracle, never injected into the agent's patch prompt."""
    return (scenario_directory(scenario_id) / "healthy.py").read_text()
