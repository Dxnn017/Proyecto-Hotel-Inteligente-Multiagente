"""
Configuración global del sistema Hotel Inteligente con 5 Agentes de IA.
Define constantes, rutas, parámetros de agentes y configuración del sistema.
"""

import os

# =============================================================
# RUTAS DEL PROYECTO
# =============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCHEMAS_DIR = os.path.join(BASE_DIR, "schemas")
METRICS_DIR = os.path.join(BASE_DIR, "metrics")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

# =============================================================
# NOMBRE DEL HOTEL
# =============================================================
HOTEL_NAME = "Hotel Inteligente IA"
HOTEL_VERSION = "1.0.0"

# =============================================================
# IDENTIFICADORES DE AGENTES
# =============================================================
ORCHESTRATOR_ID = "orchestrator_agent"
RESERVATION_AGENT_ID = "reservation_agent"
CHECKIN_AGENT_ID = "checkin_agent"
CUSTOMER_SERVICE_AGENT_ID = "customer_service_agent"
BILLING_AGENT_ID = "billing_agent"
FEEDBACK_AGENT_ID = "feedback_agent"

ALL_AGENT_IDS = [
    ORCHESTRATOR_ID,
    RESERVATION_AGENT_ID,
    CHECKIN_AGENT_ID,
    CUSTOMER_SERVICE_AGENT_ID,
    BILLING_AGENT_ID,
    FEEDBACK_AGENT_ID,
]

# =============================================================
# TIPOS DE HABITACIÓN Y TARIFAS
# =============================================================
ROOM_TYPES = {
    "simple": {"tarifa_noche": 80.00, "capacidad": 1},
    "doble": {"tarifa_noche": 120.00, "capacidad": 2},
    "matrimonial": {"tarifa_noche": 150.00, "capacidad": 2},
    "suite": {"tarifa_noche": 280.00, "capacidad": 4},
}

# =============================================================
# ESTADOS DE HABITACIÓN
# =============================================================
ROOM_STATES = ["disponible", "ocupada", "mantenimiento", "reservada"]

# =============================================================
# ESTADOS DEL PROCESO DEL HUÉSPED
# =============================================================
GUEST_STAGES = [
    "sin_reserva",
    "reserva_confirmada",
    "checkin_completado",
    "en_estadia",
    "checkout_iniciado",
    "checkout_completado",
    "feedback_completado",
]

# =============================================================
# TIPOS DE EVENTOS DEL EVENT BUS
# =============================================================
EVENT_TYPES = [
    "reserva_solicitada",
    "reserva_confirmada",
    "reserva_rechazada",
    "checkin_iniciado",
    "checkin_validado",
    "checkin_rechazado",
    "solicitud_servicio_creada",
    "solicitud_servicio_resuelta",
    "solicitud_servicio_escalada",
    "checkout_iniciado",
    "factura_generada",
    "checkout_confirmado",
    "feedback_recibido",
    "promocion_generada",
    "conflicto_detectado",
    "escalamiento_humano_requerido",
]

# =============================================================
# CATEGORÍAS DE SOLICITUDES DE SERVICIO
# =============================================================
SERVICE_CATEGORIES = [
    "limpieza",
    "mantenimiento",
    "toallas",
    "informacion_turistica",
    "restaurante",
    "reclamo",
    "room_service",
]

# Categorías que se resuelven automáticamente
AUTO_RESOLVE_CATEGORIES = [
    "limpieza",
    "toallas",
    "informacion_turistica",
    "restaurante",
    "room_service",
]

# Categorías que requieren escalamiento
ESCALATION_CATEGORIES = [
    "mantenimiento",
    "reclamo",
]

# =============================================================
# TIPOS DE CONSUMO
# =============================================================
CONSUMPTION_TYPES = {
    "restaurante": {"descripcion": "Consumo en restaurante del hotel", "rango": (15.0, 120.0)},
    "minibar": {"descripcion": "Consumo de minibar en habitación", "rango": (5.0, 50.0)},
    "lavanderia": {"descripcion": "Servicio de lavandería", "rango": (10.0, 40.0)},
    "room_service": {"descripcion": "Servicio a la habitación", "rango": (12.0, 80.0)},
    "penalidad_dano": {"descripcion": "Penalidad por daño a instalaciones", "rango": (50.0, 500.0)},
    "descuento_promocional": {"descripcion": "Descuento por promoción", "rango": (-50.0, -5.0)},
}

# =============================================================
# CLASIFICACIÓN DE FEEDBACK
# =============================================================
FEEDBACK_SENTIMENTS = ["positivo", "neutral", "negativo"]

# Palabras clave para análisis de sentimiento simulado
POSITIVE_KEYWORDS = [
    "excelente", "maravilloso", "increíble", "perfecto", "genial",
    "fantástico", "encantado", "satisfecho", "recomiendo", "volvería",
    "limpio", "cómodo", "amable", "atento", "bueno", "bien",
    "excellent", "great", "amazing", "wonderful", "happy",
]

NEGATIVE_KEYWORDS = [
    "terrible", "pésimo", "horrible", "sucio", "ruidoso",
    "malo", "desagradable", "decepcionado", "queja", "reclamo",
    "inaceptable", "vergüenza", "nunca", "peor", "molesto",
    "enojado", "furioso", "asco", "basura", "estafa",
    "bad", "terrible", "awful", "dirty", "worst",
]

# =============================================================
# CONFIGURACIÓN DE MÉTRICAS
# =============================================================
METRICS_FILE = os.path.join(METRICS_DIR, "results.json")
TOKEN_ESTIMATE_PER_CHAR = 0.25  # Estimación: ~4 chars por token

# =============================================================
# CONFIGURACIÓN DE CONFLICTOS
# =============================================================
MAX_ACTIVE_RESERVATIONS_PER_GUEST = 1
CONFLICT_AUTO_RESOLVE = True

# =============================================================
# MAPEO DE INTENCIÓN → AGENTE
# =============================================================
INTENT_AGENT_MAP = {
    "reservar": RESERVATION_AGENT_ID,
    "reserva": RESERVATION_AGENT_ID,
    "disponibilidad": RESERVATION_AGENT_ID,
    "habitacion": RESERVATION_AGENT_ID,
    "checkin": CHECKIN_AGENT_ID,
    "check-in": CHECKIN_AGENT_ID,
    "registro": CHECKIN_AGENT_ID,
    "llegada": CHECKIN_AGENT_ID,
    "limpieza": CUSTOMER_SERVICE_AGENT_ID,
    "mantenimiento": CUSTOMER_SERVICE_AGENT_ID,
    "toallas": CUSTOMER_SERVICE_AGENT_ID,
    "servicio": CUSTOMER_SERVICE_AGENT_ID,
    "reclamo": CUSTOMER_SERVICE_AGENT_ID,
    "queja": CUSTOMER_SERVICE_AGENT_ID,
    "informacion": CUSTOMER_SERVICE_AGENT_ID,
    "restaurante": CUSTOMER_SERVICE_AGENT_ID,
    "checkout": BILLING_AGENT_ID,
    "check-out": BILLING_AGENT_ID,
    "salida": BILLING_AGENT_ID,
    "factura": BILLING_AGENT_ID,
    "pago": BILLING_AGENT_ID,
    "cuenta": BILLING_AGENT_ID,
    "feedback": FEEDBACK_AGENT_ID,
    "opinion": FEEDBACK_AGENT_ID,
    "encuesta": FEEDBACK_AGENT_ID,
    "comentario": FEEDBACK_AGENT_ID,
    "calificacion": FEEDBACK_AGENT_ID,
    "experiencia": FEEDBACK_AGENT_ID,
}
