import unittest
from mini_validator import Validator, ValidationError, RangeRule, LengthRule, RegexRule


class TestMiniValidator(unittest.TestCase):
    def test_passing_length_validation(self):
        schema = {"username": [LengthRule(min_len=3, max_len=10)]}
        validator = Validator(schema)
        self.assertTrue(validator.validate({"username": "alice"}))

    def test_passing_regex_validation(self):
        schema = {"email": [RegexRule(r"^[\w\.-]+@[\w\.-]+\.\w+$")]}
        validator = Validator(schema)
        self.assertTrue(validator.validate({"email": "user@example.com"}))

    def test_passing_range_validation_interior(self):
        schema = {"age": [RangeRule(min_val=0, max_val=120)]}
        validator = Validator(schema)
        self.assertTrue(validator.validate({"age": 25}))

    def test_range_validation_boundary_inclusive(self):
        # Range is inclusive [0, 100]. Both min and max boundaries should pass.
        schema = {"score": [RangeRule(min_val=0, max_val=100)]}
        validator = Validator(schema)
        self.assertTrue(validator.validate({"score": 0}))
        # Boundary max_val should be valid, but fails due to `value >= self.max_val`
        self.assertTrue(validator.validate({"score": 100}))


if __name__ == "__main__":
    unittest.main()
