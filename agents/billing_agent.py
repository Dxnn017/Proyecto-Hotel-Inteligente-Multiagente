"""
Agente de Facturación Automática del Hotel Inteligente.

PROMPT DE SISTEMA:
==================
Rol: Agente especializado en facturación y check-out.

Responsabilidades:
- Consultar consumos del huésped (restaurante, minibar, etc.).
- Calcular monto final incluyendo cargos de habitación e impuestos.
- Aplicar descuentos promocionales o penalidades.
- Generar comprobante/factura detallada.
- Confirmar salida del huésped y cerrar folio.
- Publicar evento 'checkout_iniciado', 'factura_generada' y 'checkout_confirmado'.
- Actualizar estado de checkout en memoria.

Límites de acción:
- NO puede gestionar reservas nuevas ni cancelaciones.
- NO puede asignar habitaciones ni registrar llegadas (check-in).
- NO puede resolver solicitudes de servicio o mantenimiento.
- NO puede procesar feedback ni generar encuestas.

Entradas esperadas:
- JSON con action: iniciar_checkout | calcular_factura | generar_comprobante | confirmar_checkout
- Datos: guest_id, reservation_id, room_number

Salidas esperadas:
- JSON con status: success | failed | escalated
- Incluye: invoice_id, total_amount, response_message

Formato JSON obligatorio: Sí, según billing_schema.json

Casos de escalamiento:
- Consumos contradictorios o duplicados → escalar a humano.
- Problemas con el método de pago (simulado) → escalar a recepción.

Eventos que puede publicar:
- checkout_iniciado
- factura_generada
- checkout_confirmado

Datos de memoria que puede leer/modificar:
- LEER: reserva, consumos, promociones del huésped.
- MODIFICAR: estado de facturación, etapa del huésped, estado de habitación.
"""

import uuid
from datetime import datetime
from typing import Any

from config.settings import BILLING_AGENT_ID


class BillingAgent:
    """
    Agente de Facturación Automática: gestiona cargos, facturas y checkout.
    """

    AGENT_ID = BILLING_AGENT_ID
    AGENT_NAME = "Agente de Facturación Automática"
    TAX_RATE = 0.18  # 18% de impuestos

    def __init__(self, shared_memory, event_bus):
        self.memory = shared_memory
        self.event_bus = event_bus

    def process(self, payload: dict) -> dict[str, Any]:
        """Procesa una solicitud de facturación."""
        action = payload.get("action", "iniciar_checkout")

        if action == "iniciar_checkout":
            return self._initiate_checkout(payload)
        elif action == "calcular_factura":
            return self._calculate_invoice(payload)
        elif action == "generar_comprobante":
            return self._generate_invoice(payload)
        elif action == "confirmar_checkout":
            return self._confirm_checkout(payload)
        else:
            return {
                "status": "failed",
                "action": action,
                "response_message": f"Acción no reconocida: {action}",
            }

    def _initiate_checkout(self, payload: dict) -> dict[str, Any]:
        guest_id = payload.get("guest_id", "")
        
        self.event_bus.publish(
            "checkout_iniciado", self.AGENT_ID, guest_id,
            {"action": "iniciar_checkout"}
        )

        guest = self.memory.get_guest(guest_id)
        if not guest or not guest.get("reservation"):
            return {
                "status": "failed",
                "action": "iniciar_checkout",
                "response_message": "No se encontró reserva para procesar el checkout.",
            }
        
        return {
            "status": "success",
            "action": "iniciar_checkout",
            "response_message": "Proceso de checkout iniciado. Calculando consumos...",
        }

    def _calculate_invoice(self, payload: dict) -> dict[str, Any]:
        guest_id = payload.get("guest_id", "")
        guest = self.memory.get_guest(guest_id)
        
        if not guest or not guest.get("reservation"):
            return {
                "status": "failed",
                "action": "calcular_factura",
                "response_message": "Huésped o reserva no encontrada.",
            }

        reservation = guest.get("reservation", {})
        room_charges = reservation.get("total_cost", 0.0)
        
        consumptions = self.memory.get_consumptions(guest_id)
        consumption_total = sum(c.get("amount", 0.0) for c in consumptions if c.get("amount", 0.0) > 0)
        discounts = sum(abs(c.get("amount", 0.0)) for c in consumptions if c.get("amount", 0.0) < 0)
        
        # Considerar promociones en memoria si las hay y no están ya en consumptions
        for promo in guest.get("promotions", []):
            if "discount_percent" in promo:
                desc = (room_charges + consumption_total) * (promo["discount_percent"] / 100.0)
                discounts += desc

        subtotal = room_charges + consumption_total - discounts
        taxes = subtotal * self.TAX_RATE
        total_amount = subtotal + taxes

        return {
            "status": "success",
            "action": "calcular_factura",
            "room_charges": round(room_charges, 2),
            "consumption_total": round(consumption_total, 2),
            "discounts": round(discounts, 2),
            "taxes": round(taxes, 2),
            "total_amount": round(total_amount, 2),
            "consumptions": consumptions,
            "response_message": f"Factura calculada. Total a pagar: ${total_amount:.2f}",
        }

    def _generate_invoice(self, payload: dict) -> dict[str, Any]:
        # Para simplificar, calculamos y generamos en un paso si vienen de main.py
        calc = self._calculate_invoice(payload)
        if calc["status"] == "failed":
            return calc
            
        invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
        calc["invoice_id"] = invoice_id
        calc["action"] = "generar_comprobante"
        calc["response_message"] = f"Comprobante {invoice_id} generado por ${calc['total_amount']:.2f}"
        
        guest_id = payload.get("guest_id", "")
        self.event_bus.publish(
            "factura_generada", self.AGENT_ID, guest_id,
            {"invoice_id": invoice_id, "total_amount": calc["total_amount"]}
        )
        
        return calc

    def _confirm_checkout(self, payload: dict) -> dict[str, Any]:
        guest_id = payload.get("guest_id", "")
        payment_method = payload.get("payment_method", "efectivo")
        
        # Asegurar que generamos factura
        invoice = self._generate_invoice(payload)
        if invoice["status"] == "failed":
            return invoice

        # Actualizar memoria
        billing_data = {
            "invoice_id": invoice["invoice_id"],
            "room_charges": invoice["room_charges"],
            "consumption_total": invoice["consumption_total"],
            "taxes": invoice["taxes"],
            "discounts": invoice["discounts"],
            "total_amount": invoice["total_amount"],
            "payment_method": payment_method
        }
        
        self.memory.close_billing(guest_id, billing_data)
        
        # Liberar habitación si tenía
        guest = self.memory.get_guest(guest_id)
        if guest and guest["checkin"]["room_assigned"]:
            self.memory.update_room_status(guest["checkin"]["room_assigned"], "mantenimiento")
            
        self.event_bus.publish(
            "checkout_confirmado", self.AGENT_ID, guest_id,
            {"invoice_id": invoice["invoice_id"], "status": "cerrada"}
        )

        return {
            "status": "success",
            "action": "confirmar_checkout",
            "invoice_id": invoice["invoice_id"],
            "total_amount": invoice["total_amount"],
            "response_message": f"✅ Check-out confirmado. Pago de ${invoice['total_amount']:.2f} procesado. Habitación liberada.",
        }
