"""Trusted, fixed test harness executed only inside a disposable process/CI job."""
import os
import sys
import unittest

# Limits supplement AST validation. They do not turn this into a general sandbox.
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_048_576, 1_048_576))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (192 * 1024 * 1024, 192 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
except (ImportError, ValueError, OSError):
    pass

if len(sys.argv) != 3 or sys.argv[2] not in {"test_reproduction", "test_regression"}:
    raise SystemExit(2)
working_copy = os.path.realpath(sys.argv[1])
sys.path.insert(0, working_copy)
os.chdir(working_copy)
suite = unittest.defaultTestLoader.loadTestsFromName(sys.argv[2])
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
