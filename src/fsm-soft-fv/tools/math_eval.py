from __future__ import annotations

import ast
from typing import Any, Dict


def _err(code: str, msg: str) -> Dict[str, Any]:
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"s": "ok", "d": data, "e": None}


class _SafeMath(ast.NodeVisitor):
    """Tiny calculator brain: no imports, no funny business, just math."""

    _ALLOWED_FUNCS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
    }

    def __init__(self, variables: Dict[str, float]):
        self.variables = variables

    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, bool):
            raise ValueError("bool is not numeric")
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("unsupported constant type")

    def visit_Name(self, node: ast.Name) -> float:
        if node.id not in self.variables:
            raise ValueError(f"unknown variable: {node.id}")
        return float(self.variables[node.id])

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        val = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +val
        if isinstance(node.op, ast.USub):
            return -val
        raise ValueError("unsupported unary operator")

    def visit_BinOp(self, node: ast.BinOp) -> float:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("division by zero")
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            if right == 0:
                raise ValueError("division by zero")
            return left // right
        if isinstance(node.op, ast.Mod):
            if right == 0:
                raise ValueError("modulo by zero")
            return left % right
        if isinstance(node.op, ast.Pow):
            return left ** right
        raise ValueError("unsupported binary operator")

    def visit_Call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise ValueError("unsupported function")
        func_name = node.func.id
        if func_name not in self._ALLOWED_FUNCS:
            raise ValueError(f"unsupported function: {func_name}")
        if node.keywords:
            raise ValueError("keyword arguments are not allowed")
        args = [self.visit(a) for a in node.args]
        return float(self._ALLOWED_FUNCS[func_name](*args))

    def generic_visit(self, node: ast.AST):
        raise ValueError(f"unsupported syntax: {type(node).__name__}")


def _as_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("bool is not numeric")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().replace(",", "")
    if not text:
        raise ValueError("empty numeric value")
    return float(text)


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Args:
      {"expr": str, "vars": {name: number} }
    Returns:
      {"s":"ok|error", "d":{"value": number, "expr": str}, "e": {...}|None}
    """
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")
    expr = args.get("expr")
    vars_raw = args.get("vars", {})
    if not isinstance(expr, str) or not expr.strip():
        return _err("BAD_EXPR", "expr must be non-empty string")
    if not isinstance(vars_raw, dict):
        return _err("BAD_VARS", "vars must be object")

    variables: Dict[str, float] = {}
    try:
        for k, v in vars_raw.items():
            key = str(k).strip()
            if not key or not key.replace("_", "").isalnum():
                return _err("BAD_VAR_NAME", f"invalid variable name: {k}")
            variables[key] = _as_number(v)
    except Exception as exc:
        return _err("BAD_VAR_VALUE", str(exc))

    try:
        tree = ast.parse(expr.strip(), mode="eval")
        value = _SafeMath(variables).visit(tree)
    except Exception as exc:
        return _err("EVAL_FAIL", str(exc))

    if abs(value - round(value)) < 1e-12:
        out_value: Any = int(round(value))
    else:
        out_value = float(value)
    return _ok({"value": out_value, "expr": expr.strip()})
