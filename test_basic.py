"""
Basic test without database interactions.
"""
import unittest

class TestBasic(unittest.TestCase):
    """Basic test case with no DB interactions"""
    
    def test_simple(self):
        """Simple test"""
        self.assertEqual(1 + 1, 2)

if __name__ == '__main__':
    unittest.main()