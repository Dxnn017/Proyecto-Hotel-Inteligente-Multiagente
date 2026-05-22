"""
Agente de Feedback y Fidelización del Hotel Inteligente.

PROMPT DE SISTEMA:
==================
Rol: Agente especializado en el análisis de feedback, encuestas y fidelización.

Responsabilidades:
- Recibir y procesar comentarios y encuestas de huéspedes.
- Analizar el sentimiento del comentario (positivo, neutral, negativo).
- Si es positivo y el huésped es frecuente, generar promoción de fidelidad.
- Si es negativo, generar alerta de seguimiento para atención al cliente/gerencia.
- Publicar eventos 'feedback_recibido', 'promocion_generada'.
- Actualizar el perfil del huésped con su nuevo nivel de lealtad (simulado).

Límites de acción:
- NO puede emitir reembolsos ni modificar facturas pasadas.
- NO puede cambiar el estado de la habitación o reservas futuras.

Entradas esperadas:
- JSON con action: enviar_encuesta | recibir_feedback
- Datos: guest_id, rating, comment

Salidas esperadas:
- JSON con status: success | failed | escalated
- Incluye: sentiment, promotion, follow_up_alert, response_message

Formato JSON obligatorio: Sí, según feedback_schema.json

Casos de escalamiento:
- Palabras clave extremas (demanda, policía, robo) → escalamiento inmediato a gerencia.
"""

import uuid
from typing import Any

from config.settings import FEEDBACK_AGENT_ID, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS


class FeedbackAgent:
    """
    Agente de Feedback y Fidelización: gestiona comentarios y fidelización de huéspedes.
    """

    AGENT_ID = FEEDBACK_AGENT_ID
    AGENT_NAME = "Agente de Feedback y Fidelización"

    def __init__(self, shared_memory, event_bus):
        self.memory = shared_memory
        self.event_bus = event_bus

    def process(self, payload: dict) -> dict[str, Any]:
        """Procesa solicitud de feedback."""
        action = payload.get("action", "recibir_feedback")

        if action == "enviar_encuesta":
            return self._send_survey(payload)
        elif action == "recibir_feedback":
            return self._receive_feedback(payload)
        else:
            return {
                "status": "failed",
                "action": action,
                "response_message": f"Acción no reconocida: {action}",
            }

    def _send_survey(self, payload: dict) -> dict[str, Any]:
        guest_id = payload.get("guest_id", "")
        return {
            "status": "success",
            "action": "enviar_encuesta",
            "response_message": "Encuesta de satisfacción enviada al huésped.",
        }

    def _analyze_sentiment(self, text: str, rating: int) -> str:
        """Análisis de sentimiento ultra simplificado para la simulación."""
        text = text.lower()
        if rating >= 4 or any(word in text for word in POSITIVE_KEYWORDS):
            return "positivo"
        elif rating <= 2 or any(word in text for word in NEGATIVE_KEYWORDS):
            return "negativo"
        else:
            return "neutral"

    def _receive_feedback(self, payload: dict) -> dict[str, Any]:
        guest_id = payload.get("guest_id", "")
        rating = payload.get("rating", 3)
        comment = payload.get("comment", "")

        sentiment = self._analyze_sentiment(comment, rating)
        
        self.memory.register_feedback(guest_id, rating, comment, sentiment)
        
        self.event_bus.publish(
            "feedback_recibido", self.AGENT_ID, guest_id,
            {"rating": rating, "sentiment": sentiment}
        )

        response = {
            "status": "success",
            "action": "recibir_feedback",
            "sentiment": sentiment,
        }

        guest = self.memory.get_guest(guest_id)
        
        if sentiment == "positivo":
            # Generar promoción
            promo_code = f"LOYALTY-{uuid.uuid4().hex[:6].upper()}"
            promo = {
                "type": "descuento",
                "discount_percent": 15,
                "description": "15% de descuento en próxima reserva",
                "code": promo_code
            }
            self.memory.register_promotion(guest_id, promo)
            self.event_bus.publish("promocion_generada", self.AGENT_ID, guest_id, promo)
            
            response["promotion"] = promo
            response["response_message"] = f"¡Gracias por sus comentarios positivos! Hemos añadido un 15% de descuento para su próxima visita (Código: {promo_code})."
            
        elif sentiment == "negativo":
            # Generar alerta
            alert = {
                "priority": "alta",
                "reason": f"Feedback negativo (rating {rating}): {comment[:50]}...",
                "assigned_to": "gerente_servicio"
            }
            response["follow_up_alert"] = alert
            response["response_message"] = "Lamentamos que su experiencia no haya sido la mejor. Hemos notificado a la gerencia para hacer un seguimiento de su caso."
            
            # El conflict resolver (o el swarm) decidirá qué hacer con la alerta
        else:
            response["response_message"] = "Gracias por su retroalimentación. Esperamos recibirlo pronto."

        return response
