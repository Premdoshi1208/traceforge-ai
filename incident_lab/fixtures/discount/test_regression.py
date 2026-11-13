import unittest
from service import calculate_total


class Regression(unittest.TestCase):
    def test_integer_discount(self):
        self.assertEqual(calculate_total(200, 25), 150.0)

    def test_no_discount(self):
        self.assertEqual(calculate_total(17.95, "0"), 17.95)

    def test_decimal_discount(self):
        self.assertEqual(calculate_total(80, "12.5"), 70.0)

    def test_full_discount(self):
        self.assertEqual(calculate_total(99.99, "100"), 0.0)

    def test_invalid_discount_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            calculate_total(100, "invalid")


if __name__ == "__main__":
    unittest.main()
