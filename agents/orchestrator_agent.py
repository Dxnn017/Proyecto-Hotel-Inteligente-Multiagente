"""
Agente Orquestador del Hotel Inteligente.

PROMPT DE SISTEMA:
==================
Rol: Agente central y orquestador del sistema multiagente del hotel.

Responsabilidades:
- Recibir TODAS las solicitudes del huésped (texto simulado o estructurado).
- Identificar la intención (reserva, check-in, servicio, etc.).
- Elegir el subagente correcto (pipeline).
- Validar esquemas JSON y enviar mensajes estructurados a subagentes.
- Actualizar historial de conversación y publicar eventos de enrutamiento.
- Detectar si una intención requiere la colaboración de varios agentes (Swarms).
- Llamar al Resolvedor de Conflictos si un subagente reporta un conflicto.
- Devolver la respuesta final al huésped.

Entradas esperadas:
- Petición del huésped: {guest_id, intent_hint, raw_text, payload}

Salidas esperadas:
- Respuesta unificada hacia el huésped.
"""

import json
import os
import time
import uuid
from typing import Any

import jsonschema

from config.settings import (
    ORCHESTRATOR_ID,
    INTENT_AGENT_MAP,
    SCHEMAS_DIR,
)
from core.conflict_resolver import ConflictResolver
from core.swarm_manager import SwarmManager

from agents.reservation_agent import ReservationAgent
from agents.checkin_agent import CheckinAgent
from agents.customer_service_agent import CustomerServiceAgent
from agents.billing_agent import BillingAgent
from agents.feedback_agent import FeedbackAgent


class OrchestratorAgent:
    """Orquestador central del hotel."""

    AGENT_ID = ORCHESTRATOR_ID

    def __init__(self, shared_memory, event_bus, conversation_history, metrics_logger=None):
        self.memory = shared_memory
        self.event_bus = event_bus
        self.history = conversation_history
        self.metrics_logger = metrics_logger
        
        self.conflict_resolver = ConflictResolver(self.memory, self.event_bus)
        self.swarm_manager = SwarmManager(self.memory, self.event_bus)
        
        # Instanciar subagentes
        self.agents = {
            ReservationAgent.AGENT_ID: ReservationAgent(self.memory, self.event_bus),
            CheckinAgent.AGENT_ID: CheckinAgent(self.memory, self.event_bus),
            CustomerServiceAgent.AGENT_ID: CustomerServiceAgent(self.memory, self.event_bus),
            BillingAgent.AGENT_ID: BillingAgent(self.memory, self.event_bus),
            FeedbackAgent.AGENT_ID: FeedbackAgent(self.memory, self.event_bus),
        }
        
        # Cargar schemas
        self.schemas = self._load_schemas()
        
        # Inicializar protocolo MCP y registrar herramientas
        from mcp.protocol import MCPProtocol
        from mcp.tools import register_hotel_mcp_tools
        self.mcp_protocol = MCPProtocol()
        register_hotel_mcp_tools(self.mcp_protocol, self)

    def _load_schemas(self) -> dict:
        schemas = {}
        schema_map = {
            ReservationAgent.AGENT_ID: "reservation_schema.json",
            CheckinAgent.AGENT_ID: "checkin_schema.json",
            CustomerServiceAgent.AGENT_ID: "service_request_schema.json",
            BillingAgent.AGENT_ID: "billing_schema.json",
            FeedbackAgent.AGENT_ID: "feedback_schema.json",
        }
        
        for agent_id, file_name in schema_map.items():
            path = os.path.join(SCHEMAS_DIR, file_name)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    schemas[agent_id] = json.load(f)
        return schemas

    def process_request(self, request: dict) -> dict[str, Any]:
        """Punto de entrada principal para peticiones del huésped."""
        start_time = time.time()
        
        guest_id = request.get("guest_id")
        intent = request.get("intent_hint", "").lower()
        payload = request.get("payload", {})
        raw_text = request.get("raw_text", "")
        
        # 1. Registrar entrada
        self.history.record(guest_id, "guest", "inbound", raw_text, "text", {"intent": intent})
        
        # 2. Determinar agente o swarm
        # Simulación de Swarm trigger
        is_swarm, swarm_def = self._detect_swarm(intent, payload)
        
        if is_swarm:
            result = self._handle_swarm(guest_id, swarm_def)
            result["response_message"] = f"Swarm ejecutado: {result['summary']}"
            target_agent = "swarm_manager"
        else:
            # Flujo pipeline normal
            target_agent = self._route_intent(intent)
            
            if not target_agent:
                return self._finalize(guest_id, target_agent, start_time, {"error": "Intención no reconocida"}, False)

            # --- LLAMADA A TRAVÉS DE LA CAPA MCP ---
            # Preparamos una petición JSON-RPC 2.0 estándar de MCP: method = "tools/call"
            mcp_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": target_agent,
                    "arguments": payload
                },
                "id": f"mcp-{uuid.uuid4().hex[:8]}"
            }
            
            sub_start = time.time()
            mcp_response = self.mcp_protocol.handle_request(mcp_request)
            sub_latency = time.time() - sub_start
            
            if self.metrics_logger:
                self.metrics_logger.log_latency(target_agent, sub_latency)
                
            # Procesamos la respuesta MCP
            if "error" in mcp_response:
                # Ocurrió un error en el protocolo o ejecución
                err = mcp_response["error"]
                return self._finalize(
                    guest_id, 
                    target_agent, 
                    start_time, 
                    {"status": "system_error", "error": err["message"], "response_message": err["message"]}, 
                    False
                )
            
            # El resultado de la herramienta está dentro de result
            result = mcp_response["result"]
            
            # Si el validador de MCP retornó un fallo de validación
            if result.get("status") == "failed" and "Error de validación JSON" in result.get("error", ""):
                return self._finalize(guest_id, target_agent, start_time, result, True)

            response_msg = result.get("response_message", "Procesado correctamente.")
            
            if result.get("status") == "escalated":
                if self.metrics_logger:
                    self.metrics_logger.log_escalation()
                if "conflict_type" in result:
                    conflict_res = self.conflict_resolver.check_and_resolve(
                        result["conflict_type"], guest_id, result
                    )
                    response_msg += f"\n[Conflicto Resuelto: {conflict_res['action']}]"
                    result["conflict_resolution"] = conflict_res
                    if self.metrics_logger:
                        self.metrics_logger.log_conflict()


        # 6. Registrar salida y retornar
        return self._finalize(guest_id, target_agent, start_time, result, True)

    def _route_intent(self, intent: str) -> str | None:
        """Enruta la intención al subagente correcto."""
        for key, agent_id in INTENT_AGENT_MAP.items():
            if key in intent:
                return agent_id
        return None

    def _detect_swarm(self, intent: str, payload: dict) -> tuple[bool, dict]:
        """Detecta si la petición requiere múltiples agentes (Swarms)."""
        # Caso Swarm 1: Salida con queja (checkout + feedback)
        if "checkout" in intent and "queja" in intent:
            return True, {
                "name": "checkout_y_feedback",
                "tasks": [
                    {"agent_id": BillingAgent.AGENT_ID, "task_type": "checkout", "payload": payload.get("billing", {})},
                    {"agent_id": FeedbackAgent.AGENT_ID, "task_type": "feedback", "payload": payload.get("feedback", {})}
                ]
            }
        return False, {}

    def _handle_swarm(self, guest_id: str, swarm_def: dict) -> dict:
        swarm = self.swarm_manager.create_swarm(
            swarm_def["name"], guest_id, swarm_def["tasks"]
        )
        if self.metrics_logger:
            self.metrics_logger.log_swarm()
        return self.swarm_manager.execute_swarm(swarm, self.agents)

    def _finalize(self, guest_id: str, agent_id: str, start_time: float, result: dict, success: bool) -> dict:
        """Empaqueta la respuesta y registra métricas."""
        latency = time.time() - start_time
        msg = result.get("response_message", result.get("error", "Error desconocido"))
        
        self.history.record(guest_id, self.AGENT_ID, "outbound", msg, "json", result)
        
        if self.metrics_logger:
            self.metrics_logger.log_latency(self.AGENT_ID, latency)
            if success:
                self.metrics_logger.log_success()
            else:
                self.metrics_logger.log_error()
                
            # Token usage simulado (100 in, 100 out)
            self.metrics_logger.log_tokens(200)

        return {
            "orchestrator_latency_sec": round(latency, 3),
            "target_agent": agent_id,
            "success": success,
            "response": result,
            "final_message": msg
        }
