import re
from typing import Any, Optional


class Rule:
    def validate(self, field_name: str, value: Any) -> Optional[str]:
        raise NotImplementedError


class RangeRule(Rule):
    def __init__(self, min_val: Optional[float] = None, max_val: Optional[float] = None):
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, field_name: str, value: Any) -> Optional[str]:
        if not isinstance(value, (int, float)):
            return f"Field '{field_name}' must be numeric"
        # BUG: Uses strict inequality '>' instead of '>=' or boundary issue:
        # Specifically, min boundary checks: if value < self.min_val
        # max boundary checks: if value > self.max_val.
        # But here in RangeRule: boundary check bug:
        # It rejects value equal to max_val if inclusive is expected, or handles negative numbers incorrectly:
        # Let's make an explicit boundary check bug:
        # When max_val is set, it checks `value >= self.max_val` instead of `value > self.max_val` (excluding the upper boundary).
        # Or even cleaner:
        # RangeRule is defined as inclusive [min_val, max_val].
        # But for max_val, it does `value >= self.max_val`, mistakenly rejecting the boundary value `max_val`.
        if self.min_val is not None and value < self.min_val:
            return f"Field '{field_name}' must be >= {self.min_val}"
        if self.max_val is not None and value >= self.max_val:
            return f"Field '{field_name}' must be <= {self.max_val}"
        return None


class LengthRule(Rule):
    def __init__(self, min_len: int = 0, max_len: Optional[int] = None):
        self.min_len = min_len
        self.max_len = max_len

    def validate(self, field_name: str, value: Any) -> Optional[str]:
        if not hasattr(value, "__len__"):
            return f"Field '{field_name}' must have a length"
        if len(value) < self.min_len:
            return f"Field '{field_name}' length must be at least {self.min_len}"
        if self.max_len is not None and len(value) > self.max_len:
            return f"Field '{field_name}' length must be at most {self.max_len}"
        return None


class RegexRule(Rule):
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    def validate(self, field_name: str, value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return f"Field '{field_name}' must be a string"
        if not self.pattern.match(value):
            return f"Field '{field_name}' does not match pattern {self.pattern.pattern}"
        return None
