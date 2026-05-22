"""
Historial de Conversación del Hotel Inteligente.

Registra y gestiona todas las interacciones entre huéspedes
y agentes, preservando el contexto completo de cada conversación.
"""

from datetime import datetime
from typing import Any


class ConversationHistory:
    """
    Gestor de historial de conversación del sistema multiagente.

    Mantiene un registro global de todas las conversaciones y permite
    consultar por huésped, agente o sesión.
    """

    def __init__(self):
        """Inicializa el historial de conversación."""
        self._history: list[dict[str, Any]] = []
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def record(
        self,
        guest_id: str,
        agent_id: str,
        direction: str,
        content: str,
        message_type: str = "text",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """
        Registra una entrada en el historial de conversación.

        Args:
            guest_id: ID del huésped.
            agent_id: ID del agente involucrado.
            direction: 'inbound' (huésped→agente) o 'outbound' (agente→huésped).
            content: Contenido del mensaje.
            message_type: Tipo de mensaje (text, json, event).
            metadata: Datos adicionales.

        Returns:
            La entrada registrada.
        """
        entry = {
            "guest_id": guest_id,
            "agent_id": agent_id,
            "direction": direction,
            "content": content,
            "message_type": message_type,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        self._history.append(entry)

        # Agrupar por sesión de huésped
        if guest_id not in self._sessions:
            self._sessions[guest_id] = []
        self._sessions[guest_id].append(entry)

        return entry

    def get_by_guest(self, guest_id: str) -> list[dict[str, Any]]:
        """Obtiene todo el historial de un huésped."""
        return list(self._sessions.get(guest_id, []))

    def get_by_agent(self, agent_id: str) -> list[dict[str, Any]]:
        """Obtiene todo el historial de un agente."""
        return [e for e in self._history if e["agent_id"] == agent_id]

    def get_full_history(self) -> list[dict[str, Any]]:
        """Retorna el historial completo."""
        return list(self._history)

    def get_last_n(self, guest_id: str, n: int = 5) -> list[dict[str, Any]]:
        """Obtiene las últimas N entradas de un huésped."""
        session = self._sessions.get(guest_id, [])
        return session[-n:]

    def get_entry_count(self) -> int:
        """Retorna el número total de entradas."""
        return len(self._history)

    def clear(self) -> None:
        """Limpia todo el historial."""
        self._history.clear()
        self._sessions.clear()
