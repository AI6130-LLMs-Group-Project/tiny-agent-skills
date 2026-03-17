import json
import os
from pathlib import Path


class FeverWrapper:
    def __init__(self, env, split="dev", data_dir=None):
        self.env = env
        self.split = split
        project_root = Path(__file__).resolve().parents[2]
        self.data_dir = (
            data_dir
            or os.environ.get("FEVER_DATA_DIR")
            or os.path.join(project_root, "data")
        )
        self.data = self._load_split(split)
        self.current = None

    def _load_split(self, split):
        if split == "dev":
            filename = "paper_dev.jsonl"
        elif split == "test":
            filename = "paper_test.jsonl"
        elif split == "train":
            filename = "train.jsonl"
        else:
            raise ValueError(f"Unknown split: {split}")
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Missing FEVER split file: {path}. Download it first."
            )
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def reset(self, idx):
        self.env.reset()
        self.current = self.data[idx]
        return self.current["claim"]

    def step(self, action):
        return self.env.step(action)

    def gold(self):
        if not self.current:
            return None
        return self.current.get("label")


class LoggingWrapper:
    def __init__(self, env):
        self.env = env
        self.logs = []

    def reset(self, *args, **kwargs):
        self.logs = []
        return self.env.reset(*args, **kwargs)

    def step(self, action):
        observation = self.env.step(action)
        self.logs.append({"action": action, "observation": observation})
        return observation

    def gold(self):
        return self.env.gold()

    def __getattr__(self, name):
        return getattr(self.env, name)
