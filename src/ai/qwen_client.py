
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from pydantic import ValidationError

from src.schemas.decision import DecisionRequest


# ============================================================
# CONFIG
# ============================================================

SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
HEALTH_URL = "http://127.0.0.1:8080/health"

MODEL_NAME = "qwen-local"
MAX_NEW_TOKENS = 256
TIMEOUT_SECONDS = 300


# ============================================================
# QWEN CLIENT — llama.cpp HTTP BACKEND
# ============================================================

class QwenClient:
    def __init__(self, check_connection: bool = True):
        """Create the client. Set check_connection=False to defer network checks.

        Deferring the check keeps imports, construction, and unit tests offline;
        the first generate() call will still report a clear connection error.
        """
        if not isinstance(check_connection, bool):
            raise TypeError("check_connection must be a bool")

        print("Backend: llama.cpp HTTP API")
        print(f"Endpoint: {SERVER_URL}")

        if check_connection:
            self.check_health()

    def check_health(self) -> None:
        try:
            with urlopen(HEALTH_URL, timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"llama-server health check failed: HTTP {response.status}"
                    )
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                "Không kết nối được llama-server tại 127.0.0.1:8080. "
                "Hãy khởi động server trước."
            ) from exc
        print("LLAMA SERVER CONNECTED")

    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")

        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict JSON decision engine. "
                    "Follow the requested JSON schema exactly. "
                    "Return one complete JSON object only. "
                    "Do not use Markdown fences, explanations, "
                    "or text outside the JSON object. "
                    "Do not invent tools or change field names. "
                    "Ensure every object and array is properly closed."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0,
            "max_tokens": MAX_NEW_TOKENS,
            "stream": False,
        }

        request = Request(
            SERVER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        start = time.perf_counter()

        try:
            with urlopen(
                request,
                timeout=TIMEOUT_SECONDS,
            ) as response:
                response_text = response.read().decode("utf-8")
                result = json.loads(response_text)

        except HTTPError as exc:
            detail = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise RuntimeError(
                f"llama-server HTTP {exc.code}: {detail}"
            ) from exc

        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                f"llama-server request failed: {exc}"
            ) from exc

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "llama-server returned invalid response JSON"
            ) from exc

        elapsed = time.perf_counter() - start

        # Extract response safely.
        try:
            choice = result["choices"][0]
            message = choice["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected llama-server response: {result!r}"
            ) from exc

        if not isinstance(content, str):
            raise TypeError(
                "llama-server returned non-string content"
            )

        # Debug information for diagnosing incomplete output.
        finish_reason = choice.get("finish_reason")

        print(f"[Qwen GGUF] Response received in {elapsed:.1f}s")
        print(f"[DEBUG] finish_reason: {finish_reason}")
        print(f"[DEBUG] usage: {result.get('usage')}")
        print(f"[DEBUG] raw content: {content!r}")

        if finish_reason == "length":
            print(
                "[WARNING] Model reached the output token limit. "
                "The JSON may be incomplete."
            )

        return content.strip()

    # --------------------------------------------------------

    # --------------------------------------------------------
    # GENERATE NATURAL LANGUAGE (separate from JSON decisions)
    # --------------------------------------------------------

    def generate_text(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if not prompt.strip():
            raise ValueError("prompt must not be empty")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the response-generation component of JEV, "
                    "a local Vietnamese AI assistant. Follow the supplied "
                    "context and action result. Answer naturally and clearly. "
                    "Do not claim tools were executed unless the context "
                    "contains their actual results. Do not output JSON unless "
                    "the user explicitly requests it."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 512,
            "stream": False,
        }

        request = Request(
            SERVER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        start = time.perf_counter()
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"llama-server HTTP {exc.code}: {detail}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                f"llama-server text request failed: {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "llama-server returned invalid response JSON"
            ) from exc

        try:
            choice = result["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected llama-server response: {result!r}"
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise ValueError("Qwen returned empty natural-language output")

        print(
            f"[JEV response] {time.perf_counter() - start:.1f}s "
            f"(finish_reason={choice.get('finish_reason')})"
        )
        return content.strip()

    # PARSE DECISION
    # --------------------------------------------------------

    def parse_decision(self, raw_output: str) -> DecisionRequest:
        if not isinstance(raw_output, str):
            raise TypeError("raw_output must be a string")

        cleaned = raw_output.strip()

        if not cleaned:
            raise ValueError("Qwen returned empty output")

        # Remove Markdown fences only when they wrap the output.
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        # Strict JSON parsing: never repair truncated JSON silently.
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            preview = cleaned[:500]

            raise ValueError(
                "Qwen returned invalid or incomplete JSON. "
                f"Line {exc.lineno}, column {exc.colno}: "
                f"{exc.msg}. Output preview: {preview!r}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Decision output must be a JSON object"
            )

        try:
            return DecisionRequest.model_validate(data)
        except ValidationError as exc:
            raise ValueError(
                "Qwen JSON does not match DecisionRequest schema: "
                f"{exc}"
            ) from exc
