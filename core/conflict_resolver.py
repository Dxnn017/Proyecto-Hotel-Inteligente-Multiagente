"""
Resolvedor de Conflictos del Hotel Inteligente.

Detecta y resuelve conflictos entre agentes o en los datos del sistema:
1. Reservas duplicadas activas para un mismo huésped.
2. Habitación asignada a dos huéspedes distintos.
3. Check-in sin reserva previa.
4. Consumos contradictorios o duplicados.
5. Feedback negativo con promoción automática.

Publica evento 'conflicto_detectado' y escala a humano cuando no puede resolver.
"""

import uuid
from datetime import datetime
from typing import Any

from config.settings import BILLING_AGENT_ID, CHECKIN_AGENT_ID, RESERVATION_AGENT_ID


class ConflictResolver:
    """
    Módulo de detección y resolución de conflictos del sistema multiagente.

    Analiza el estado de la memoria compartida y el event bus para
    identificar inconsistencias y aplicar estrategias de resolución.
    """

    def __init__(self, shared_memory, event_bus):
        """
        Inicializa el resolvedor de conflictos.

        Args:
            shared_memory: Instancia de SharedMemory.
            event_bus: Instancia de EventBus.
        """
        self.memory = shared_memory
        self.event_bus = event_bus
        self._conflict_log: list[dict[str, Any]] = []

    def check_and_resolve(
        self, conflict_type: str, guest_id: str, context: dict | None = None
    ) -> dict[str, Any]:
        """
        Verifica y resuelve un conflicto específico.

        Args:
            conflict_type: Tipo de conflicto a verificar.
            guest_id: ID del huésped involucrado.
            context: Contexto adicional para la resolución.

        Returns:
            Resultado de la resolución con status, action y detalles.
        """
        context = context or {}
        resolvers = {
            "reserva_duplicada": self._resolve_duplicate_reservation,
            "habitacion_ocupada": self._resolve_room_conflict,
            "checkin_sin_reserva": self._resolve_checkin_no_reservation,
            "consumo_contradictorio": self._resolve_contradictory_consumption,
            "feedback_negativo_promocion": self._resolve_negative_feedback_promotion,
        }

        resolver = resolvers.get(conflict_type)
        if not resolver:
            return {
                "conflict_type": conflict_type,
                "resolved": False,
                "action": "tipo_desconocido",
                "message": f"Tipo de conflicto desconocido: {conflict_type}",
                "requires_human": True,
            }

        result = resolver(guest_id, context)
        result["conflict_id"] = f"CF-{uuid.uuid4().hex[:8]}"
        result["conflict_type"] = conflict_type
        result["guest_id"] = guest_id
        result["timestamp"] = datetime.now().isoformat()

        # Registrar en log interno
        self._conflict_log.append(result)

        # Publicar evento
        self.event_bus.publish(
            event_type="conflicto_detectado",
            agent_id="conflict_resolver",
            guest_id=guest_id,
            data={
                "conflict_type": conflict_type,
                "resolved": result["resolved"],
                "action": result["action"],
                "requires_human": result.get("requires_human", False),
            },
        )

        # Si requiere humano, publicar escalamiento
        if result.get("requires_human"):
            self.event_bus.publish(
                event_type="escalamiento_humano_requerido",
                agent_id="conflict_resolver",
                guest_id=guest_id,
                data={
                    "reason": result.get("message", "Conflicto no resuelto automáticamente"),
                    "conflict_type": conflict_type,
                },
            )

        return result

    def _resolve_duplicate_reservation(
        self, guest_id: str, context: dict
    ) -> dict[str, Any]:
        """
        Resuelve conflicto de reservas duplicadas.

        Estrategia: Usar la reserva con fecha de check-in más cercana.
        Si no se puede resolver, escalar a humano.
        """
        guest = self.memory.get_guest(guest_id)
        if not guest or not guest["reservation"]:
            return {
                "resolved": True,
                "action": "sin_conflicto",
                "message": "No se encontraron reservas duplicadas.",
                "requires_human": False,
            }

        # Si hay reservas duplicadas en el contexto
        reservations = context.get("reservations", [])
        if len(reservations) <= 1:
            return {
                "resolved": True,
                "action": "sin_conflicto",
                "message": "Solo hay una reserva activa.",
                "requires_human": False,
            }

        # Seleccionar la más cercana a la fecha actual
        now = datetime.now().strftime("%Y-%m-%d")
        sorted_res = sorted(
            reservations,
            key=lambda r: abs(
                (datetime.strptime(r.get("check_in_date", now), "%Y-%m-%d") - datetime.now()).days
            ),
        )
        selected = sorted_res[0]

        return {
            "resolved": True,
            "action": "seleccionar_reserva_cercana",
            "message": f"Se seleccionó la reserva {selected.get('reservation_id')} por ser la más cercana.",
            "selected_reservation": selected,
            "requires_human": False,
        }

    def _resolve_room_conflict(
        self, guest_id: str, context: dict
    ) -> dict[str, Any]:
        """
        Resuelve conflicto de habitación ya asignada.

        Estrategia: Buscar otra habitación disponible del mismo tipo.
        Si no hay, escalar a humano.
        """
        room_id = context.get("room_id", "")
        room_type = context.get("room_type", "")

        # Buscar otra habitación disponible del mismo tipo
        available = self.memory.get_available_rooms(room_type)
        available = [r for r in available if r["room_id"] != room_id]

        if available:
            new_room = available[0]
            return {
                "resolved": True,
                "action": "reasignar_habitacion",
                "message": f"Habitación {room_id} ocupada. Se reasigna a {new_room['room_id']}.",
                "new_room": new_room,
                "requires_human": False,
            }

        # Si no hay del mismo tipo, buscar cualquier disponible
        all_available = self.memory.get_available_rooms()
        all_available = [r for r in all_available if r["room_id"] != room_id]

        if all_available:
            new_room = all_available[0]
            return {
                "resolved": True,
                "action": "reasignar_habitacion_diferente_tipo",
                "message": f"No hay {room_type} disponible. Se ofrece {new_room['room_type']} (hab. {new_room['room_id']}).",
                "new_room": new_room,
                "requires_human": False,
            }

        return {
            "resolved": False,
            "action": "escalar_sin_disponibilidad",
            "message": "No hay habitaciones disponibles. Se escala a recepción.",
            "requires_human": True,
        }

    def _resolve_checkin_no_reservation(
        self, guest_id: str, context: dict
    ) -> dict[str, Any]:
        """
        Resuelve intento de check-in sin reserva.

        Estrategia: Rechazar check-in y redirigir al agente de reservas.
        """
        return {
            "resolved": True,
            "action": "redirigir_a_reservas",
            "message": "El huésped no tiene reserva. Se redirige al Agente de Reservas para crear una.",
            "redirect_to": RESERVATION_AGENT_ID,
            "requires_human": False,
        }

    def _resolve_contradictory_consumption(
        self, guest_id: str, context: dict
    ) -> dict[str, Any]:
        """
        Resuelve consumos contradictorios o duplicados.

        Estrategia: Marcar factura para revisión humana.
        """
        consumption_id = context.get("consumption_id", "")
        is_duplicate = self.memory.has_duplicate_consumption(guest_id, consumption_id)

        if is_duplicate:
            return {
                "resolved": False,
                "action": "marcar_revision_humana",
                "message": f"Consumo {consumption_id} aparece duplicado. Factura marcada para revisión.",
                "requires_human": True,
            }

        return {
            "resolved": True,
            "action": "sin_conflicto",
            "message": "No se encontraron consumos contradictorios.",
            "requires_human": False,
        }

    def _resolve_negative_feedback_promotion(
        self, guest_id: str, context: dict
    ) -> dict[str, Any]:
        """
        Resuelve caso de feedback negativo con intento de promoción.

        Estrategia: No enviar promoción directa, generar alerta de seguimiento.
        """
        sentiment = context.get("sentiment", "neutral")

        if sentiment == "negativo":
            return {
                "resolved": True,
                "action": "generar_alerta_seguimiento",
                "message": "Feedback negativo detectado. No se genera promoción directa. Se crea alerta de seguimiento para el gerente.",
                "alert": {
                    "type": "seguimiento_feedback_negativo",
                    "priority": "alta",
                    "assigned_to": "gerente_servicio",
                    "guest_id": guest_id,
                },
                "requires_human": False,
            }

        return {
            "resolved": True,
            "action": "sin_conflicto",
            "message": "El feedback no es negativo, se puede proceder con promoción.",
            "requires_human": False,
        }

    def get_conflict_log(self) -> list[dict[str, Any]]:
        """Retorna el log de todos los conflictos detectados."""
        return list(self._conflict_log)

    def get_conflict_count(self) -> int:
        """Retorna el número total de conflictos detectados."""
        return len(self._conflict_log)

    def get_unresolved_conflicts(self) -> list[dict[str, Any]]:
        """Retorna los conflictos no resueltos."""
        return [c for c in self._conflict_log if not c.get("resolved")]

    def clear(self) -> None:
        """Limpia el log de conflictos."""
        self._conflict_log.clear()
