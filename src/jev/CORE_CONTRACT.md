# JEV Core v1.0 — Standard Contract

This is the stable, domain-neutral template for new JEV agents. A new agent should normally add **configuration, questions, policy rules, and registered handlers**; it should not fork or rewrite the core.

## Execution pipeline

`JEVRequest -> Decider -> JEVResponse -> GenericPolicy -> GenericAction -> GenericActionRouter -> handler -> updated state/result`

- **Decider (AI):** interprets the provided state and answers typed questions. It does not choose executable tools.
- **Policy (deterministic):** maps answer fields to configured action names and parameters.
- **Router (deterministic):** executes only a registered handler. Unknown actions fail closed.
- **StateStore:** returns deep copies; model output cannot mutate the authoritative state directly.
- **Loop:** bounds repeated cycles by a positive `max_steps`; callbacks may stop or prepare the next question set.
- **JEVCore:** public facade and stable result envelope.

## Public API

```python
from src.jev import (
    GenericActionRouter, GenericPolicy, JEVConfig, JEVCore,
    JEVQuestion, JEVRequest,
)

policy = GenericPolicy(
    rules={
        "priority": ("choice", "high", {
            "action": "request_review",
            "parameters": {"reason": "high_priority"},
        }),
    },
    default_action="continue_task",
    default_parameters={},
)
router = GenericActionRouter({
    "request_review": lambda params: {"status": "review_requested", **params},
    "continue_task": lambda params: {"status": "continued", **params},
})
core = JEVCore(
    policy=policy,
    action_router=router,
    config=JEVConfig(agent_id="example-agent", max_steps=3),
)
request = JEVRequest(
    state={"task": "review the report"},
    questions={"priority": JEVQuestion(
        type="choice",
        instructions="Classify task priority.",
        criteria=["low", "medium", "high"],
    )},
)
result = core.run_once(request)  # exactly one cycle
```

Pass a decider implementing `decide(request) -> JEVResponse` to `JEVCore(..., decider=...)` for deterministic/offline execution or a different model backend. If omitted, the standard local Qwen/llama.cpp decider is constructed. The model client connection check is deferred until generation, so constructing a core does not itself require a running server.

A starter implementation is provided in `src/jev/agent_template.py`. Copy it and change only the agent ID, state/question contract, policy rules, and registered handlers for a new domain. Keep the shared core unchanged unless the public contract itself must evolve.

## Question types

- `choice`: `criteria` is a list of allowed string choices; the decider validates the returned choice against it.
- `score`: `criteria` defines the allowed numeric score keys; the decider validates the score.
- `noul`: a normalized value in `[0, 1]`, suitable for probabilities or confidence-like scores; domain thresholds belong in deterministic policy/configuration.

Every question has `type`, `instructions`, and optional `criteria`. The request `state` must be a dictionary and is treated as data, not as executable instructions.

## Policy rule format

Each `rules` entry has the form:

`question_name: (answer_field, expected_value, {"action": "registered_action", "parameters": {...}})`

`answer_field` must be one of `choice`, `score`, or `noul`. The policy returns the configured action; it does not silently append extra parameters. The default action is used when no rule matches.

## Result envelope

Both public run methods return `agent_id`, `status`, `mode`, `steps`, `stop_reason`, `history`, `last_decisions`, `last_action`, `last_result`, `final_state`, and `metadata`.

- `run_once(request)` executes one cycle.
- `run(request, max_steps=None, should_continue=None, next_request=None)` runs up to the configured hard limit. Without `should_continue`, it continues until `max_steps`; when the callback returns false, it stops after that cycle. `next_request(state, history)` can choose the next questions; the loop preserves state continuity.

`stop_reason` is `single_cycle_completed`, `continuation_condition_met`, or `max_steps_reached`.

## Safety and extension boundary

1. AI returns typed answer data, not a tool/action command.
2. Policy maps that data to a configured action name.
3. Router dispatches only names registered by the application.
4. Keep business rules and domain-specific tool handlers in the agent configuration/handler layer, not in the generic engine.
5. Never place secrets, credentials, or unrestricted code execution in state, prompts, or handlers.
6. Existing finance-specific files (`src/jev/engine.py`, `policy.py`, `action_router.py`, `loop.py`) are legacy/domain-specific and are not replaced by this generic core.
7. `world_state.py`, `observation.py`, and `world_engine.py` remain a separate experimental branch; they are not part of the v1.0 public core contract.
