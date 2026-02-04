### This tool verifies and sanitizes the output data according to a given schema.

import json


_TYPE_MAP = {
    "string": str,
    "int": int,
    "bool": bool,
    "object": dict,
    "array": list,
    "float": float,
}


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(data, errors, sanitized):
    return {"s": "ok", "d": {"data": data, "errors": errors, "sanitized": sanitized}, "e": None}


def _check_type(value, t):
    py = _TYPE_MAP.get(t)
    if py is None:
        return True
    if t == "bool":
        return isinstance(value, bool)
    return isinstance(value, py)


def _validate(schema, data, path, errors, sanitized):
    if schema is None:
        return data, sanitized

    if isinstance(schema, dict):
        required = schema.get("required", [])
        props = schema.get("properties", {})
        allow_extra = schema.get("allow_extra", False)
        if not isinstance(data, dict):
            errors.append(f"{path}: expected object")
            return data, sanitized

        out = {}
        for k in required:
            if k not in data:
                errors.append(f"{path}.{k}: missing")
        for k, v in data.items():
            if k not in props:
                if not allow_extra:
                    sanitized = True
                else:
                    out[k] = v
                continue
            spec = props[k]
            if isinstance(spec, dict):
                t = spec.get("type")
                if t and not _check_type(v, t):
                    errors.append(f"{path}.{k}: type")
                enum = spec.get("enum")
                if enum and v not in enum:
                    errors.append(f"{path}.{k}: enum")
                if t == "object":
                    v2, sanitized = _validate(spec, v, f"{path}.{k}", errors, sanitized)
                    out[k] = v2
                elif t == "array" and isinstance(v, list):
                    out[k] = v
                else:
                    out[k] = v
            else:
                out[k] = v
        return out, sanitized

    return data, sanitized


def run(args):
    """
    Args schema:
        {"data": object|str, "schema": object, "strict": bool|null}

    Returns:
        {"s": "ok|error", "d": {"data": object, "errors": [str], "sanitized": bool}, "e": {..}|None}
    """
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be an object")
    data = args.get("data")
    schema = args.get("schema")
    strict = args.get("strict")

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return _err("BAD_JSON", "data is not valid json")

    errors = []
    sanitized = False
    data_out, sanitized = _validate(schema, data, "$", errors, sanitized)

    if strict and errors:
        return _err("SCHEMA_FAIL", "; ".join(errors))

    return _ok(data_out, errors, sanitized)

# Quick test lah
if __name__ == "__main__":
    sample = {"data": {"s": "ok", "x": 1}, "schema": {"required": ["s"], "properties": {"s": {"type": "string"}}}, "strict": False}
    print(json.dumps(run(sample), ensure_ascii=True))
