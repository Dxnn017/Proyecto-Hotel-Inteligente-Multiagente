"""
Demo Principal del Sistema Multiagente del Hotel Inteligente.

Este script orquesta una simulación completa de los 11 escenarios
requeridos en la rúbrica, demostrando el ciclo completo del huésped,
el uso de agentes, memoria compartida, event bus y swarms.
"""

import json
import os
import sys
from datetime import datetime

# Forzar UTF-8 para evitar errores de UnicodeEncodeError en Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Añadir el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.event_bus import EventBus
from core.shared_memory import SharedMemory
from core.conversation_history import ConversationHistory
from metrics.metrics_logger import MetricsLogger
from agents.orchestrator_agent import OrchestratorAgent


def print_step(title: str):
    print(f"\n{'-'*60}")
    print(f"🔹 {title}")
    print(f"{'-'*60}")


def print_result(result: dict):
    agent = result.get('target_agent', 'Desconocido')
    success = result.get('success', False)
    latency = result.get('orchestrator_latency_sec', 0.0)
    response = result.get('response', {})
    
    print(f"🤖 Agente Seleccionado: {agent}")
    print(f"⏱️  Latencia: {latency:.3f}s")
    print(f"✅ Éxito: {success}")
    print(f"💬 Respuesta Final:\n   {result.get('final_message')}")
    if response.get("conflict_resolution"):
        print(f"⚠️  Conflicto Detectado y Resuelto: {response['conflict_resolution']['action']}")


def run_demo():
    print("\n🏨 INICIANDO SISTEMA MULTIAGENTE HOTEL INTELIGENTE 🏨")
    print("=" * 65)

    # 1. Inicializar Infraestructura Core
    event_bus = EventBus()
    shared_memory = SharedMemory()
    conversation_history = ConversationHistory()
    metrics_logger = MetricsLogger()
    
    # 2. Inicializar Orquestador
    orchestrator = OrchestratorAgent(
        shared_memory=shared_memory,
        event_bus=event_bus,
        conversation_history=conversation_history,
        metrics_logger=metrics_logger
    )

    guest_id_new = "G_DEMO_01"  # Para casos nuevos
    guest_id_existing = "G001"  # Huésped que ya existe en el data/guests.json

    # =====================================================================
    # ESCENARIO 1: Reserva exitosa
    # =====================================================================
    print_step("1. Reserva Exitosa")
    req1 = {
        "guest_id": guest_id_new,
        "intent_hint": "Quiero reservar una habitación matrimonial",
        "raw_text": "Hola, necesito reservar una habitación matrimonial para 2 personas del 2026-06-01 al 2026-06-05.",
        "payload": {
            "action": "crear_reserva",
            "guest_name": "Juan Perez Demo",
            "guest_email": "juan.demo@email.com",
            "room_type": "matrimonial",
            "check_in_date": "2026-06-01",
            "check_out_date": "2026-06-05",
            "num_guests": 2
        }
    }
    res1 = orchestrator.process_request(req1)
    print_result(res1)
    # Actualizar ID para futuros pasos si se creó en memoria
    if res1["success"] and "reservation_id" in res1["response"]:
        # Find the guest by reservation id to keep consistency
        guest_id_new = shared_memory.find_guest_by_reservation(res1["response"]["reservation_id"]) or guest_id_new

    # =====================================================================
    # ESCENARIO 2: Reserva sin disponibilidad
    # =====================================================================
    print_step("2. Reserva Sin Disponibilidad")
    # Forzamos que las suites estén ocupadas en memoria primero
    for r in shared_memory._rooms:
        if r["room_type"] == "suite":
            r["status"] = "ocupada"
            
    req2 = {
        "guest_id": "G_DEMO_02",
        "intent_hint": "reservar suite",
        "payload": {
            "action": "crear_reserva",
            "guest_name": "Ana SinSuerte",
            "room_type": "suite",
            "check_in_date": "2026-07-01",
            "check_out_date": "2026-07-03",
            "num_guests": 2
        }
    }
    res2 = orchestrator.process_request(req2)
    print_result(res2)

    # =====================================================================
    # ESCENARIO 3: Check-in con datos válidos
    # =====================================================================
    print_step("3. Check-in con datos válidos")
    req3 = {
        "guest_id": guest_id_new,
        "intent_hint": "hacer check-in",
        "payload": {
            "action": "confirmar_checkin",
            "guest_id": guest_id_new
        }
    }
    res3 = orchestrator.process_request(req3)
    print_result(res3)

    # =====================================================================
    # ESCENARIO 4: Check-in con datos inválidos
    # =====================================================================
    print_step("4. Check-in con datos inválidos")
    req4 = {
        "guest_id": "G004", # Maria Torres, sin reserva en guests.json
        "intent_hint": "check-in identidad",
        "payload": {
            "action": "validar_identidad",
            "guest_id": "G004",
            "guest_name": "M",  # Muy corto
            "document_type": "dni",
            "document_number": "123" # Muy corto
        }
    }
    res4 = orchestrator.process_request(req4)
    print_result(res4)

    # =====================================================================
    # ESCENARIO 5: Solicitud de limpieza resuelta automáticamente
    # =====================================================================
    print_step("5. Solicitud de Limpieza (Auto-resolución)")
    req5 = {
        "guest_id": guest_id_new,
        "intent_hint": "pedir limpieza",
        "payload": {
            "action": "crear_solicitud",
            "guest_id": guest_id_new,
            "service_category": "limpieza",
            "description": "Por favor limpiar la habitación",
            "room_number": "201"
        }
    }
    res5 = orchestrator.process_request(req5)
    print_result(res5)

    # =====================================================================
    # ESCENARIO 6: Solicitud de mantenimiento escalada
    # =====================================================================
    print_step("6. Solicitud de Mantenimiento (Escalada)")
    req6 = {
        "guest_id": guest_id_new,
        "intent_hint": "mantenimiento aire acondicionado",
        "payload": {
            "action": "crear_solicitud",
            "guest_id": guest_id_new,
            "service_category": "mantenimiento",
            "description": "El aire acondicionado gotea agua",
            "room_number": "201"
        }
    }
    res6 = orchestrator.process_request(req6)
    print_result(res6)

    # =====================================================================
    # ESCENARIO 7: Check-out con consumos
    # =====================================================================
    print_step("7. Check-out y Facturación")
    # Registramos un consumo simulado primero
    shared_memory.register_consumption(guest_id_new, {
        "type": "minibar", "amount": 45.00, "description": "Snacks"
    })
    
    req7 = {
        "guest_id": guest_id_new,
        "intent_hint": "hacer checkout factura",
        "payload": {
            "action": "confirmar_checkout",
            "guest_id": guest_id_new,
            "payment_method": "tarjeta_credito"
        }
    }
    res7 = orchestrator.process_request(req7)
    print_result(res7)

    # =====================================================================
    # ESCENARIO 8: Feedback positivo con promoción
    # =====================================================================
    print_step("8. Feedback Positivo (Genera Promoción)")
    req8 = {
        "guest_id": guest_id_new,
        "intent_hint": "dejar feedback excelente",
        "payload": {
            "action": "recibir_feedback",
            "guest_id": guest_id_new,
            "rating": 5,
            "comment": "Todo fue excelente, me encantó la habitación y la comida."
        }
    }
    res8 = orchestrator.process_request(req8)
    print_result(res8)

    # =====================================================================
    # ESCENARIO 9: Feedback negativo con alerta
    # =====================================================================
    print_step("9. Feedback Negativo (Genera Alerta)")
    req9 = {
        "guest_id": "G005",
        "intent_hint": "dejar feedback malo",
        "payload": {
            "action": "recibir_feedback",
            "guest_id": "G005",
            "rating": 1,
            "comment": "Terrible servicio, mucho ruido y sucio."
        }
    }
    res9 = orchestrator.process_request(req9)
    print_result(res9)

    # =====================================================================
    # ESCENARIO 10: Conflicto de Habitación
    # =====================================================================
    print_step("10. Conflicto: Check-in a habitación ocupada")
    # Forzamos que la habitación asiganada a G003 (203) esté ocupada
    shared_memory.update_room_status("203", "ocupada")
    
    req10 = {
        "guest_id": "G003",
        "intent_hint": "hacer check-in",
        "payload": {
            "action": "confirmar_checkin",
            "guest_id": "G003"
        }
    }
    res10 = orchestrator.process_request(req10)
    print_result(res10)

    # =====================================================================
    # ESCENARIO 11: Swarm (Múltiples agentes colaborando)
    # =====================================================================
    print_step("11. Caso Swarm: Salida (Checkout) y Queja (Feedback) a la vez")
    req11 = {
        "guest_id": "G001",
        "intent_hint": "quiero hacer checkout y dejar una queja",
        "raw_text": "Me voy ahora mismo, la cama era terrible, quiero mi factura.",
        "payload": {
            "billing": {
                "action": "confirmar_checkout",
                "guest_id": "G001",
                "payment_method": "efectivo"
            },
            "feedback": {
                "action": "recibir_feedback",
                "guest_id": "G001",
                "rating": 2,
                "comment": "Me voy porque la cama era muy incómoda."
            }
        }
    }
    res11 = orchestrator.process_request(req11)
    print_result(res11)


    # =====================================================================
    # GUARDADO Y RESUMEN
    # =====================================================================
    print("\n" + "="*65)
    print("MÉTRICAS Y RESULTADOS FINALES")
    print("="*65)
    
    metrics_logger.save_metrics()
    metrics_logger.print_summary()
    
    print("\n📝 Eventos publicados en el bus:", event_bus.get_event_count())
    print("📝 Conflictos detectados:", orchestrator.conflict_resolver.get_conflict_count())
    print("📝 Swarms ejecutados:", orchestrator.swarm_manager.get_swarm_count())
    
    print("\n¡Demo completada exitosamente! Los resultados se guardaron en metrics/results.json")

if __name__ == "__main__":
    run_demo()
