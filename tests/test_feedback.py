import pytest
from core.shared_memory import SharedMemory
from core.event_bus import EventBus
from agents.feedback_agent import FeedbackAgent

@pytest.fixture
def setup():
    memory = SharedMemory()
    bus = EventBus()
    agent = FeedbackAgent(memory, bus)
    return memory, bus, agent

def test_feedback_positive(setup):
    memory, bus, agent = setup
    payload = {
        "action": "recibir_feedback",
        "guest_id": "G001",
        "rating": 5,
        "comment": "Excelente hotel."
    }
    result = agent.process(payload)
    assert result["status"] == "success"
    assert result["sentiment"] == "positivo"
    assert "promotion" in result

def test_feedback_negative(setup):
    memory, bus, agent = setup
    payload = {
        "action": "recibir_feedback",
        "guest_id": "G001",
        "rating": 1,
        "comment": "Pésimo servicio."
    }
    result = agent.process(payload)
    assert result["status"] == "success"
    assert result["sentiment"] == "negativo"
    assert "follow_up_alert" in result
    assert "promotion" not in result
