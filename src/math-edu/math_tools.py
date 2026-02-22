import ast
import math
import operator as op

from tool_registry import ToolRegistry, tool

registry = ToolRegistry()

_ALLOWED = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.Mod: op.mod,
}

_MAX_EXPR_LEN = 200
_MAX_AST_NODES = 80
_MAX_POWER_ABS = 10
_MAX_ABS_NUMBER = 1e12


def _safe_eval(expr: str) -> float:
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError("Empty expression")
    if len(expr) > _MAX_EXPR_LEN:
        raise ValueError("Expression too long")

    parsed = ast.parse(expr, mode="eval")
    if sum(1 for _ in ast.walk(parsed)) > _MAX_AST_NODES:
        raise ValueError("Expression too complex")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            val = float(node.value)
            if not math.isfinite(val) or abs(val) > _MAX_ABS_NUMBER:
                raise ValueError("Number out of allowed range")
            return val

        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
            if isinstance(node.op, ast.Pow):
                right = _eval(node.right)
                if abs(right) > _MAX_POWER_ABS:
                    raise ValueError("Power too large")
                left = _eval(node.left)
                val = _ALLOWED[type(node.op)](left, right)
            else:
                left = _eval(node.left)
                right = _eval(node.right)
                val = _ALLOWED[type(node.op)](left, right)

            if not math.isfinite(val):
                raise ValueError("Non-finite result")
            return val

        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED:
            val = _ALLOWED[type(node.op)](_eval(node.operand))
            if not math.isfinite(val):
                raise ValueError("Non-finite result")
            return val

        raise ValueError("Unsupported expression")

    return _eval(parsed.body)


def reset() -> None:
    return None


setattr(registry, "reset", reset)


@tool(
    registry,
    name="calculate",
    description="Safely evaluate a math expression with + - * / ** % and parentheses.",
    parameters={
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
)
def calculate(expression: str) -> str:
    try:
        value = _safe_eval(expression)
        if value.is_integer():
            return str(int(value))
        return str(value)
    except ZeroDivisionError:
        return "ERROR: division by zero"
    except Exception as exc:
        return f"ERROR: {exc}"
