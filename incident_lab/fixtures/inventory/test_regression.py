import unittest
from service import validate_inventory


class Regression(unittest.TestCase):
    def test_legacy_contract(self):
        self.assertTrue(validate_inventory({"available": 12}, 2))

    def test_insufficient_v2_stock(self):
        with self.assertRaises(ValueError):
            validate_inventory({"stock": {"available": 1}}, 2)

    def test_exact_stock(self):
        self.assertTrue(validate_inventory({"stock": {"available": 2}}, 2))

    def test_empty_response_is_rejected(self):
        with self.assertRaises(KeyError):
            validate_inventory({}, 1)

    def test_zero_quantity(self):
        self.assertTrue(validate_inventory({"stock": {"available": 0}}, 0))


if __name__ == "__main__":
    unittest.main()
