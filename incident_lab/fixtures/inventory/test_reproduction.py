import unittest
from service import validate_inventory


class Reproduction(unittest.TestCase):
    def test_inventory_v2_response(self):
        self.assertTrue(validate_inventory({"stock": {"available": 12}}, 2))


if __name__ == "__main__":
    unittest.main()
