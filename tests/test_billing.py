import pytest
from core.shared_memory import SharedMemory
from core.event_bus import EventBus
from agents.billing_agent import BillingAgent

@pytest.fixture
def setup():
    memory = SharedMemory()
    bus = EventBus()
    agent = BillingAgent(memory, bus)
    return memory, bus, agent

def test_billing_with_consumptions(setup):
    memory, bus, agent = setup
    payload = {
        "action": "calcular_factura",
        "guest_id": "G001"
    }
    result = agent.process(payload)
    assert result["status"] == "success"
    assert result["consumption_total"] > 0
    assert result["total_amount"] > 0
    assert "invoice_id" not in result # Solo se calcula, no se genera aún

def test_billing_checkout_confirm(setup):
    memory, bus, agent = setup
    payload = {
        "action": "confirmar_checkout",
        "guest_id": "G001",
        "payment_method": "tarjeta_credito"
    }
    result = agent.process(payload)
    assert result["status"] == "success"
    assert "invoice_id" in result
    
    # Verificar que el folio se cerró en memoria
    guest = memory.get_guest("G001")
    assert guest["billing"]["status"] == "cerrada"
