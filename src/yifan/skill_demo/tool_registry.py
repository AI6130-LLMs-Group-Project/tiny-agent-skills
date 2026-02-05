import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable[..., Any]


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any], func: Callable[..., Any]) -> None:
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = Tool(name=name, description=description, parameters=parameters, func=func)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list(self) -> List[Tool]:
        return list(self._tools.values())

    def openai_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]


def tool(registry: ToolRegistry, name: str, description: str, parameters: Dict[str, Any]):
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        registry.register(name, description, parameters, fn)
        return fn

    return decorator


def parse_tool_args(arg_str: str) -> Dict[str, Any]:
    if not arg_str:
        return {}
    try:
        return json.loads(arg_str)
    except json.JSONDecodeError:
        return {}
