# Controlled incident lab

The hosted lab is an instrumented single-process ASGI application. Gateway, orders, inventory, payments and the payment-provider boundary perform real HTTP requests using HTTPX's ASGI transport. They are not separately deployed microservices. Each `observe()` call creates fresh fixture modules, app state, logs and spans, so one visitor cannot corrupt another run or the control plane.

Each run sends one healthy baseline request followed by three failing checkout requests. Status codes, errors, spans, retry counts and elapsed times come from execution. Fault activation is labeled a controlled scenario, not a production deployment. `recent_changes` records the activation instead of inventing a Git commit.

| Scenario | Real failure | Reproduction | Regression coverage |
| --- | --- | --- | --- |
| `discount` | String discount divided by integer raises `TypeError`; HTTP 500 | String-valued checkout discount | Numeric, zero, decimal, full and invalid discounts |
| `retry` | Four downstream HTTP requests despite a three-attempt budget; HTTP 504 | Count callback invocations after actual timeouts | Immediate success, transient recovery, one-attempt budget, non-timeout rejection |
| `inventory` | Flat-contract consumer reads a nested response; `KeyError`, HTTP 500 | V2 stock response | Legacy contract, insufficient stock, exact stock, malformed response, zero quantity |

`service.py` is the buggy source inspected by the agent. `healthy.py` is an evaluation oracle and is never supplied to a patch-generation prompt. Reproduction and regression tests are trusted repository code; candidates cannot modify them.

## Candidate execution boundary

`verification.policy.validate_patch()` checks an exact function signature and a narrow Python AST allowlist. It rejects imports, attributes, arbitrary calls, decorators, nested definitions and unrelated files. This policy is a defense for these curated exercises, not a secure general-purpose Python sandbox.

`verification.runner.verify_patch()` executes validated source in temporary working copies using a fixed child-process harness with a stripped environment, CPU/file/descriptor limits, Linux memory/process limits and a ten-second deadline. It requires `TRACEFORGE_ALLOW_LOCAL_EXECUTION=1`. Enable that only for local development or the ephemeral verification CI job. **Do not enable it in a public web process.** Production dispatches `.github/workflows/verify-patch.yml` to GitHub Actions, whose test job has no application secrets and no persisted checkout credentials.

Verification requires the original reproduction to fail for the expected reason, the same reproduction to pass after the patch, and every trusted regression test to pass. A passing reproduction by itself is never enough. Evidence preserves commands, output, exit codes, duration, timestamps and the exact candidate SHA-256.

## Execute the checks

```sh
python -m unittest discover -s tests -p test_lab.py -v
```

The test suite sets the local-execution opt-in only around explicit verifier tests. These deterministic fixture/security checks do not measure model diagnosis accuracy.
