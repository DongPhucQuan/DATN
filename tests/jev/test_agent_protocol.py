
import pytest

from src.jev.agent_protocol import AgentProtocol
from src.jev.generic_policy import GenericAction


@pytest.fixture
def protocol():
    return AgentProtocol({
        "wait": {
            "required": {},
            "optional": {},
        },
        "move": {
            "required": {
                "direction": {
                    "type": str,
                    "choices": ["north", "south", "east", "west"],
                },
            },
            "optional": {},
        },
        "inspect": {
            "required": {},
            "optional": {
                "target": {"type": str},
            },
        },
    })


def test_valid_move_returns_generic_action(protocol):
    action = protocol.validate({
        "action": "move",
        "parameters": {"direction": "east"},
    })

    assert action == GenericAction(
        "move", {"direction": "east"}
    )


def test_valid_wait_without_parameters(protocol):
    action = protocol.validate({
        "action": "wait",
        "parameters": {},
    })

    assert action.action == "wait"
    assert action.parameters == {}


def test_optional_parameter_is_supported(protocol):
    action = protocol.validate({
        "action": "inspect",
        "parameters": {"target": "tree"},
    })

    assert action.parameters["target"] == "tree"


def test_unknown_action_is_rejected(protocol):
    with pytest.raises(ValueError, match="not allowed"):
        protocol.validate({
            "action": "fly",
            "parameters": {},
        })


def test_invalid_direction_is_rejected(protocol):
    with pytest.raises(ValueError, match="Invalid value"):
        protocol.validate({
            "action": "move",
            "parameters": {"direction": "up"},
        })


def test_missing_required_parameter_is_rejected(protocol):
    with pytest.raises(ValueError, match="Missing required"):
        protocol.validate({
            "action": "move",
            "parameters": {},
        })


def test_unexpected_parameter_is_rejected(protocol):
    with pytest.raises(ValueError, match="Unexpected"):
        protocol.validate({
            "action": "wait",
            "parameters": {"secret_command": "delete_world"},
        })


def test_wrong_parameter_type_is_rejected(protocol):
    with pytest.raises(TypeError, match="must have type"):
        protocol.validate({
            "action": "move",
            "parameters": {"direction": 123},
        })


def test_wrong_decision_structure_is_rejected(protocol):
    with pytest.raises(ValueError, match="exactly"):
        protocol.validate({
            "action": "wait",
            "parameters": {},
            "execute_arbitrary_code": True,
        })


def test_non_dictionary_decision_is_rejected(protocol):
    with pytest.raises(TypeError, match="dictionary"):
        protocol.validate("wait")


def test_non_dictionary_parameters_are_rejected(protocol):
    with pytest.raises(TypeError, match="parameters"):
        protocol.validate({
            "action": "wait",
            "parameters": [],
        })
