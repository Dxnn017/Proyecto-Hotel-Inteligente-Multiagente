"""
Memoria Compartida del Hotel Inteligente.

Implementa el almacén de estado compartido entre todos los agentes.
Cada huésped tiene un perfil completo que incluye: datos personales,
estado de reserva, check-in, solicitudes, consumos, facturación,
feedback, promociones, historial de conversación y eventos.

Todos los agentes pueden leer y modificar la memoria compartida
a través de métodos especializados con control de acceso.
"""

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any

from config.settings import DATA_DIR


class SharedMemory:
    """
    Memoria compartida explícita del sistema multiagente.

    Almacena y gestiona el estado completo de cada huésped durante
    todo su ciclo de servicio en el hotel.
    """

    def __init__(self):
        """Inicializa la memoria compartida y carga datos simulados."""
        self._guests: dict[str, dict[str, Any]] = {}
        self._rooms: list[dict[str, Any]] = []
        self._load_initial_data()

    def _load_initial_data(self) -> None:
        """Carga los datos simulados desde los archivos JSON en data/."""
        # Cargar habitaciones
        rooms_path = os.path.join(DATA_DIR, "rooms.json")
        if os.path.exists(rooms_path):
            with open(rooms_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._rooms = data.get("rooms", [])

        # Cargar huéspedes predefinidos
        guests_path = os.path.join(DATA_DIR, "guests.json")
        if os.path.exists(guests_path):
            with open(guests_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for guest in data.get("guests", []):
                    self._init_guest_profile(guest)

        # Cargar reservas existentes
        reservations_path = os.path.join(DATA_DIR, "reservations.json")
        if os.path.exists(reservations_path):
            with open(reservations_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for res in data.get("reservations", []):
                    gid = res.get("guest_id")
                    if gid in self._guests:
                        self._guests[gid]["reservation"] = res
                        self._guests[gid]["stage"] = "reserva_confirmada"

        # Cargar consumos existentes
        consumptions_path = os.path.join(DATA_DIR, "consumptions.json")
        if os.path.exists(consumptions_path):
            with open(consumptions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for c in data.get("consumptions", []):
                    gid = c.get("guest_id")
                    if gid in self._guests:
                        self._guests[gid]["consumptions"].append(c)

    def _init_guest_profile(self, guest_data: dict) -> None:
        """
        Inicializa el perfil completo de un huésped en memoria.

        Args:
            guest_data: Datos base del huésped.
        """
        guest_id = guest_data.get("guest_id", f"G{uuid.uuid4().hex[:6].upper()}")
        self._guests[guest_id] = {
            "guest_id": guest_id,
            "name": guest_data.get("name", ""),
            "email": guest_data.get("email", ""),
            "phone": guest_data.get("phone", ""),
            "document_type": guest_data.get("document_type", ""),
            "document_number": guest_data.get("document_number", ""),
            "guest_type": guest_data.get("type", "nuevo"),
            "previous_stays": guest_data.get("previous_stays", 0),
            "loyalty_level": guest_data.get("loyalty_level", "none"),
            "preferences": guest_data.get("preferences", []),
            "stage": "sin_reserva",
            "reservation": None,
            "checkin": {
                "status": "pendiente",
                "check_in_time": None,
                "room_assigned": None,
                "validated": False,
            },
            "service_requests": [],
            "consumptions": [],
            "billing": {
                "status": "pendiente",
                "invoice_id": None,
                "room_charges": 0.0,
                "consumption_total": 0.0,
                "taxes": 0.0,
                "discounts": 0.0,
                "total_amount": 0.0,
                "payment_method": None,
                "checkout_time": None,
            },
            "feedback": {
                "rating": None,
                "comment": None,
                "sentiment": None,
                "submitted": False,
            },
            "promotions": [],
            "conversation_history": [],
            "events": [],
        }

    # =========================================================
    # GESTIÓN DE HUÉSPEDES
    # =========================================================

    def create_guest(
        self,
        name: str,
        email: str = "",
        phone: str = "",
        document_type: str = "",
        document_number: str = "",
        guest_type: str = "nuevo",
    ) -> str:
        """
        Crea un nuevo huésped en memoria.

        Returns:
            El guest_id generado.
        """
        guest_id = f"G{uuid.uuid4().hex[:6].upper()}"
        guest_data = {
            "guest_id": guest_id,
            "name": name,
            "email": email,
            "phone": phone,
            "document_type": document_type,
            "document_number": document_number,
            "type": guest_type,
            "previous_stays": 0,
            "loyalty_level": "none",
            "preferences": [],
        }
        self._init_guest_profile(guest_data)
        return guest_id

    def get_guest(self, guest_id: str) -> dict[str, Any] | None:
        """
        Consulta el estado completo de un huésped.

        Args:
            guest_id: ID del huésped.

        Returns:
            Perfil completo del huésped o None si no existe.
        """
        guest = self._guests.get(guest_id)
        return deepcopy(guest) if guest else None

    def guest_exists(self, guest_id: str) -> bool:
        """Verifica si un huésped existe en memoria."""
        return guest_id in self._guests

    def get_guest_stage(self, guest_id: str) -> str | None:
        """Retorna la etapa actual del huésped."""
        guest = self._guests.get(guest_id)
        return guest["stage"] if guest else None

    def update_guest_stage(self, guest_id: str, stage: str) -> bool:
        """
        Actualiza la etapa del huésped.

        Args:
            guest_id: ID del huésped.
            stage: Nueva etapa.

        Returns:
            True si se actualizó exitosamente.
        """
        if guest_id in self._guests:
            self._guests[guest_id]["stage"] = stage
            return True
        return False

    # =========================================================
    # GESTIÓN DE RESERVAS
    # =========================================================

    def update_reservation(self, guest_id: str, reservation: dict) -> bool:
        """
        Actualiza la información de reserva del huésped.

        Args:
            guest_id: ID del huésped.
            reservation: Datos de la reserva.

        Returns:
            True si se actualizó correctamente.
        """
        if guest_id in self._guests:
            self._guests[guest_id]["reservation"] = reservation
            self._guests[guest_id]["stage"] = "reserva_confirmada"
            return True
        return False

    def get_reservation(self, guest_id: str) -> dict | None:
        """Obtiene la reserva actual del huésped."""
        guest = self._guests.get(guest_id)
        return deepcopy(guest["reservation"]) if guest else None

    # =========================================================
    # GESTIÓN DE HABITACIONES
    # =========================================================

    def get_available_rooms(
        self, room_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Obtiene habitaciones disponibles, opcionalmente filtradas por tipo.

        Args:
            room_type: Tipo de habitación a filtrar (opcional).

        Returns:
            Lista de habitaciones disponibles.
        """
        available = [r for r in self._rooms if r["status"] == "disponible"]
        if room_type:
            available = [r for r in available if r["room_type"] == room_type]
        return deepcopy(available)

    def get_room(self, room_id: str) -> dict | None:
        """Obtiene una habitación por su ID."""
        for room in self._rooms:
            if room["room_id"] == room_id:
                return deepcopy(room)
        return None

    def update_room_status(self, room_id: str, status: str) -> bool:
        """
        Actualiza el estado de una habitación.

        Args:
            room_id: ID de la habitación.
            status: Nuevo estado.

        Returns:
            True si se actualizó correctamente.
        """
        for room in self._rooms:
            if room["room_id"] == room_id:
                room["status"] = status
                return True
        return False

    def is_room_available(self, room_id: str) -> bool:
        """Verifica si una habitación está disponible."""
        room = self.get_room(room_id)
        return room is not None and room["status"] == "disponible"

    def get_room_assigned_to_guest(self, room_id: str) -> str | None:
        """
        Encuentra qué huésped tiene asignada una habitación.

        Returns:
            guest_id del huésped que tiene la habitación, o None.
        """
        for gid, guest in self._guests.items():
            if guest["checkin"]["room_assigned"] == room_id:
                return gid
            if guest["reservation"] and guest["reservation"].get("room_assigned") == room_id:
                return gid
        return None

    # =========================================================
    # GESTIÓN DE CHECK-IN
    # =========================================================

    def update_checkin(
        self,
        guest_id: str,
        status: str,
        room_assigned: str | None = None,
        validated: bool = False,
    ) -> bool:
        """
        Actualiza el estado de check-in del huésped.

        Args:
            guest_id: ID del huésped.
            status: Estado del check-in.
            room_assigned: Habitación asignada.
            validated: Si la validación fue exitosa.

        Returns:
            True si se actualizó correctamente.
        """
        if guest_id in self._guests:
            self._guests[guest_id]["checkin"]["status"] = status
            self._guests[guest_id]["checkin"]["validated"] = validated
            if room_assigned:
                self._guests[guest_id]["checkin"]["room_assigned"] = room_assigned
            if validated:
                self._guests[guest_id]["checkin"]["check_in_time"] = datetime.now().isoformat()
                self._guests[guest_id]["stage"] = "checkin_completado"
            return True
        return False

    # =========================================================
    # GESTIÓN DE SOLICITUDES DE SERVICIO
    # =========================================================

    def register_service_request(self, guest_id: str, request: dict) -> bool:
        """
        Registra una solicitud de servicio para un huésped.

        Args:
            guest_id: ID del huésped.
            request: Datos de la solicitud.

        Returns:
            True si se registró correctamente.
        """
        if guest_id in self._guests:
            request["request_id"] = request.get(
                "request_id", f"SR-{uuid.uuid4().hex[:8]}"
            )
            request["created_at"] = datetime.now().isoformat()
            self._guests[guest_id]["service_requests"].append(request)
            if self._guests[guest_id]["stage"] == "checkin_completado":
                self._guests[guest_id]["stage"] = "en_estadia"
            return True
        return False

    def update_service_request(
        self, guest_id: str, request_id: str, status: str, details: str = ""
    ) -> bool:
        """Actualiza el estado de una solicitud de servicio."""
        if guest_id in self._guests:
            for req in self._guests[guest_id]["service_requests"]:
                if req.get("request_id") == request_id:
                    req["status"] = status
                    req["resolution_details"] = details
                    req["resolved_at"] = datetime.now().isoformat()
                    return True
        return False

    # =========================================================
    # GESTIÓN DE CONSUMOS
    # =========================================================

    def register_consumption(self, guest_id: str, consumption: dict) -> bool:
        """
        Registra un consumo para un huésped.

        Args:
            guest_id: ID del huésped.
            consumption: Datos del consumo.

        Returns:
            True si se registró correctamente.
        """
        if guest_id in self._guests:
            consumption["consumption_id"] = consumption.get(
                "consumption_id", f"C{uuid.uuid4().hex[:6].upper()}"
            )
            self._guests[guest_id]["consumptions"].append(consumption)
            return True
        return False

    def get_consumptions(self, guest_id: str) -> list[dict]:
        """Obtiene todos los consumos de un huésped."""
        guest = self._guests.get(guest_id)
        return deepcopy(guest["consumptions"]) if guest else []

    def has_duplicate_consumption(self, guest_id: str, consumption_id: str) -> bool:
        """Verifica si ya existe un consumo con el mismo ID."""
        guest = self._guests.get(guest_id)
        if guest:
            ids = [c.get("consumption_id") for c in guest["consumptions"]]
            return ids.count(consumption_id) > 1
        return False

    # =========================================================
    # GESTIÓN DE FACTURACIÓN
    # =========================================================

    def close_billing(self, guest_id: str, billing_data: dict) -> bool:
        """
        Cierra la facturación del huésped.

        Args:
            guest_id: ID del huésped.
            billing_data: Datos de facturación calculados.

        Returns:
            True si se cerró correctamente.
        """
        if guest_id in self._guests:
            self._guests[guest_id]["billing"].update(billing_data)
            self._guests[guest_id]["billing"]["status"] = "cerrada"
            self._guests[guest_id]["billing"]["checkout_time"] = datetime.now().isoformat()
            self._guests[guest_id]["stage"] = "checkout_completado"
            return True
        return False

    # =========================================================
    # GESTIÓN DE FEEDBACK
    # =========================================================

    def register_feedback(
        self,
        guest_id: str,
        rating: int,
        comment: str,
        sentiment: str,
    ) -> bool:
        """
        Registra el feedback de un huésped.

        Args:
            guest_id: ID del huésped.
            rating: Calificación (1-5).
            comment: Comentario del huésped.
            sentiment: Sentimiento detectado.

        Returns:
            True si se registró correctamente.
        """
        if guest_id in self._guests:
            self._guests[guest_id]["feedback"] = {
                "rating": rating,
                "comment": comment,
                "sentiment": sentiment,
                "submitted": True,
                "submitted_at": datetime.now().isoformat(),
            }
            self._guests[guest_id]["stage"] = "feedback_completado"
            return True
        return False

    def register_promotion(self, guest_id: str, promotion: dict) -> bool:
        """Registra una promoción generada para el huésped."""
        if guest_id in self._guests:
            promotion["generated_at"] = datetime.now().isoformat()
            self._guests[guest_id]["promotions"].append(promotion)
            return True
        return False

    # =========================================================
    # GESTIÓN DE HISTORIAL
    # =========================================================

    def add_conversation_entry(
        self, guest_id: str, role: str, content: str, agent_id: str = ""
    ) -> bool:
        """
        Añade una entrada al historial de conversación del huésped.

        Args:
            guest_id: ID del huésped.
            role: Rol del emisor (guest, agent, system).
            content: Contenido del mensaje.
            agent_id: ID del agente (si aplica).

        Returns:
            True si se añadió correctamente.
        """
        if guest_id in self._guests:
            entry = {
                "role": role,
                "content": content,
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat(),
            }
            self._guests[guest_id]["conversation_history"].append(entry)
            return True
        return False

    def get_conversation_history(self, guest_id: str) -> list[dict]:
        """Obtiene el historial de conversación de un huésped."""
        guest = self._guests.get(guest_id)
        return deepcopy(guest["conversation_history"]) if guest else []

    def add_event_reference(self, guest_id: str, event_id: str) -> bool:
        """Registra una referencia a un evento en el perfil del huésped."""
        if guest_id in self._guests:
            self._guests[guest_id]["events"].append(event_id)
            return True
        return False

    def get_full_history(self, guest_id: str) -> dict | None:
        """
        Obtiene el historial completo del huésped incluyendo
        reserva, check-in, solicitudes, consumos, facturación,
        feedback, promociones, conversación y eventos.
        """
        return self.get_guest(guest_id)

    # =========================================================
    # UTILIDADES
    # =========================================================

    def get_all_guest_ids(self) -> list[str]:
        """Retorna todos los IDs de huéspedes registrados."""
        return list(self._guests.keys())

    def get_active_reservations(self) -> list[dict]:
        """Retorna todas las reservas activas."""
        active = []
        for guest in self._guests.values():
            if guest["reservation"] and guest["reservation"].get("status") == "confirmada":
                active.append(deepcopy(guest["reservation"]))
        return active

    def find_guest_by_reservation(self, reservation_id: str) -> str | None:
        """Encuentra un huésped por su ID de reserva."""
        for gid, guest in self._guests.items():
            if guest["reservation"] and guest["reservation"].get("reservation_id") == reservation_id:
                return gid
        return None

    def clear(self) -> None:
        """Limpia toda la memoria (útil para testing)."""
        self._guests.clear()
        self._rooms.clear()
