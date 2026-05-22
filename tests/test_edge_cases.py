import pytest
from core.shared_memory import SharedMemory
from core.event_bus import EventBus
from agents.checkin_agent import CheckinAgent
from agents.customer_service_agent import CustomerServiceAgent
from core.conflict_resolver import ConflictResolver

@pytest.fixture
def setup():
    memory = SharedMemory()
    bus = EventBus()
    return memory, bus

def test_checkin_without_reservation(setup):
    memory, bus = setup
    agent = CheckinAgent(memory, bus)
    
    # G004 is a guest without reservation in guests.json
    payload = {
        "action": "iniciar_checkin",
        "guest_id": "G004"
    }
    result = agent.process(payload)
    
    assert result["status"] == "failed"
    assert "redirect_to" in result
    assert result["redirect_to"] == "reservation_agent"

def test_service_request_ambiguous(setup):
    memory, bus = setup
    agent = CustomerServiceAgent(memory, bus)
    
    payload = {
        "action": "crear_solicitud",
        "guest_id": "G001",
        "service_category": "desconocida",
        "description": "Quiero algo",
        "room_number": "201"
    }
    result = agent.process(payload)
    assert result["status"] == "failed"
    assert "no reconocida" in result["response_message"].lower()

def test_room_conflict_resolution(setup):
    memory, bus = setup
    resolver = ConflictResolver(memory, bus)
    
    context = {
        "room_id": "203",
        "room_type": "doble"
    }
    
    # Intentar resolver conflicto de habitación
    result = resolver.check_and_resolve("habitacion_ocupada", "G001", context)
    
    assert result["resolved"] is True
    assert "new_room" in result
