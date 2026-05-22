"""
Agente de Atención al Cliente del Hotel Inteligente.

PROMPT DE SISTEMA:
==================
Rol: Agente especializado en atención al cliente durante la estadía.

Responsabilidades:
- Atender consultas y solicitudes durante la estadía del huésped.
- Clasificar solicitudes: limpieza, mantenimiento, toallas, restaurante,
  información turística, room service, reclamo.
- Resolver solicitudes simples automáticamente (limpieza, toallas, info, restaurante).
- Escalar al personal humano solicitudes complejas (mantenimiento, reclamos).
- Registrar estado de cada solicitud.
- Publicar eventos: solicitud_servicio_creada, solicitud_servicio_resuelta,
  escalamiento_humano_requerido.

Límites de acción:
- NO puede facturar ni procesar pagos.
- NO puede analizar feedback final ni generar promociones.
- NO puede registrar reservas nuevas.
- NO puede gestionar check-in ni check-out.

Entradas esperadas:
- JSON con action: crear_solicitud | resolver_solicitud | escalar_solicitud | consultar_estado
- Datos: guest_id, service_category, description, priority, room_number

Salidas esperadas:
- JSON con status: success | failed | escalated
- Incluye: request_id, resolution_status, response_message

Formato JSON obligatorio: Sí, según service_request_schema.json

Casos de escalamiento:
- Mantenimiento de infraestructura → escalar a equipo técnico.
- Reclamos graves → escalar a gerente de servicio.
- Solicitud ambigua no clasificable → solicitar más información.

Eventos que puede publicar:
- solicitud_servicio_creada
- solicitud_servicio_resuelta
- solicitud_servicio_escalada
- escalamiento_humano_requerido

Datos de memoria que puede leer/modificar:
- LEER: perfil del huésped, habitación asignada, solicitudes previas.
- MODIFICAR: solicitudes de servicio, estado de servicio.
"""

import uuid
from datetime import datetime
from typing import Any

from config.settings import (
    AUTO_RESOLVE_CATEGORIES,
    CUSTOMER_SERVICE_AGENT_ID,
    ESCALATION_CATEGORIES,
    SERVICE_CATEGORIES,
)


class CustomerServiceAgent:
    """
    Agente de Atención al Cliente: gestiona solicitudes de servicio durante la estadía.
    """

    AGENT_ID = CUSTOMER_SERVICE_AGENT_ID
    AGENT_NAME = "Agente de Atención al Cliente"

    # Respuestas automáticas para categorías resolubles
    AUTO_RESPONSES = {
        "limpieza": "Se ha programado el servicio de limpieza para su habitación. El equipo llegará en los próximos 20 minutos.",
        "toallas": "Se enviarán toallas limpias a su habitación en los próximos 10 minutos.",
        "informacion_turistica": "Le enviaremos una guía digital con atracciones turísticas, restaurantes y actividades recomendadas en la zona.",
        "restaurante": "Nuestro restaurante principal está abierto de 7:00 a 22:00. Le enviamos el menú digital a su dispositivo.",
        "room_service": "Su pedido de room service ha sido registrado. Tiempo estimado de entrega: 25-35 minutos.",
    }

    ESTIMATED_TIMES = {
        "limpieza": "20 minutos",
        "toallas": "10 minutos",
        "informacion_turistica": "Inmediato (digital)",
        "restaurante": "Información inmediata",
        "room_service": "25-35 minutos",
        "mantenimiento": "Requiere evaluación técnica (1-4 horas)",
        "reclamo": "Se asigna un supervisor para atender su caso",
    }

    def __init__(self, shared_memory, event_bus):
        self.memory = shared_memory
        self.event_bus = event_bus

    def process(self, payload: dict) -> dict[str, Any]:
        """
        Procesa una solicitud de servicio.

        Args:
            payload: Diccionario con action y datos de la solicitud.

        Returns:
            Resultado del procesamiento.
        """
        action = payload.get("action", "crear_solicitud")

        if action == "crear_solicitud":
            return self._create_request(payload)
        elif action == "resolver_solicitud":
            return self._resolve_request(payload)
        elif action == "escalar_solicitud":
            return self._escalate_request(payload)
        elif action == "consultar_estado":
            return self._query_status(payload)
        else:
            return {
                "status": "failed",
                "action": action,
                "response_message": f"Acción no reconocida: {action}",
            }

    def _create_request(self, payload: dict) -> dict[str, Any]:
        """Crea y procesa una solicitud de servicio."""
        guest_id = payload.get("guest_id", "")
        category = payload.get("service_category", "")
        description = payload.get("description", "")
        room_number = payload.get("room_number", "")
        priority = payload.get("priority", "media")

        # Validar categoría
        if category not in SERVICE_CATEGORIES:
            return {
                "status": "failed",
                "action": "crear_solicitud",
                "response_message": (
                    f"Categoría de servicio no reconocida: '{category}'. "
                    f"Categorías disponibles: {', '.join(SERVICE_CATEGORIES)}."
                ),
            }

        # Crear solicitud
        request_id = f"SR-{uuid.uuid4().hex[:8]}"
        request = {
            "request_id": request_id,
            "service_category": category,
            "description": description,
            "priority": priority,
            "room_number": room_number,
            "status": "pendiente",
        }

        # Publicar evento de creación
        self.event_bus.publish(
            "solicitud_servicio_creada", self.AGENT_ID, guest_id,
            {"request_id": request_id, "category": category},
        )

        # Determinar si se resuelve automáticamente o se escala
        if category in AUTO_RESOLVE_CATEGORIES:
            return self._auto_resolve(guest_id, request)
        elif category in ESCALATION_CATEGORIES:
            return self._auto_escalate(guest_id, request)
        else:
            # Categoría desconocida -> solicitar más info
            request["status"] = "pendiente"
            self.memory.register_service_request(guest_id, request)
            return {
                "status": "pending",
                "action": "crear_solicitud",
                "request_id": request_id,
                "response_message": "Su solicitud ha sido registrada. Necesitamos más información para procesarla.",
            }

    def _auto_resolve(self, guest_id: str, request: dict) -> dict[str, Any]:
        """Resuelve automáticamente una solicitud simple."""
        category = request["service_category"]
        request["status"] = "resuelto"
        request["resolution_details"] = self.AUTO_RESPONSES.get(category, "Solicitud procesada.")

        # Registrar en memoria
        self.memory.register_service_request(guest_id, request)

        # Publicar evento
        self.event_bus.publish(
            "solicitud_servicio_resuelta", self.AGENT_ID, guest_id,
            {
                "request_id": request["request_id"],
                "category": category,
                "resolution": "automatica",
            },
        )

        return {
            "status": "success",
            "action": "crear_solicitud",
            "request_id": request["request_id"],
            "resolution_status": "resuelto",
            "service_category": category,
            "estimated_time": self.ESTIMATED_TIMES.get(category, "Pronto"),
            "response_message": self.AUTO_RESPONSES.get(category, "Solicitud procesada."),
        }

    def _auto_escalate(self, guest_id: str, request: dict) -> dict[str, Any]:
        """Escala automáticamente una solicitud compleja."""
        category = request["service_category"]
        request["status"] = "escalado"
        request["escalation_reason"] = f"Categoría {category} requiere atención especializada."

        # Registrar en memoria
        self.memory.register_service_request(guest_id, request)

        # Publicar eventos
        self.event_bus.publish(
            "solicitud_servicio_escalada", self.AGENT_ID, guest_id,
            {
                "request_id": request["request_id"],
                "category": category,
                "reason": request["escalation_reason"],
            },
        )
        self.event_bus.publish(
            "escalamiento_humano_requerido", self.AGENT_ID, guest_id,
            {
                "request_id": request["request_id"],
                "category": category,
            },
        )

        return {
            "status": "escalated",
            "action": "crear_solicitud",
            "request_id": request["request_id"],
            "resolution_status": "escalado",
            "service_category": category,
            "escalation_reason": request["escalation_reason"],
            "estimated_time": self.ESTIMATED_TIMES.get(category, "Variable"),
            "requires_human": True,
            "response_message": (
                f"Su solicitud de {category} ha sido registrada y escalada al equipo especializado. "
                f"Tiempo estimado: {self.ESTIMATED_TIMES.get(category, 'Variable')}. "
                "Un miembro del personal se comunicará con usted."
            ),
        }

    def _resolve_request(self, payload: dict) -> dict[str, Any]:
        """Marca una solicitud como resuelta."""
        guest_id = payload.get("guest_id", "")
        request_id = payload.get("request_id", "")
        details = payload.get("resolution_details", "Solicitud resuelta.")

        success = self.memory.update_service_request(
            guest_id, request_id, "resuelto", details
        )

        if success:
            self.event_bus.publish(
                "solicitud_servicio_resuelta", self.AGENT_ID, guest_id,
                {"request_id": request_id},
            )
            return {
                "status": "success",
                "action": "resolver_solicitud",
                "request_id": request_id,
                "resolution_status": "resuelto",
                "response_message": f"Solicitud {request_id} resuelta: {details}",
            }

        return {
            "status": "failed",
            "action": "resolver_solicitud",
            "response_message": f"No se pudo resolver la solicitud {request_id}.",
        }

    def _escalate_request(self, payload: dict) -> dict[str, Any]:
        """Escala una solicitud manualmente."""
        guest_id = payload.get("guest_id", "")
        request_id = payload.get("request_id", "")
        reason = payload.get("escalation_reason", "Requiere intervención humana")

        self.memory.update_service_request(guest_id, request_id, "escalado", reason)

        self.event_bus.publish(
            "escalamiento_humano_requerido", self.AGENT_ID, guest_id,
            {"request_id": request_id, "reason": reason},
        )

        return {
            "status": "escalated",
            "action": "escalar_solicitud",
            "request_id": request_id,
            "requires_human": True,
            "response_message": f"Solicitud {request_id} escalada: {reason}",
        }

    def _query_status(self, payload: dict) -> dict[str, Any]:
        """Consulta el estado de las solicitudes de un huésped."""
        guest_id = payload.get("guest_id", "")
        guest = self.memory.get_guest(guest_id)

        if not guest:
            return {
                "status": "failed",
                "action": "consultar_estado",
                "response_message": "Huésped no encontrado.",
            }

        requests = guest.get("service_requests", [])
        if not requests:
            return {
                "status": "success",
                "action": "consultar_estado",
                "response_message": "No tiene solicitudes de servicio registradas.",
            }

        summary = []
        for req in requests:
            summary.append(
                f"  - {req.get('request_id')}: {req.get('service_category')} → {req.get('status')}"
            )

        return {
            "status": "success",
            "action": "consultar_estado",
            "response_message": "Sus solicitudes de servicio:\n" + "\n".join(summary),
        }
