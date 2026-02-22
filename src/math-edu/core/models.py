from dataclasses import dataclass


@dataclass
class MathEduConfig:
    base_url: str = "http://127.0.0.1:1234"
    model: str = "local-model"
    max_steps: int = 10
    stop_on_answer: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.max_steps, int) or self.max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        if not isinstance(self.base_url, str) or not self.base_url.strip():
            raise ValueError("base_url cannot be empty")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model cannot be empty")


SKILL_STOP_SUBSKILL = {
    "math_qa": "verify",
    "math_diagnosis": "report",
    "math_tutoring": "lesson_end",
}
