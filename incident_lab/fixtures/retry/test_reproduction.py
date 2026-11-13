import unittest
from service import charge


class Reproduction(unittest.IsolatedAsyncioTestCase):
    async def test_downstream_attempt_budget(self):
        calls = []
        async def timeout():
            calls.append(1)
            raise TimeoutError("payment provider deadline exceeded")
        with self.assertRaises(TimeoutError):
            await charge(timeout, max_attempts=3)
        self.assertEqual(len(calls), 3, "payment attempts exceeded the configured budget")


if __name__ == "__main__":
    unittest.main()
