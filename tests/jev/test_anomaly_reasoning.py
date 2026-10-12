from src.jev.qwen_decider import JEVQwenDecider
from src.jev.schemas import JEVQuestion, JEVRequest


def test_logic_choice_clean():
    request = JEVRequest(
        state={
            "condition_a": "true",
            "condition_b": "false",
            "logic": "A OR B",
        },
        questions={
            "result": JEVQuestion(
                type="choice",
                instructions=(
                    "Determine the final result of the logic. "
                    "Condition A is true. "
                    "Condition B is false. "
                    "The rule is A OR B. "
                    "Choose exactly one answer from the provided criteria."
                ),
                criteria=["true", "false"],
            )
        },
    )

    decider = JEVQwenDecider()
    response = decider.decide(request)

    print(response.model_dump())

    assert response.answers["result"].choice == "true"