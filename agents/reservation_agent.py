"""
Agente de Reservas del Hotel Inteligente.

PROMPT DE SISTEMA:
==================
Rol: Agente especializado en gestión de reservas hoteleras.

Responsabilidades:
- Atender consultas de reserva de huéspedes.
- Interpretar fechas, número de huéspedes y tipo de habitación.
- Verificar disponibilidad en el sistema.
- Proponer habitaciones disponibles al huésped.
- Confirmar reserva y asignar habitación.
- Publicar evento 'reserva_confirmada' o 'reserva_rechazada'.
- Actualizar memoria compartida con datos de la reserva.

Límites de acción:
- NO puede gestionar check-in ni asignar llaves.
- NO puede calcular facturas ni procesar pagos.
- NO puede analizar feedback ni generar promociones.
- NO puede resolver solicitudes de servicio durante la estadía.

Entradas esperadas:
- JSON con action: consultar_disponibilidad | crear_reserva | cancelar_reserva
- Datos: guest_id, guest_name, check_in_date, check_out_date, room_type, num_guests

Salidas esperadas:
- JSON con status: success | failed | escalated
- Incluye: reservation_id, room_assigned, total_cost, available_rooms, response_message

Formato JSON obligatorio: Sí, según reservation_schema.json

Casos de escalamiento:
- Si no hay habitaciones de ningún tipo disponibles → escalar a humano.
- Si las fechas son inválidas o contradictorias → solicitar corrección.

Eventos que puede publicar:
- reserva_solicitada
- reserva_confirmada
- reserva_rechazada

Datos de memoria que puede leer/modificar:
- LEER: habitaciones disponibles, perfil del huésped, reservas existentes.
- MODIFICAR: reserva del huésped, estado de habitación, etapa del huésped.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from config.settings import (
    RESERVATION_AGENT_ID,
    ROOM_TYPES,
)


class ReservationAgent:
    """
    Agente de Reservas: gestiona consultas, creación y cancelación de reservas.
    """

    AGENT_ID = RESERVATION_AGENT_ID
    AGENT_NAME = "Agente de Reservas"

    def __init__(self, shared_memory, event_bus):
        self.memory = shared_memory
        self.event_bus = event_bus

    def process(self, payload: dict) -> dict[str, Any]:
        """
        Procesa una solicitud de reserva.

        Args:
            payload: Diccionario con action y datos de la reserva.

        Returns:
            Resultado del procesamiento.
        """
        action = payload.get("action", "consultar_disponibilidad")
        guest_id = payload.get("guest_id", "")

        if action == "consultar_disponibilidad":
            return self._check_availability(payload)
        elif action == "crear_reserva":
            return self._create_reservation(payload)
        elif action == "cancelar_reserva":
            return self._cancel_reservation(payload)
        else:
            return {
                "status": "failed",
                "action": action,
                "response_message": f"Acción no reconocida: {action}",
            }

    def _check_availability(self, payload: dict) -> dict[str, Any]:
        """Consulta disponibilidad de habitaciones."""
        room_type = payload.get("room_type")
        available = self.memory.get_available_rooms(room_type)

        if available:
            rooms_info = [
                {
                    "room_id": r["room_id"],
                    "room_type": r["room_type"],
                    "floor": r["floor"],
                    "tarifa_noche": r["tarifa_noche"],
                }
                for r in available
            ]
            msg = f"Hay {len(available)} habitaciones disponibles"
            if room_type:
                msg += f" de tipo {room_type}"
            msg += "."
            return {
                "status": "success",
                "action": "consultar_disponibilidad",
                "available_rooms": rooms_info,
                "response_message": msg,
            }
        else:
            msg = "No hay habitaciones disponibles"
            if room_type:
                msg += f" de tipo {room_type}"
            msg += " en este momento."
            return {
                "status": "failed",
                "action": "consultar_disponibilidad",
                "available_rooms": [],
                "response_message": msg,
            }

    def _create_reservation(self, payload: dict) -> dict[str, Any]:
        """Crea una nueva reserva."""
        guest_id = payload.get("guest_id", "")
        guest_name = payload.get("guest_name", "")
        room_type = payload.get("room_type", "simple")
        check_in_date = payload.get("check_in_date", "")
        check_out_date = payload.get("check_out_date", "")
        num_guests = payload.get("num_guests", 1)

        # Validar fechas
        try:
            ci = datetime.strptime(check_in_date, "%Y-%m-%d")
            co = datetime.strptime(check_out_date, "%Y-%m-%d")
            if co <= ci:
                self.event_bus.publish(
                    "reserva_rechazada", self.AGENT_ID, guest_id,
                    {"reason": "Fechas inválidas"},
                )
                return {
                    "status": "failed",
                    "action": "crear_reserva",
                    "response_message": "Error: La fecha de check-out debe ser posterior al check-in.",
                }
            total_nights = (co - ci).days
        except (ValueError, TypeError):
            self.event_bus.publish(
                "reserva_rechazada", self.AGENT_ID, guest_id,
                {"reason": "Formato de fechas inválido"},
            )
            return {
                "status": "failed",
                "action": "crear_reserva",
                "response_message": "Error: Formato de fechas inválido. Use YYYY-MM-DD.",
            }

        # Publicar evento de solicitud
        self.event_bus.publish(
            "reserva_solicitada", self.AGENT_ID, guest_id,
            {"room_type": room_type, "check_in": check_in_date, "check_out": check_out_date},
        )

        # Verificar disponibilidad
        available = self.memory.get_available_rooms(room_type)
        if not available:
            self.event_bus.publish(
                "reserva_rechazada", self.AGENT_ID, guest_id,
                {"reason": f"No hay habitaciones {room_type} disponibles"},
            )
            return {
                "status": "failed",
                "action": "crear_reserva",
                "response_message": f"Lo sentimos, no hay habitaciones de tipo {room_type} disponibles.",
                "available_rooms": [],
            }

        # Verificar capacidad
        room_config = ROOM_TYPES.get(room_type, {})
        if num_guests > room_config.get("capacidad", 1):
            return {
                "status": "failed",
                "action": "crear_reserva",
                "response_message": f"La habitación {room_type} tiene capacidad para {room_config.get('capacidad', 1)} personas. Se requiere una habitación más grande.",
            }

        # Asignar habitación
        selected_room = available[0]
        tarifa = selected_room["tarifa_noche"]
        total_cost = tarifa * total_nights

        # Crear reserva
        reservation_id = f"R{uuid.uuid4().hex[:6].upper()}"
        reservation = {
            "reservation_id": reservation_id,
            "guest_id": guest_id,
            "guest_name": guest_name,
            "room_type": room_type,
            "room_assigned": selected_room["room_id"],
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "num_guests": num_guests,
            "status": "confirmada",
            "total_nights": total_nights,
            "total_cost": total_cost,
            "special_requests": payload.get("special_requests", ""),
            "created_at": datetime.now().isoformat(),
        }

        # Si es un huésped nuevo, crearlo en memoria
        if not self.memory.guest_exists(guest_id) and guest_name:
            guest_id = self.memory.create_guest(
                name=guest_name,
                email=payload.get("guest_email", ""),
                phone=payload.get("guest_phone", ""),
            )
            reservation["guest_id"] = guest_id

        # Actualizar memoria
        self.memory.update_reservation(guest_id, reservation)
        self.memory.update_room_status(selected_room["room_id"], "reservada")

        # Publicar evento de confirmación
        self.event_bus.publish(
            "reserva_confirmada", self.AGENT_ID, guest_id,
            {
                "reservation_id": reservation_id,
                "room": selected_room["room_id"],
                "total_cost": total_cost,
            },
        )

        return {
            "status": "success",
            "action": "crear_reserva",
            "reservation_id": reservation_id,
            "room_assigned": selected_room["room_id"],
            "room_type": room_type,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "total_nights": total_nights,
            "total_cost": total_cost,
            "response_message": (
                f"✅ Reserva confirmada. ID: {reservation_id}. "
                f"Habitación {selected_room['room_id']} ({room_type}). "
                f"{total_nights} noches. Total: ${total_cost:.2f}."
            ),
        }

    def _cancel_reservation(self, payload: dict) -> dict[str, Any]:
        """Cancela una reserva existente."""
        guest_id = payload.get("guest_id", "")
        reservation = self.memory.get_reservation(guest_id)

        if not reservation:
            return {
                "status": "failed",
                "action": "cancelar_reserva",
                "response_message": "No se encontró una reserva activa para este huésped.",
            }

        # Liberar habitación
        room_id = reservation.get("room_assigned")
        if room_id:
            self.memory.update_room_status(room_id, "disponible")

        # Actualizar reserva
        reservation["status"] = "cancelada"
        self.memory.update_reservation(guest_id, reservation)
        self.memory.update_guest_stage(guest_id, "sin_reserva")

        return {
            "status": "success",
            "action": "cancelar_reserva",
            "reservation_id": reservation.get("reservation_id"),
            "response_message": f"Reserva {reservation.get('reservation_id')} cancelada exitosamente.",
        }
