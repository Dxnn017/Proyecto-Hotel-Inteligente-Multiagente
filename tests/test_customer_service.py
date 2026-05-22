import pytest
from core.shared_memory import SharedMemory
from core.event_bus import EventBus
from agents.customer_service_agent import CustomerServiceAgent

@pytest.fixture
def setup():
    memory = SharedMemory()
    bus = EventBus()
    agent = CustomerServiceAgent(memory, bus)
    # Simulate an active checkin so guest is "in house"
    memory._guests["G001"]["stage"] = "checkin_completado"
    return memory, bus, agent

def test_service_request_cleaning(setup):
    memory, bus, agent = setup
    payload = {
        "action": "crear_solicitud",
        "guest_id": "G001",
        "service_category": "limpieza",
        "description": "Limpieza de cuarto",
        "room_number": "201"
    }
    result = agent.process(payload)
    assert result["status"] == "success"
    assert result["resolution_status"] == "resuelto"

def test_service_request_maintenance_escalation(setup):
    memory, bus, agent = setup
    payload = {
        "action": "crear_solicitud",
        "guest_id": "G001",
        "service_category": "mantenimiento",
        "description": "Fuga de agua",
        "room_number": "201"
    }
    result = agent.process(payload)
    assert result["status"] == "escalated"
    assert result["requires_human"] is True
