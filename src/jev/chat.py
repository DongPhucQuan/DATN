
import re
from typing import Any

from src.jev.chat_policy import ChatPolicy
from src.jev.chat_router import ChatActionRouter
from src.jev.qwen_decider import JEVQwenDecider
from src.jev.schemas import JEVQuestion, JEVRequest


QUESTIONS = {
    "category": JEVQuestion(
        type="choice",
        instructions="Classify the user's latest message.",
        criteria=["normal", "important", "suspicious"],
    ),
    "risk_level": JEVQuestion(
        type="score",
        instructions="Score the risk level of the user's latest message.",
        criteria={
            "1": "low risk",
            "2": "medium risk",
            "3": "high risk",
        },
    ),
    "is_anomaly": JEVQuestion(
        type="noul",
        instructions=(
            "Estimate whether the user's latest message contains "
            "anomalous or suspicious content, from 0 to 1."
        ),
        criteria={},
    ),
}


def calculate_percentage_change(message: str) -> str | None:
    """Deterministically calculate simple percentage increases/decreases."""
    text = message.casefold().replace(",", "").replace(".", ".")

    patterns = [
        r"(?:từ|tu|from)\s*(-?\d+(?:\.\d+)?)\s*"
        r"(?:triệu|trieu|million|m)?\s*"
        r"(?:lên|len|to|thành|thanh)\s*"
        r"(-?\d+(?:\.\d+)?)\s*(?:triệu|trieu|million|m)?",
        r"(?:kỳ trước|ky truoc|previous period|last period)"
        r".*?(-?\d+(?:\.\d+)?).*?"
        r"(?:kỳ này|ky nay|current period|this period)"
        r".*?(-?\d+(?:\.\d+)?)",
    ]

    if not any(
        keyword in text
        for keyword in (
            "phần trăm", "phan tram", "%", "tăng bao nhiêu",
            "tang bao nhieu", "giảm bao nhiêu", "giam bao nhieu",
            "percentage", "percent",
        )
    ):
        return None

    values = None
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            values = (float(match.group(1)), float(match.group(2)))
            break

    # Also support explicit comparisons such as "100 triệu và 300 triệu".
    if values is None:
        numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
        if len(numbers) == 2:
            values = (float(numbers[0]), float(numbers[1]))

    if values is None:
        return None

    previous, current = values

    if previous == 0:
        return (
            "Không thể tính phần trăm thay đổi so với kỳ trước bằng "
            "công thức thông thường vì giá trị kỳ trước bằng 0."
        )

    change = (current - previous) / abs(previous) * 100
    direction = "tăng" if change > 0 else "giảm" if change < 0 else "không đổi"

    return (
        f"Giá trị thay đổi từ {previous:g} lên {current:g}. "
        f"Tỷ lệ {direction}: {abs(change):g}%."
    )


class JEVChat:
    def __init__(self, qwen=None):
        self.decider = JEVQwenDecider(qwen=qwen)
        self.qwen = self.decider.qwen
        self.policy = ChatPolicy()
        self.router = ChatActionRouter()
        self.state = {
            "session_started": True,
            "message_count": 0,
        }

    def process(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        *,
        analyze: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Tin nhắn không được để trống.")

        message = message.strip()
        history = history or []
        recent_history = history[-10:]

        self.state["last_user_message"] = message
        self.state["message_count"] += 1

        decisions = None
        action = None
        result = None

        # Run structured classification only when explicitly requested.
        if analyze:
            request = JEVRequest(
                state=dict(self.state),
                questions=QUESTIONS,
            )
            response = self.decider.decide(request)
            decisions = response.model_dump()

            action = self.policy.decide(response)
            result = self.router.execute(action)

            self.state["last_action"] = action.action
            self.state["last_result"] = result

        # Prefer deterministic calculation for recognizable percentage questions.
        answer = calculate_percentage_change(message)

        if answer is None:
            history_text = "\n".join(
                f'{item.get("role", "unknown")}: {item.get("content", "")}'
                for item in recent_history
                if isinstance(item, dict)
            ) or "(Chưa có hội thoại trước đó.)"

            pipeline_context = ""
            if analyze:
                pipeline_context = (
                    "\nKẾT QUẢ PIPELINE JEV:\n"
                    f"{decisions}\n"
                    f"Action: {action.action}\n"
                    f"Router result: {result}\n"
                    "Không khẳng định router đã thực hiện tác vụ "
                    "nào ngoài việc trả về kết quả trên.\n"
                )

            prompt = f"""
Bạn là JEV, trợ lý AI chạy cục bộ.

LỊCH SỬ HỘI THOẠI:
{history_text}

TIN NHẮN MỚI:
{message}

{pipeline_context}

Hãy trả lời trực tiếp câu hỏi mới nhất bằng tiếng Việt tự nhiên,
hoặc dùng ngôn ngữ mà người dùng đang sử dụng.
Không xuất JSON trừ khi người dùng yêu cầu.
Không bịa kết quả của công cụ hoặc dữ liệu chưa được cung cấp.
Chỉ trả lời nội dung cần thiết.
""".strip()

            generate_text = getattr(self.qwen, "generate_text", None)
            if not callable(generate_text):
                raise TypeError(
                    "Qwen client cần có generate_text(prompt)."
                )

            answer = generate_text(prompt).strip()

            if not answer:
                raise ValueError("JEV không tạo được câu trả lời.")

        return {
            "answer": answer,
            "decisions": decisions,
            "action": (
                {
                    "name": action.action,
                    "parameters": action.parameters,
                }
                if action is not None
                else None
            ),
            "result": result,
            "state": dict(self.state),
        }


def main():
    from src.ai.qwen_client import QwenClient

    chat = JEVChat(qwen=QwenClient())

    print("=" * 60)
    print("JEV AI - Interactive Prototype")
    print("Type 'exit' to quit.")
    print("Type '/analyze <message>' to run the decision pipeline.")
    print("=" * 60)

    while True:
        try:
            message = input("\nBạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nJEV: Hẹn gặp lại.")
            break

        if not message:
            continue

        if message.casefold() in {"exit", "quit"}:
            print("JEV: Hẹn gặp lại.")
            break

        analyze = message.startswith("/analyze ")
        if analyze:
            message = message[len("/analyze "):].strip()

        try:
            output = chat.process(message, analyze=analyze)
            print("\nJEV:", output["answer"])
        except Exception as exc:
            print(f"\nJEV ERROR [{type(exc).__name__}]: {exc}")


if __name__ == "__main__":
    main()
