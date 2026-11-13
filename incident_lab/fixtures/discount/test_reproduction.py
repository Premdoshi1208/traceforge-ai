import unittest
from service import calculate_total


class Reproduction(unittest.TestCase):
    def test_checkout_discount_from_http_json(self):
        self.assertEqual(calculate_total(100, "10"), 90.0)


if __name__ == "__main__":
    unittest.main()
