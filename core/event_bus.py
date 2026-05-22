"""
Event Bus del Hotel Inteligente.

Implementa un sistema de eventos publish-subscribe para la comunicación
asíncrona entre agentes. Cada evento se registra con timestamp, agente
emisor, tipo de evento y datos asociados.

Eventos soportados:
    - reserva_solicitada, reserva_confirmada, reserva_rechazada
    - checkin_iniciado, checkin_validado, checkin_rechazado
    - solicitud_servicio_creada, solicitud_servicio_resuelta, solicitud_servicio_escalada
    - checkout_iniciado, factura_generada, checkout_confirmado
    - feedback_recibido, promocion_generada
    - conflicto_detectado, escalamiento_humano_requerido
"""

import uuid
from datetime import datetime
from typing import Any


class EventBus:
    """
    Bus de eventos central del sistema multiagente.

    Permite publicar, listar y filtrar eventos generados por los agentes
    durante el ciclo de servicio del huésped.
    """

    def __init__(self):
        """Inicializa el event bus con un registro vacío de eventos."""
        self._events: list[dict[str, Any]] = []
        self._subscribers: dict[str, list] = {}

    def publish(
        self,
        event_type: str,
        agent_id: str,
        guest_id: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        """
        Publica un evento en el bus.

        Args:
            event_type: Tipo de evento (ej: 'reserva_confirmada').
            agent_id: ID del agente emisor.
            guest_id: ID del huésped asociado.
            data: Datos adicionales del evento.

        Returns:
            El evento publicado con su ID y timestamp.
        """
        event = {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "agent_id": agent_id,
            "guest_id": guest_id,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        }
        self._events.append(event)

        # Notificar a suscriptores
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(event)
                except Exception:
                    pass  # No interrumpir el flujo por errores en suscriptores

        return event

    def subscribe(self, event_type: str, callback) -> None:
        """
        Suscribe un callback a un tipo de evento.

        Args:
            event_type: Tipo de evento al que suscribirse.
            callback: Función a ejecutar cuando se publique el evento.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def get_all_events(self) -> list[dict[str, Any]]:
        """Retorna todos los eventos registrados."""
        return list(self._events)

    def get_events_by_guest(self, guest_id: str) -> list[dict[str, Any]]:
        """
        Filtra eventos por ID de huésped.

        Args:
            guest_id: ID del huésped.

        Returns:
            Lista de eventos asociados al huésped.
        """
        return [e for e in self._events if e["guest_id"] == guest_id]

    def get_events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """
        Filtra eventos por tipo.

        Args:
            event_type: Tipo de evento a filtrar.

        Returns:
            Lista de eventos del tipo especificado.
        """
        return [e for e in self._events if e["event_type"] == event_type]

    def get_events_by_agent(self, agent_id: str) -> list[dict[str, Any]]:
        """
        Filtra eventos por agente emisor.

        Args:
            agent_id: ID del agente.

        Returns:
            Lista de eventos publicados por el agente.
        """
        return [e for e in self._events if e["agent_id"] == agent_id]

    def get_event_count(self) -> int:
        """Retorna el número total de eventos registrados."""
        return len(self._events)

    def get_events_summary(self) -> dict[str, int]:
        """
        Retorna un resumen con la cantidad de eventos por tipo.

        Returns:
            Diccionario {tipo_evento: cantidad}.
        """
        summary: dict[str, int] = {}
        for event in self._events:
            t = event["event_type"]
            summary[t] = summary.get(t, 0) + 1
        return summary

    def clear(self) -> None:
        """Limpia todos los eventos del bus (útil para testing)."""
        self._events.clear()
        self._subscribers.clear()
