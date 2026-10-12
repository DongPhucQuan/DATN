import json

from pydantic import ValidationError

from src.ai.qwen_client import QwenClient
from src.jev.schemas import (
    JEVAnswer,
    JEVRequest,
    JEVResponse,
)


class JEVQwenDecider:
    def __init__(self, qwen=None):
        """Create a decider with an injectable Qwen-compatible client.

        The default client defers its health check until generation, so merely
        constructing the core does not require a running model server.
        """
        self.qwen = qwen if qwen is not None else QwenClient(check_connection=False)
        if not callable(getattr(self.qwen, "generate", None)):
            raise TypeError("qwen must provide a callable generate(prompt) method")

    def _build_prompt(
        self,
        state,
        question_name,
        question,
    ):
        state_json = json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        )

        question_json = json.dumps(
            question.model_dump(),
            ensure_ascii=False,
            indent=2,
        )

        if question.type == "noul":
            output_format = """
Return exactly this structure:

{
  "noul": 0.0
}

Rules:
- The key MUST be exactly "noul".
- The value MUST be a number from 0 to 1.
- Do NOT use the question name as a key.
- Do NOT return "type".
- Do NOT return "answers".
- Do NOT return an explanation.
"""

        elif question.type == "score":
            output_format = """
Return exactly this structure:

{
  "score": 2
}

Rules:
- The key MUST be exactly "score".
- The value MUST be one of the numeric scores in criteria.
- Do NOT write "risk_level": "medium risk".
- Do NOT use the question name as a key.
- Do NOT return the text description as the score.
- Do NOT return "type".
- Do NOT return "answers".
- Do NOT return an explanation.
"""

        elif question.type == "choice":
            output_format = """
Return exactly this structure:

{
  "choice": "normal"
}

Rules:
- The key MUST be exactly "choice".
- The value MUST be exactly one option from criteria.
- Do NOT use the question name as a key.
- Do NOT return "type".
- Do NOT return "answers".
- Do NOT return an explanation.
"""

        else:
            raise ValueError(
                f"Unsupported question type: "
                f"{question.type}"
            )

        return f"""
You are a strict decision model.

Your task is to answer ONE question.

STATE:
{state_json}

QUESTION NAME:
{question_name}

QUESTION:
{question_json}

IMPORTANT:
You are NOT returning a general answer.
You are returning ONLY the typed decision value.

{output_format}

Return ONLY valid JSON.

No markdown.
No code fences.
No explanation.
No extra text.
"""

    def _clean_output(
        self,
        raw_output: str,
    ) -> str:
        cleaned = raw_output.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if (
                lines
                and lines[0].strip().startswith("```")
            ):
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        return cleaned

    def _validate_required_field(
        self,
        data: dict,
        question_type: str,
        question_name: str,
    ) -> None:
        required_fields = {
            "noul": "noul",
            "choice": "choice",
            "score": "score",
        }

        field = required_fields.get(
            question_type
        )

        if field is None:
            raise ValueError(
                f"Unsupported question type "
                f"'{question_type}' "
                f"for question "
                f"'{question_name}'"
            )

        if field not in data:
            raise ValueError(
                f"Missing required field "
                f"'{field}' for question "
                f"'{question_name}'"
            )

        if data[field] is None:
            raise ValueError(
                f"Required field "
                f"'{field}' cannot be null "
                f"for question "
                f"'{question_name}'"
            )

    def _validate_probabilities(
        self,
        data: dict,
        question_name: str,
    ) -> None:
        probabilities = data.get(
            "probabilities",
            {},
        )

        if not isinstance(
            probabilities,
            dict,
        ):
            raise ValueError(
                f"Probabilities must be an object "
                f"for question "
                f"'{question_name}'"
            )

        for key, value in probabilities.items():
            if not isinstance(
                value,
                (int, float),
            ):
                raise ValueError(
                    f"Probability '{key}' must be numeric "
                    f"for question "
                    f"'{question_name}'"
                )

            if value < 0.0 or value > 1.0:
                raise ValueError(
                    f"Probability '{key}' must be "
                    f"between 0 and 1 "
                    f"for question "
                    f"'{question_name}'"
                )

    def _validate_choice(
        self,
        data: dict,
        question,
        question_name: str,
    ) -> None:
        if question.type != "choice":
            return

        choice = data["choice"]
        criteria = question.criteria

        if not isinstance(
            criteria,
            list,
        ):
            raise ValueError(
                f"Choice criteria must be a list "
                f"for question "
                f"'{question_name}'"
            )

        if choice not in criteria:
            raise ValueError(
                f"Invalid choice '{choice}' "
                f"for question "
                f"'{question_name}'. "
                f"Allowed choices: {criteria}"
            )

    def _validate_score(
        self,
        data: dict,
        question,
        question_name: str,
    ) -> None:
        if question.type != "score":
            return

        score = data["score"]

        criteria = question.criteria

        if not isinstance(
            criteria,
            dict,
        ):
            raise ValueError(
                f"Score criteria must be an object "
                f"for question "
                f"'{question_name}'"
            )

        allowed_scores = set()

        for key in criteria:
            try:
                allowed_scores.add(
                    float(key)
                )
            except (
                TypeError,
                ValueError,
            ):
                raise ValueError(
                    f"Invalid score criterion "
                    f"'{key}' for question "
                    f"'{question_name}'"
                )

        if not isinstance(
            score,
            (int, float),
        ):
            raise ValueError(
                f"Score must be numeric "
                f"for question "
                f"'{question_name}'"
            )

        if float(score) not in allowed_scores:
            raise ValueError(
                f"Invalid score '{score}' "
                f"for question "
                f"'{question_name}'. "
                f"Allowed scores: "
                f"{sorted(allowed_scores)}"
            )

    def _ask_one(
        self,
        state,
        question_name,
        question,
    ):
        prompt = self._build_prompt(
            state,
            question_name,
            question,
        )

        raw_output = self.qwen.generate(
            prompt
        )

        cleaned = self._clean_output(
            raw_output
        )

        try:
            data = json.loads(
                cleaned
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON for question "
                f"'{question_name}':\n"
                f"{cleaned}"
            ) from exc

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                f"Answer must be a JSON object "
                f"for question "
                f"'{question_name}'"
            )

        allowed_fields = {
            "choice", "score", "noul", "probabilities", "confidence"
        }
        unexpected_fields = set(data) - allowed_fields
        if unexpected_fields:
            raise ValueError(
                f"Unexpected fields for question '{question_name}': "
                f"{sorted(unexpected_fields)}"
            )

        primary_field = {
            "choice": "choice",
            "score": "score",
            "noul": "noul",
        }.get(question.type)
        if primary_field is None:
            raise ValueError(f"Unsupported question type: {question.type}")
        other_primary_fields = {"choice", "score", "noul"} - {primary_field}
        supplied_other_fields = other_primary_fields.intersection(data)
        if supplied_other_fields:
            raise ValueError(
                f"Wrong answer fields for question '{question_name}': "
                f"{sorted(supplied_other_fields)}"
            )

        self._validate_required_field(
            data,
            question.type,
            question_name,
        )

        self._validate_probabilities(
            data,
            question_name,
        )

        self._validate_choice(
            data,
            question,
            question_name,
        )

        self._validate_score(
            data,
            question,
            question_name,
        )

        answer_data = {
            "type": question.type,
            "choice": data.get(
                "choice"
            ),
            "score": data.get(
                "score"
            ),
            "noul": data.get(
                "noul"
            ),
            "probabilities": data.get(
                "probabilities",
                {},
            ),
            "confidence": data.get(
                "confidence"
            ),
        }

        try:
            answer = (
                JEVAnswer.model_validate(
                    answer_data
                )
            )
        except ValidationError as exc:
            raise ValueError(
                f"Invalid answer for question "
                f"'{question_name}':\n"
                f"{exc}"
            ) from exc

        return answer.model_dump()

    def decide(
        self,
        request: JEVRequest,
    ) -> JEVResponse:
        answers = {}

        for (
            question_name,
            question,
        ) in request.questions.items():
            answers[
                question_name
            ] = self._ask_one(
                request.state,
                question_name,
                question,
            )

        return JEVResponse.model_validate(
            {
                "answers": answers,
            }
        )