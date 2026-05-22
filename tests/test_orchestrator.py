import pytest
from core.shared_memory import SharedMemory
from core.event_bus import EventBus
from core.conversation_history import ConversationHistory
from agents.orchestrator_agent import OrchestratorAgent

@pytest.fixture
def setup():
    memory = SharedMemory()
    bus = EventBus()
    history = ConversationHistory()
    agent = OrchestratorAgent(memory, bus, history)
    return memory, bus, history, agent

def test_orchestrator_routing(setup):
    memory, bus, history, agent = setup
    
    # Test valid routing to check-in
    req = {
        "guest_id": "G001",
        "intent_hint": "check-in",
        "payload": {
            "action": "iniciar_checkin",
            "guest_id": "G001"
        }
    }
    result = agent.process_request(req)
    assert result["success"] is True
    assert result["target_agent"] == "checkin_agent"

def test_orchestrator_swarm_detection(setup):
    memory, bus, history, agent = setup
    
    req = {
        "guest_id": "G001",
        "intent_hint": "quiero checkout y dejar queja",
        "payload": {
            "billing": {
                "action": "confirmar_checkout",
                "guest_id": "G001"
            },
            "feedback": {
                "action": "recibir_feedback",
                "guest_id": "G001",
                "rating": 2,
                "comment": "Mal"
            }
        }
    }
    result = agent.process_request(req)
    assert result["target_agent"] == "swarm_manager"
    assert result["success"] is True

def test_json_schema_validation(setup):
    memory, bus, history, agent = setup
    
    # Intentional missing field (action)
    req = {
        "guest_id": "G001",
        "intent_hint": "reservar",
        "payload": {
            "guest_name": "Test",
            "room_type": "simple"
        }
    }
    result = agent.process_request(req)
    assert result["success"] is True  # Functional success
    assert "Error de validación JSON" in result["final_message"]
