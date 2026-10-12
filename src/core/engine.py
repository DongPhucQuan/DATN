
from __future__ import annotations

import json
import math
from typing import Any

from src.ai.qwen_client import QwenClient
from src.core.tool_router import ToolRouter
from src.schemas.decision import DecisionRequest


class JEVEngine:
    """
    JEV Finance runtime.

    Chat:
        User message -> Qwen -> Natural-language response

    Invoice analysis:
        Input validation -> Qwen decision -> Decision validation
        -> Allow-listed tool router -> Deterministic result
    """

    AGENT_NAME = "finance"
    CONDITION_NAME = "invoice_anomaly"
    TOOL_NAME = "invoice_anomaly"

    def __init__(
        self,
        qwen: QwenClient | None = None,
        router: ToolRouter | None = None,
    ):
        self.qwen = (
            qwen if qwen is not None else QwenClient()
        )
        self.router = (
            router if router is not None else ToolRouter()
        )

    # ---------------------------------------------------------
    # CHAT: trả về văn bản thuần, KHÔNG parse thành quyết định
    # ---------------------------------------------------------

    def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Tin nhắn không được để trống.")

        history = history or []

        # Chỉ lấy 10 tin nhắn gần nhất để giới hạn độ dài prompt.
        recent_history = history[-10:]

        history_text = self._format_history(recent_history)

        prompt = f"""
Bạn là JEV, trợ lý AI chạy cục bộ trên máy tính người dùng.
Mô hình ngôn ngữ đang sử dụng là Qwen thông qua llama.cpp.

QUY TẮC GIAO TIẾP:
1. Mặc định trả lời bằng tiếng Việt tự nhiên, rõ ràng.
2. Người dùng nói tiếng Anh thì có thể trả lời tiếng Anh.
3. Xưng hô tự nhiên, không máy móc, không tự giới thiệu dài dòng.
4. Ưu tiên câu trả lời ngắn gọn; giải thích kỹ khi được yêu cầu.
5. Nếu người dùng hỏi cách làm, đưa ra các bước cụ thể.
6. Không tự bịa dữ liệu, kết quả kiểm tra hoặc thông tin hệ thống.
7. Không nói đã thực thi công cụ nếu chưa có kết quả công cụ.
8. Nếu thiếu thông tin quan trọng, hỏi lại đúng trọng tâm.
9. Nếu không biết chắc, nói rõ mức độ không chắc chắn.
10. Không xuất JSON trừ khi người dùng yêu cầu.

PHẠM VI HIỆN TẠI:
- Trò chuyện và giải thích thông tin.
- Hỗ trợ người dùng hiểu cách sử dụng JEV.
- JEV Finance có chức năng phân tích hóa đơn qua pipeline riêng.
- Không tự tuyên bố đã phân tích hóa đơn chỉ bằng hội thoại.
- Không tuyên bố có quyền truy cập tệp, Internet hoặc hệ thống bên ngoài
  nếu chưa có công cụ tương ứng.

LỊCH SỬ HỘI THOẠI:
{history_text}

TIN NHẮN MỚI NHẤT:
{message.strip()}

Hãy trả lời trực tiếp tin nhắn mới nhất bằng ngôn ngữ phù hợp.
Chỉ xuất nội dung câu trả lời, không thêm nhãn "Assistant:".
""".strip()

        raw_answer = self.qwen.generate(prompt)

        if not isinstance(raw_answer, str):
            raise TypeError(
                "QwenClient.generate() phải trả về chuỗi văn bản."
            )

        answer = raw_answer.strip()

        if not answer:
            raise ValueError(
                "Qwen trả về câu trả lời rỗng. Hãy thử lại."
            )

        # Loại bỏ nhãn phổ biến nếu mô hình tự thêm vào.
        prefixes = (
            "JEV:",
            "JEV >",
            "Assistant:",
            "Trợ lý:",
        )

        for prefix in prefixes:
            if answer.lower().startswith(prefix.lower()):
                answer = answer[len(prefix):].strip()
                break

        if not answer:
            raise ValueError(
                "Qwen không tạo được nội dung trả lời."
            )

        return answer

    @staticmethod
    def _format_history(
        history: list[dict[str, str]],
    ) -> str:
        if not history:
            return "(Chưa có hội thoại trước đó.)"

        lines: list[str] = []

        for item in history:
            if not isinstance(item, dict):
                continue

            role = item.get("role", "")
            content = item.get("content", "")

            if not isinstance(content, str) or not content.strip():
                continue

            if role == "user":
                label = "Người dùng"
            elif role == "assistant":
                label = "JEV"
            else:
                continue

            # Giới hạn từng tin nhắn để tránh prompt phình quá lớn.
            content = content.strip()[:2000]
            lines.append(f"{label}: {content}")

        return "\n".join(lines) or "(Chưa có hội thoại trước đó.)"

    # ---------------------------------------------------------
    # BACKWARD COMPATIBILITY: luồng quyết định cũ
    # ---------------------------------------------------------

    def run(self, prompt: str) -> dict[str, Any]:
        """
        Entry point tương thích ngược cho pipeline quyết định cũ.
        Không sử dụng hàm này cho hội thoại tự do.
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt phải là chuỗi không rỗng.")

        raw_output = self.qwen.generate(prompt)
        decision = self.qwen.parse_decision(raw_output)

        return self.router.execute(decision)

    # ---------------------------------------------------------
    # INVOICE VALIDATION
    # ---------------------------------------------------------

    @staticmethod
    def _is_number(value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    @classmethod
    def _validate_invoices(
        cls,
        invoices: list[dict[str, Any]],
        threshold: float,
    ) -> tuple[list[dict[str, Any]], float]:
        if not cls._is_number(threshold):
            raise ValueError(
                "Ngưỡng phải là một số hữu hạn."
            )

        threshold = float(threshold)

        if not 0 < threshold <= 1:
            raise ValueError(
                "Ngưỡng phải lớn hơn 0 và không vượt quá 1."
            )

        if not isinstance(invoices, list):
            raise TypeError(
                "Danh sách hóa đơn phải có kiểu list."
            )

        normalized: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for index, invoice in enumerate(invoices):
            if not isinstance(invoice, dict):
                raise TypeError(
                    f"Hóa đơn thứ {index + 1} phải là một object."
                )

            invoice_id = invoice.get("invoice_id")
            expected = invoice.get("expected_price")
            actual = invoice.get("actual_price")

            if (
                not isinstance(invoice_id, str)
                or not invoice_id.strip()
            ):
                raise ValueError(
                    f"Hóa đơn thứ {index + 1} thiếu invoice_id hợp lệ."
                )

            invoice_id = invoice_id.strip()

            if invoice_id in seen_ids:
                raise ValueError(
                    f"Mã hóa đơn bị trùng: {invoice_id}"
                )

            seen_ids.add(invoice_id)

            if not cls._is_number(expected):
                raise ValueError(
                    f"{invoice_id}: expected_price phải là số hữu hạn."
                )

            if not cls._is_number(actual):
                raise ValueError(
                    f"{invoice_id}: actual_price phải là số hữu hạn."
                )

            expected = float(expected)
            actual = float(actual)

            if expected <= 0:
                raise ValueError(
                    f"{invoice_id}: giá dự kiến phải lớn hơn 0."
                )

            if actual < 0:
                raise ValueError(
                    f"{invoice_id}: giá thực tế không được âm."
                )

            normalized.append(
                {
                    "invoice_id": invoice_id,
                    "expected_price": expected,
                    "actual_price": actual,
                }
            )

        return normalized, threshold

    # ---------------------------------------------------------
    # OFFICIAL INVOICE PIPELINE
    # ---------------------------------------------------------

    def run_invoices(
        self,
        invoices: list[dict[str, Any]],
        threshold: float = 0.15,
    ) -> dict[str, Any]:
        """
        Phân tích hóa đơn qua pipeline JEV hiện có.

        Dữ liệu đầu vào đã kiểm tra là nguồn dữ liệu có thẩm quyền.
        Qwen không được tự sửa mã hóa đơn, giá hoặc ngưỡng thực thi.
        """
        trusted_invoices, trusted_threshold = (
            self._validate_invoices(invoices, threshold)
        )

        prompt_payload = {
            "agent": self.AGENT_NAME,
            "condition": self.CONDITION_NAME,
            "tool": self.TOOL_NAME,
            "parameters": {
                "threshold": trusted_threshold,
                "invoices": trusted_invoices,
            },
        }

        prompt = f"""
Bạn là thành phần quyết định của JEV Finance.

Hãy chọn đúng tác vụ phân tích hóa đơn đã được cấu hình.

Trả về đúng một JSON object theo cấu trúc:
{{
  "agent": "finance",
  "condition": "invoice_anomaly",
  "tool": "invoice_anomaly",
  "parameters": {{
    "threshold": 0.15,
    "invoices": []
  }}
}}

Dữ liệu yêu cầu:
{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}

Quy tắc:
- Chỉ dùng agent, condition và tool đã chỉ định.
- Không bịa hoặc thay đổi mã hóa đơn.
- Chỉ trả về JSON hợp lệ.
- Không trả Markdown hoặc giải thích.
""".strip()

        raw_output = self.qwen.generate(prompt)
        proposed_decision = self.qwen.parse_decision(raw_output)

        # Kiểm tra quyết định theo allow-list của router.
        self.router.validator.validate(proposed_decision)

        if (
            proposed_decision.agent != self.AGENT_NAME
            or proposed_decision.condition != self.CONDITION_NAME
            or proposed_decision.tool != self.TOOL_NAME
        ):
            raise ValueError(
                "Qwen chọn một tác vụ không được hỗ trợ."
            )

        # Dùng dữ liệu đã xác thực, không dùng tham số do Qwen tự sinh.
        trusted_decision = DecisionRequest(
            agent=self.AGENT_NAME,
            condition=self.CONDITION_NAME,
            tool=self.TOOL_NAME,
            parameters={
                "threshold": trusted_threshold,
                "invoices": trusted_invoices,
            },
        )

        result = self.router.execute(trusted_decision)

        return {
            "status": "completed",
            "agent": self.AGENT_NAME,
            "condition": self.CONDITION_NAME,
            "tool": self.TOOL_NAME,
            "input_count": len(trusted_invoices),
            "threshold": trusted_threshold,
            "result": result,
        }
