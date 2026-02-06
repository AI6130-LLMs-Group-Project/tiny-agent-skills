from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "paper_dev.jsonl"


def _is_port_listening(host: str, port: int, timeout: float = 0.3) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _prompt_port() -> int:
    while True:
        raw = input("Enter LLM server port number: ").strip()
        if raw.isdigit():
            port = int(raw)
            if 1 <= port <= 65535:
                return port
        print("Invalid port. Enter a number between 1 and 65535.")


def _start_server(port: int) -> None:
    if os.name == "nt":
        script = ROOT / "script" / "run_qwen3vl_server.bat"
        cmd = ["cmd", "/c", str(script), str(port)]
    else:
        script = ROOT / "script" / "run_qwen3vl_server.sh"
        cmd = ["bash", str(script), str(port)]
    print(f"Starting LLM server on port {port}...")
    subprocess.Popen(cmd, cwd=str(ROOT))


def _wait_for_port(port: int, timeout_s: int = 20) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _is_port_listening("127.0.0.1", port):
            return True
        time.sleep(0.5)
    return False


def _uv_available() -> bool:
    if not shutil.which("uv"):
        return False
    return (ROOT / "pyproject.toml").is_file()


def _pip_available() -> bool:
    try:
        import pip  # noqa: F401
        return True
    except Exception:
        return False


def _resolve_python_cmd() -> list[str] | None:
    if _uv_available():
        return ["uv", "run", "python"]
    venv_py = ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "python"
    if venv_py.is_file():
        return [str(venv_py)]
    if _pip_available():
        return [sys.executable]
    return None


def _pause_exit() -> None:
    if os.name == "nt":
        input("Press Enter to exit...")


def _resolve_dataset_path(data_arg: str | None) -> Path:
    if data_arg:
        path = Path(data_arg).expanduser()
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        return path
    return DEFAULT_DATASET


def _react_split_from_path(path: Path) -> str | None:
    name = path.name
    if name == "paper_dev.jsonl":
        return "dev"
    if name == "paper_test.jsonl":
        return "test"
    if name == "train.jsonl":
        return "train"
    return None


def _select_menu(options: list[str]) -> int:
    if os.name != "nt":
        for i, opt in enumerate(options, start=1):
            print(f"{i}. {opt}")
        while True:
            raw = input("Select a test number: ").strip()
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(options):
                    return idx
            print("Invalid selection.")

    import msvcrt

    idx = 0
    while True:
        os.system("cls")
        print("Select a test (use ↑/↓ and Enter):\n")
        for i, opt in enumerate(options):
            prefix = "> " if i == idx else "  "
            print(f"{prefix}{opt}")
        ch = msvcrt.getch()
        if ch in (b"\r", b"\n"):
            return idx
        if ch in (b"\x00", b"\xe0"):
            key = msvcrt.getch()
            if key == b"H":
                idx = (idx - 1) % len(options)
            elif key == b"P":
                idx = (idx + 1) % len(options)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None, help="LLM server port")
    parser.add_argument("--data", default=None, help="Dataset JSONL path")
    args = parser.parse_args()

    if args.port is not None and not (1 <= args.port <= 65535):
        print(f"Invalid port: {args.port}")
        _pause_exit()
        return 1

    dataset_path = _resolve_dataset_path(args.data)
    if not dataset_path.is_file():
        print(f"Dataset not found: {dataset_path}")
        _pause_exit()
        return 1

    if args.port is not None:
        port = args.port
    elif args.data is None:
        if _is_port_listening("127.0.0.1", 1025):
            port = 1025
        else:
            port = _prompt_port()
    else:
        port = 1025

    if not _is_port_listening("127.0.0.1", port):
        if args.data is None:
            _start_server(port)
            if not _wait_for_port(port):
                print(f"LLM server did not start on port {port}.")
                _pause_exit()
                return 1
        else:
            print(f"Warning: no LLM server detected on 127.0.0.1:{port}.")

    python_cmd = _resolve_python_cmd()
    if not python_cmd:
        print("No valid Python environment found. Install with uv or pip first.")
        _pause_exit()
        return 1

    env = os.environ.copy()
    env["LLM_PORT"] = str(port)
    env["LLM_ENDPOINT"] = f"http://127.0.0.1:{port}"
    env["LLM_BASE_URL"] = f"http://127.0.0.1:{port}/v1"
    py_path = str(ROOT / "src")
    env["PYTHONPATH"] = (
        py_path
        if not env.get("PYTHONPATH")
        else py_path + os.pathsep + env["PYTHONPATH"]
    )

    options = [
        ("ReAct", "react"),
        ("DAG", "dag"),
        ("FSM", "fsm"),
        ("Chinese test 1 (math solver)", "cn2"),
        ("Chinese test 2 (fact verification)", "cn3"),
        ("Chinese test 3 (chat)", "cn_chat"),
    ]
    choice = _select_menu([o[0] for o in options])
    selected = options[choice][1]

    if selected == "react":
        split = _react_split_from_path(dataset_path)
        if split is None:
            print("ReAct runner supports paper_dev.jsonl, paper_test.jsonl, or train.jsonl only.")
            dataset_path = DEFAULT_DATASET
            split = "dev"
        cmd = [
            *python_cmd,
            "src/react-based-method/run_skill_fever_eval.py",
            "--n",
            "20",
            "--split",
            split,
            "--data-dir",
            str(dataset_path.parent),
            "--base-url",
            f"http://127.0.0.1:{port}",
        ]
    elif selected == "dag":
        cmd = [
            *python_cmd,
            "-m",
            "dag",
            "--dataset",
            str(dataset_path),
            "--limit",
            "20",
        ]
    elif selected == "fsm":
        cmd = [
            *python_cmd,
            "src/fsm-based-method/fever_runner.py",
            "--data",
            str(dataset_path),
            "--limit",
            "20",
        ]
    elif selected == "cn2":
        cmd = [*python_cmd, "src/react-based-method/scripts/test_cn2.py"]
    elif selected == "cn3":
        cmd = [*python_cmd, "src/react-based-method/scripts/test_cn3.py"]
    else:
        cmd = [*python_cmd, "src/react-based-method/scripts/test_chinese.py"]

    print("\nRunning:")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT), env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
