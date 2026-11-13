import unittest
from service import charge


class Regression(unittest.IsolatedAsyncioTestCase):
    async def test_immediate_success(self):
        async def paid():
            return "paid"
        self.assertEqual(await charge(paid), "paid")

    async def test_recovers_on_second_attempt(self):
        calls = []
        async def eventually_succeeds():
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError("transient")
            return "paid"
        self.assertEqual(await charge(eventually_succeeds), "paid")
        self.assertEqual(len(calls), 2)

    async def test_single_attempt_budget(self):
        calls = []
        async def timeout():
            calls.append(1)
            raise TimeoutError("deadline")
        with self.assertRaises(TimeoutError):
            await charge(timeout, max_attempts=1)
        self.assertEqual(len(calls), 1)

    async def test_non_timeout_errors_are_not_retried(self):
        calls = []
        async def declined():
            calls.append(1)
            raise ValueError("card declined")
        with self.assertRaises(ValueError):
            await charge(declined)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
