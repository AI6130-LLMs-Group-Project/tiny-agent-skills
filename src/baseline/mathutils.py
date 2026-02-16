"""
Math utility tools for GSM8K baseline function-calling.
"""

from __future__ import annotations

import ast
import json
import math
from fractions import Fraction
from typing import Any

_MAX_ABS_VALUE = 10**12
_MAX_POWER = 12


def _to_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid numeric input")
    return float(value)


def _check_numeric_bounds(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("non-finite numeric result")
    if abs(value) > _MAX_ABS_VALUE:
        raise ValueError("numeric result too large")
    return value


def _eval_expr(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_expr(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return _check_numeric_bounds(float(node.value))
        raise ValueError("only numeric constants are allowed")

    if isinstance(node, ast.UnaryOp):
        operand = _eval_expr(node.operand)
        if isinstance(node.op, ast.UAdd):
            return _check_numeric_bounds(+operand)
        if isinstance(node.op, ast.USub):
            return _check_numeric_bounds(-operand)
        raise ValueError("unsupported unary operator")

    if isinstance(node, ast.BinOp):
        left = _eval_expr(node.left)
        right = _eval_expr(node.right)

        if isinstance(node.op, ast.Add):
            return _check_numeric_bounds(left + right)
        if isinstance(node.op, ast.Sub):
            return _check_numeric_bounds(left - right)
        if isinstance(node.op, ast.Mult):
            return _check_numeric_bounds(left * right)
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("division by zero")
            return _check_numeric_bounds(left / right)
        if isinstance(node.op, ast.FloorDiv):
            if right == 0:
                raise ValueError("division by zero")
            return _check_numeric_bounds(left // right)
        if isinstance(node.op, ast.Mod):
            if right == 0:
                raise ValueError("division by zero")
            return _check_numeric_bounds(left % right)
        if isinstance(node.op, ast.Pow):
            if abs(right) > _MAX_POWER:
                raise ValueError("power exponent too large")
            return _check_numeric_bounds(left**right)
        raise ValueError("unsupported binary operator")

    raise ValueError("unsupported expression")


def safe_calculate(expression: str) -> float:
    text = (expression or "").strip()
    if not text:
        raise ValueError("expression is required")
    tree = ast.parse(text, mode="eval")
    return _eval_expr(tree)


def calculator(expression: str) -> dict[str, Any]:
    value = safe_calculate(expression)
    return {"value": value}


def simplify_fraction(numerator: int | float, denominator: int | float) -> dict[str, Any]:
    den = _to_float(denominator)
    if den == 0:
        raise ValueError("denominator must not be zero")
    num = _to_float(numerator)

    frac = Fraction(num / den).limit_denominator()
    return {
        "numerator": frac.numerator,
        "denominator": frac.denominator,
        "fraction": f"{frac.numerator}/{frac.denominator}",
    }


def round_number(value: int | float, digits: int = 2) -> dict[str, Any]:
    d = int(digits)
    if d < 0 or d > 10:
        raise ValueError("digits must be between 0 and 10")
    v = _to_float(value)
    return {"value": round(v, d)}


def to_percent(value: int | float, decimals: int = 2) -> dict[str, Any]:
    d = int(decimals)
    if d < 0 or d > 10:
        raise ValueError("decimals must be between 0 and 10")
    v = _to_float(value) * 100.0
    p = round(v, d)
    return {"value": p, "percent": f"{p:.{d}f}%"}


def _as_number(value: Any) -> int | float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid numeric input")
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        v = value.strip()
        if "." in v:
            return float(v)
        return int(v)
    raise ValueError("invalid numeric input")


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate an arithmetic expression. Supports +, -, *, /, //, %, **, and parentheses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simplify_fraction",
            "description": "Reduce numerator/denominator to simplest fraction form.",
            "parameters": {
                "type": "object",
                "properties": {
                    "numerator": {"type": "number"},
                    "denominator": {"type": "number"},
                },
                "required": ["numerator", "denominator"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "round_number",
            "description": "Round a number to a fixed number of decimal digits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "digits": {"type": "integer", "default": 2},
                },
                "required": ["value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "to_percent",
            "description": "Convert a ratio (e.g. 0.25) to percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "decimals": {"type": "integer", "default": 2},
                },
                "required": ["value"],
            },
        },
    },
]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    args = arguments or {}
    try:
        if name == "calculator":
            result = calculator(expression=str(args.get("expression", "")))
        elif name == "simplify_fraction":
            result = simplify_fraction(
                numerator=_as_number(args.get("numerator")),
                denominator=_as_number(args.get("denominator")),
            )
        elif name == "round_number":
            result = round_number(
                value=_as_number(args.get("value")),
                digits=int(args.get("digits", 2)),
            )
        elif name == "to_percent":
            result = to_percent(
                value=_as_number(args.get("value")),
                decimals=int(args.get("decimals", 2)),
            )
        else:
            return {"ok": False, "error": f"unknown tool: {name}"}
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def parse_tool_args(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
