"""
Agente de Check-in Digital del Hotel Inteligente.

PROMPT DE SISTEMA:
==================
Rol: Agente especializado en el registro digital y check-in de huéspedes.

Responsabilidades:
- Gestionar el registro previo online del huésped.
- Validar identidad y documentos presentados.
- Verificar que exista una reserva activa para el huésped.
- Solicitar corrección si los datos son inválidos o incompletos.
- Confirmar el check-in y asignar/confirmar habitación.
- Publicar evento 'checkin_validado' o 'checkin_rechazado'.
- Actualizar memoria compartida con datos de check-in.

Límites de acción:
- NO puede registrar reservas nuevas.
- NO puede calcular facturas ni procesar pagos.
- NO puede analizar feedback ni generar promociones.
- NO puede resolver solicitudes de servicio.

Entradas esperadas:
- JSON con action: iniciar_checkin | validar_identidad | confirmar_checkin
- Datos: guest_id, reservation_id, guest_name, document_type, document_number

Salidas esperadas:
- JSON con status: success | failed | escalated
- Incluye: validation_status, room_assigned, check_in_time, response_message

Formato JSON obligatorio: Sí, según checkin_schema.json

Casos de escalamiento:
- Si el huésped no tiene reserva → rechazar y redirigir a Agente de Reservas.
- Si los documentos son inválidos → solicitar corrección.
- Si la habitación asignada está ocupada → escalar a Resolvedor de Conflictos.

Eventos que puede publicar:
- checkin_iniciado
- checkin_validado
- checkin_rechazado

Datos de memoria que puede leer/modificar:
- LEER: reserva del huésped, estado de habitación.
- MODIFICAR: estado de check-in, habitación asignada, etapa del huésped.
"""

from datetime import datetime
from typing import Any

from config.settings import CHECKIN_AGENT_ID


class CheckinAgent:
    """
    Agente de Check-in Digital: gestiona registro, validación y confirmación de check-in.
    """

    AGENT_ID = CHECKIN_AGENT_ID
    AGENT_NAME = "Agente de Check-in Digital"

    def __init__(self, shared_memory, event_bus):
        self.memory = shared_memory
        self.event_bus = event_bus

    def process(self, payload: dict) -> dict[str, Any]:
        """
        Procesa una solicitud de check-in.

        Args:
            payload: Diccionario con action y datos del check-in.

        Returns:
            Resultado del procesamiento.
        """
        action = payload.get("action", "iniciar_checkin")
        guest_id = payload.get("guest_id", "")

        if action == "iniciar_checkin":
            return self._initiate_checkin(payload)
        elif action == "validar_identidad":
            return self._validate_identity(payload)
        elif action == "confirmar_checkin":
            return self._confirm_checkin(payload)
        elif action == "rechazar_checkin":
            return self._reject_checkin(payload)
        else:
            return {
                "status": "failed",
                "action": action,
                "response_message": f"Acción no reconocida: {action}",
            }

    def _initiate_checkin(self, payload: dict) -> dict[str, Any]:
        """Inicia el proceso de check-in."""
        guest_id = payload.get("guest_id", "")

        # Publicar evento
        self.event_bus.publish(
            "checkin_iniciado", self.AGENT_ID, guest_id,
            {"action": "iniciar_checkin"},
        )

        # Verificar que el huésped existe
        if not self.memory.guest_exists(guest_id):
            self.event_bus.publish(
                "checkin_rechazado", self.AGENT_ID, guest_id,
                {"reason": "Huésped no registrado"},
            )
            return {
                "status": "failed",
                "action": "iniciar_checkin",
                "response_message": "Huésped no encontrado en el sistema. Debe realizar una reserva primero.",
            }

        # Verificar que tiene reserva
        reservation = self.memory.get_reservation(guest_id)
        if not reservation:
            self.event_bus.publish(
                "checkin_rechazado", self.AGENT_ID, guest_id,
                {"reason": "Sin reserva activa"},
            )
            return {
                "status": "failed",
                "action": "iniciar_checkin",
                "validation_status": "invalido",
                "response_message": "No se encontró una reserva activa. Debe realizar una reserva antes del check-in.",
                "redirect_to": "reservation_agent",
            }

        # Reserva encontrada - solicitar validación de identidad
        return {
            "status": "success",
            "action": "iniciar_checkin",
            "reservation_id": reservation.get("reservation_id"),
            "room_assigned": reservation.get("room_assigned"),
            "room_type": reservation.get("room_type"),
            "response_message": (
                f"Reserva encontrada: {reservation.get('reservation_id')}. "
                f"Habitación: {reservation.get('room_assigned')}. "
                "Por favor, presente su documento de identidad para validación."
            ),
        }

    def _validate_identity(self, payload: dict) -> dict[str, Any]:
        """Valida la identidad y documentos del huésped."""
        guest_id = payload.get("guest_id", "")
        document_type = payload.get("document_type", "")
        document_number = payload.get("document_number", "")
        guest_name = payload.get("guest_name", "")

        errors = []

        # Validar que se proporcionaron los datos
        if not document_type:
            errors.append("Tipo de documento no proporcionado.")
        elif document_type not in ["dni", "pasaporte", "cedula", "licencia"]:
            errors.append(f"Tipo de documento no válido: {document_type}.")

        if not document_number:
            errors.append("Número de documento no proporcionado.")
        elif len(document_number) < 5:
            errors.append("Número de documento demasiado corto (mínimo 5 caracteres).")

        if not guest_name:
            errors.append("Nombre del huésped no proporcionado.")
        elif len(guest_name) < 2:
            errors.append("Nombre del huésped demasiado corto.")

        if errors:
            return {
                "status": "failed",
                "action": "validar_identidad",
                "validation_status": "invalido",
                "validation_errors": errors,
                "response_message": "Datos de identidad inválidos: " + "; ".join(errors),
            }

        # Validación exitosa
        return {
            "status": "success",
            "action": "validar_identidad",
            "validation_status": "valido",
            "document_type": document_type,
            "document_number": document_number,
            "guest_name": guest_name,
            "response_message": "✅ Identidad validada correctamente. Procediendo a confirmar check-in.",
        }

    def _confirm_checkin(self, payload: dict) -> dict[str, Any]:
        """Confirma el check-in del huésped."""
        guest_id = payload.get("guest_id", "")

        # Verificar reserva
        reservation = self.memory.get_reservation(guest_id)
        if not reservation:
            return {
                "status": "failed",
                "action": "confirmar_checkin",
                "response_message": "No se puede confirmar check-in sin reserva activa.",
            }

        room_id = reservation.get("room_assigned", "")

        # Verificar que la habitación esté disponible o reservada (para este huésped)
        room = self.memory.get_room(room_id)
        if room and room["status"] not in ["disponible", "reservada"]:
            # Habitación ocupada - conflicto
            return {
                "status": "escalated",
                "action": "confirmar_checkin",
                "response_message": f"La habitación {room_id} no está disponible. Se requiere resolución de conflicto.",
                "conflict_type": "habitacion_ocupada",
                "room_id": room_id,
                "room_type": reservation.get("room_type"),
                "requires_human": False,
            }

        # Confirmar check-in
        check_in_time = datetime.now().isoformat()
        self.memory.update_checkin(
            guest_id,
            status="completado",
            room_assigned=room_id,
            validated=True,
        )
        self.memory.update_room_status(room_id, "ocupada")

        # Publicar evento
        self.event_bus.publish(
            "checkin_validado", self.AGENT_ID, guest_id,
            {
                "room": room_id,
                "check_in_time": check_in_time,
                "reservation_id": reservation.get("reservation_id"),
            },
        )

        return {
            "status": "success",
            "action": "confirmar_checkin",
            "room_assigned": room_id,
            "check_in_time": check_in_time,
            "response_message": (
                f"✅ Check-in completado exitosamente. "
                f"Habitación: {room_id}. "
                f"¡Bienvenido al Hotel Inteligente! "
                "Su llave digital ha sido activada."
            ),
        }

    def _reject_checkin(self, payload: dict) -> dict[str, Any]:
        """Rechaza el check-in."""
        guest_id = payload.get("guest_id", "")
        reason = payload.get("reason", "Datos inválidos")

        self.memory.update_checkin(guest_id, status="rechazado", validated=False)

        self.event_bus.publish(
            "checkin_rechazado", self.AGENT_ID, guest_id,
            {"reason": reason},
        )

        return {
            "status": "failed",
            "action": "rechazar_checkin",
            "response_message": f"Check-in rechazado: {reason}",
        }
