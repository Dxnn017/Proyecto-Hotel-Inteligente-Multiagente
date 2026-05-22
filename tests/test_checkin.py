import pytest
from core.shared_memory import SharedMemory
from core.event_bus import EventBus
from agents.checkin_agent import CheckinAgent

@pytest.fixture
def setup():
    memory = SharedMemory()
    bus = EventBus()
    agent = CheckinAgent(memory, bus)
    return memory, bus, agent

def test_checkin_valid_data(setup):
    memory, bus, agent = setup
    payload = {
        "action": "validar_identidad",
        "guest_id": "G003",
        "guest_name": "Roberto Diaz",
        "document_type": "dni",
        "document_number": "12345678"
    }
    result = agent.process(payload)
    assert result["status"] == "success"
    assert result["validation_status"] == "valido"

def test_checkin_invalid_data(setup):
    memory, bus, agent = setup
    payload = {
        "action": "validar_identidad",
        "guest_id": "G003",
        "guest_name": "R",
        "document_type": "dni",
        "document_number": "123"
    }
    result = agent.process(payload)
    assert result["status"] == "failed"
    assert result["validation_status"] == "invalido"
