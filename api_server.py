"""
API Server – FastAPI backend para el Hotel Inteligente.

Expone endpoints REST que delegan al Agente Orquestador existente.
Sirve el frontend estático desde la carpeta ui/.
"""

import json
import os
import sys
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Asegurar que el directorio raíz está en sys.path ──────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ── Importaciones del proyecto ────────────────────────────────
from core.event_bus import EventBus
from core.shared_memory import SharedMemory
from core.conversation_history import ConversationHistory
from metrics.metrics_logger import MetricsLogger
from agents.orchestrator_agent import OrchestratorAgent

# ── Instanciar infraestructura (singleton en el proceso) ──────
event_bus = EventBus()
shared_memory = SharedMemory()
conversation_history = ConversationHistory()
metrics_logger = MetricsLogger()

orchestrator = OrchestratorAgent(
    shared_memory=shared_memory,
    event_bus=event_bus,
    conversation_history=conversation_history,
    metrics_logger=metrics_logger,
)

# ── FastAPI app ───────────────────────────────────────────────
app = FastAPI(title="Hotel Inteligente API", version="1.0.0")

UI_DIR = os.path.join(BASE_DIR, "ui")

# ── Archivos estáticos ────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(os.path.join(UI_DIR, "index.html"))

@app.get("/styles.css")
async def styles():
    return FileResponse(os.path.join(UI_DIR, "styles.css"), media_type="text/css")

@app.get("/app.js")
async def js():
    return FileResponse(os.path.join(UI_DIR, "app.js"), media_type="application/javascript")


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _call_orchestrator(intent: str, payload: dict, guest_id: str | None = None):
    """Wrapper seguro alrededor del orquestador."""
    gid = guest_id or payload.get("guest_id") or f"G{uuid.uuid4().hex[:6].upper()}"
    req = {
        "guest_id": gid,
        "intent_hint": intent,
        "raw_text": f"Solicitud web: {intent}",
        "payload": payload,
    }

    # Capturar MCP envelope para el panel técnico
    target_agent = orchestrator._route_intent(intent.lower()) or "unknown"
    mcp_sent = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": target_agent, "arguments": payload},
        "id": f"mcp-{uuid.uuid4().hex[:8]}",
    }

    try:
        result = orchestrator.process_request(req)
        metrics_logger.save_metrics()
    except Exception as e:
        return {
            "success": False,
            "final_message": "Ocurrió un error interno. Contacte a soporte.",
            "target_agent": target_agent,
            "mcp_request": mcp_sent,
            "mcp_response": {"error": str(e)},
        }

    mcp_received = {
        "jsonrpc": "2.0",
        "result": result.get("response", result) if isinstance(result, dict) else result,
        "id": mcp_sent["id"],
    }

    return {
        **result,
        "mcp_request": mcp_sent,
        "mcp_response": mcp_received,
    }


# ══════════════════════════════════════════════════════════════
# DASHBOARD / INFO
# ══════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
async def dashboard():
    """KPIs de negocio en tiempo real."""
    guests = getattr(shared_memory, "_guests", {})
    rooms = getattr(shared_memory, "_rooms", [])

    h_disp = len([r for r in rooms if r.get("status") == "disponible"])
    reservas = len(shared_memory.get_active_reservations())
    checkins = len([g for g in guests.values() if g.get("stage") in ("checkin_completado", "en_estadia", "checkout_completado")])
    solicitudes = sum(len(g.get("service_requests", [])) for g in guests.values())
    facturas = len([g for g in guests.values() if g.get("stage") == "checkout_completado"])
    feedbacks = len([g for g in guests.values() if g.get("feedback", {}).get("submitted")])

    m = getattr(metrics_logger, "metrics", {})

    return {
        "rooms_available": h_disp,
        "rooms_total": len(rooms),
        "active_reservations": reservas,
        "checkins_today": checkins,
        "service_requests": solicitudes,
        "invoices": facturas,
        "feedbacks": feedbacks,
        "human_escalations": m.get("human_escalations", 0),
        "swarms_executed": m.get("swarms_executed", 0),
    }


# ══════════════════════════════════════════════════════════════
# ENDPOINTS DE NEGOCIO
# ══════════════════════════════════════════════════════════════

@app.post("/api/reservations")
async def create_reservation(req: Request):
    body = await req.json()
    payload = {
        "action": "crear_reserva",
        "guest_name": body.get("guest_name", ""),
        "guest_email": body.get("guest_email", ""),
        "document_number": body.get("document_number", ""),
        "phone": body.get("phone", ""),
        "room_type": body.get("room_type", "simple"),
        "num_guests": body.get("num_guests", 1),
        "check_in_date": body.get("check_in_date", ""),
        "check_out_date": body.get("check_out_date", ""),
    }
    return JSONResponse(_call_orchestrator(f"reservar habitacion {payload['room_type']}", payload))


@app.post("/api/checkin")
async def checkin(req: Request):
    body = await req.json()
    guest_id = body.get("guest_id", "")
    name = body.get("guest_name", "")
    doc = body.get("document_number", "")

    if name and doc:
        payload = {"action": "validar_identidad", "guest_id": guest_id, "guest_name": name, "document_type": "dni", "document_number": doc}
        intent = "check-in identidad"
    else:
        payload = {"action": "confirmar_checkin", "guest_id": guest_id}
        intent = "hacer check-in"

    return JSONResponse(_call_orchestrator(intent, payload, guest_id))


@app.post("/api/service-request")
async def service_request(req: Request):
    body = await req.json()
    guest_id = body.get("guest_id", "")
    category = body.get("service_category", "limpieza")
    payload = {
        "action": "crear_solicitud",
        "guest_id": guest_id,
        "room_number": body.get("room_number", ""),
        "service_category": category,
        "description": body.get("description", f"Solicitud de {category}"),
    }
    return JSONResponse(_call_orchestrator(f"pedir {category}", payload, guest_id))


@app.post("/api/billing")
async def billing(req: Request):
    body = await req.json()
    guest_id = body.get("guest_id", "")

    # Registrar consumos extras antes de facturar
    consumptions = body.get("consumptions", [])
    for c in consumptions:
        if c.get("amount", 0) > 0:
            shared_memory.register_consumption(guest_id, {"type": c.get("type", "otros"), "amount": c["amount"], "description": c.get("description", "")})

    payload = {"action": "confirmar_checkout", "guest_id": guest_id, "payment_method": body.get("payment_method", "efectivo")}
    return JSONResponse(_call_orchestrator("hacer checkout factura", payload, guest_id))


@app.post("/api/feedback")
async def feedback(req: Request):
    body = await req.json()
    guest_id = body.get("guest_id", "")
    rating = body.get("rating", 3)
    payload = {
        "action": "recibir_feedback",
        "guest_id": guest_id,
        "rating": rating,
        "comment": body.get("comment", ""),
    }
    intent = "dejar feedback excelente" if rating >= 4 else "dejar feedback malo"
    return JSONResponse(_call_orchestrator(intent, payload, guest_id))


@app.post("/api/swarm/checkout-complaint")
async def swarm_checkout_complaint(req: Request):
    body = await req.json()
    guest_id = body.get("guest_id", "G001")
    payload = {
        "billing": {"action": "confirmar_checkout", "guest_id": guest_id, "payment_method": body.get("payment_method", "efectivo")},
        "feedback": {"action": "recibir_feedback", "guest_id": guest_id, "rating": body.get("rating", 2), "comment": body.get("comment", "Servicio regular.")},
    }

    mcp_sent = {"swarm_orchestration": "SwarmManager activado", "tasks": [{"agent_id": "billing_agent", "payload": payload["billing"]}, {"agent_id": "feedback_agent", "payload": payload["feedback"]}]}

    r = {
        "guest_id": guest_id,
        "intent_hint": "quiero hacer checkout y dejar una queja",
        "raw_text": "Swarm: checkout + queja",
        "payload": payload,
    }

    try:
        result = orchestrator.process_request(r)
        metrics_logger.save_metrics()
    except Exception:
        return JSONResponse({"success": False, "final_message": "Error interno al ejecutar Swarm."})

    return JSONResponse({**result, "mcp_request": mcp_sent, "mcp_response": {"swarm_status": "completed", "results": result.get("response", {})}})


# ══════════════════════════════════════════════════════════════
# PANEL TÉCNICO
# ══════════════════════════════════════════════════════════════

@app.get("/api/events")
async def events():
    return JSONResponse(event_bus.get_all_events())


@app.get("/api/memory")
async def memory():
    ids = shared_memory.get_all_guest_ids()
    data = {}
    for gid in ids:
        g = shared_memory.get_guest(gid)
        if g:
            data[gid] = g
    return JSONResponse(data)


@app.get("/api/metrics")
async def metrics():
    path = os.path.join(BASE_DIR, "metrics", "results.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return JSONResponse(json.load(f))
    return JSONResponse({"message": "Sin métricas disponibles."})


@app.get("/api/conflicts")
async def conflicts():
    resolver = getattr(orchestrator, "conflict_resolver", None)
    log = getattr(resolver, "_conflict_log", []) if resolver else []
    return JSONResponse(log)


@app.get("/api/swarms")
async def swarms():
    mgr = getattr(orchestrator, "swarm_manager", None)
    history = mgr.get_swarm_history() if mgr else []
    return JSONResponse(history)
