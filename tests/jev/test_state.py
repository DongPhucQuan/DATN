from src.jev.state import StateStore


def test_initial_state():
    store = StateStore(
        {
            "invoice_id": "INV001",
            "status": "pending",
        }
    )

    state = store.get()

    assert state["invoice_id"] == "INV001"
    assert state["status"] == "pending"


def test_state_update():
    store = StateStore(
        {
            "invoice_id": "INV001",
            "status": "pending",
        }
    )

    state = store.update(
        {
            "status": "review_required",
        }
    )

    assert state["status"] == "review_required"


def test_get_returns_copy():
    store = StateStore(
        {
            "status": "pending",
        }
    )

    state = store.get()
    state["status"] = "corrupted"

    assert store.get()["status"] == "pending"


def test_update_does_not_alias_input():
    changes = {
        "metadata": {
            "risk": "high",
        }
    }

    store = StateStore()

    store.update(changes)

    changes["metadata"]["risk"] = "corrupted"

    assert store.get()["metadata"]["risk"] == "high"