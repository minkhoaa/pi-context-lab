from typing import Any, Dict, List
from .rules import Rule


class ValidationError(Exception):
    def __init__(self, errors: Dict[str, List[str]]):
        super().__init__(f"Validation failed with {len(errors)} error(s): {errors}")
        self.errors = errors


class Validator:
    def __init__(self, schema: Dict[str, List[Rule]]):
        self.schema = schema

    def validate(self, data: Dict[str, Any]) -> bool:
        errors: Dict[str, List[str]] = {}
        for field, rules in self.schema.items():
            value = data.get(field)
            if value is None:
                continue
            field_errors = []
            for rule in rules:
                err = rule.validate(field, value)
                if err:
                    field_errors.append(err)
            if field_errors:
                errors[field] = field_errors

        if errors:
            raise ValidationError(errors)
        return True
