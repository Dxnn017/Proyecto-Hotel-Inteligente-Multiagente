"""
Aplicación Streamlit: Sistema de Gestión Hotelera Inteligente.
"""

import json
import time
from datetime import datetime, date
import streamlit as st

st.set_page_config(
    page_title="Sistema Hotelero Inteligente",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .hotel-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    
    .hotel-subtitle {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    .dashboard-card {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
        border-top: 3px solid #2563EB;
        height: 100%;
    }
    
    .dash-val { font-size: 2.2rem; font-weight: 700; color: #1E293B; }
    .dash-label { font-size: 0.85rem; color: #64748B; text-transform: uppercase; font-weight: 600; }
    
    .badge-success { padding: 4px 10px; border-radius: 6px; background-color: #DCFCE7; color: #166534; font-weight: 600; font-size: 0.85rem; }
    .badge-escalated { padding: 4px 10px; border-radius: 6px; background-color: #FFEDD5; color: #9A3412; font-weight: 600; font-size: 0.85rem; }
    .badge-info { padding: 4px 10px; border-radius: 6px; background-color: #DBEAFE; color: #1E40AF; font-weight: 600; font-size: 0.85rem; }
    .badge-error { padding: 4px 10px; border-radius: 6px; background-color: #FEE2E2; color: #991B1B; font-weight: 600; font-size: 0.85rem; }
    
    .result-box {
        background-color: #F8FAFC; border-left: 4px solid #3B82F6; padding: 1.5rem; border-radius: 6px; margin-top: 1rem; border-right: 1px solid #E2E8F0; border-top: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0;
    }
    
    @media (prefers-color-scheme: dark) {
        .hotel-title { color: #F8FAFC; }
        .hotel-subtitle { color: #94A3B8; }
        .dashboard-card { background-color: #1E293B; border-color: #334155; border-top-color: #3B82F6; }
        .dash-val { color: #F8FAFC; }
        .dash-label { color: #94A3B8; }
        .result-box { background-color: #0F172A; border-color: #334155; border-left-color: #3B82F6; }
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# INICIALIZACIÓN DEL SISTEMA
# -------------------------------------------------------------
if "infra_initialized" not in st.session_state:
    try:
        from core.event_bus import EventBus
        from core.shared_memory import SharedMemory
        from core.conversation_history import ConversationHistory
        from metrics.metrics_logger import MetricsLogger
        from agents.orchestrator_agent import OrchestratorAgent

        st.session_state.event_bus = EventBus()
        st.session_state.shared_memory = SharedMemory()
        st.session_state.conversation_history = ConversationHistory()
        st.session_state.metrics_logger = MetricsLogger()
        st.session_state.orchestrator = OrchestratorAgent(
            shared_memory=st.session_state.shared_memory,
            event_bus=st.session_state.event_bus,
            conversation_history=st.session_state.conversation_history,
            metrics_logger=st.session_state.metrics_logger
        )
        
        st.session_state.mcp_envelope_sent = None
        st.session_state.mcp_envelope_received = None
        st.session_state.infra_initialized = True
        st.session_state.op_result = None
    except Exception as e:
        st.session_state.infra_initialized = False
        st.error(f"Error crítico: {str(e)}")

if not st.session_state.infra_initialized:
    st.stop()

eb = st.session_state.event_bus
sm = st.session_state.shared_memory
ch = st.session_state.conversation_history
ml = st.session_state.metrics_logger
orchestrator = st.session_state.orchestrator

def execute_operation(intent: str, payload: dict, is_swarm: bool = False):
    try:
        req = {
            "guest_id": payload.get("guest_id") or payload.get("billing", {}).get("guest_id") or "G_NUEVO",
            "intent_hint": intent,
            "raw_text": f"Operación desde Recepción: {intent}",
            "payload": payload
        }
        
        if is_swarm:
            st.session_state.mcp_envelope_sent = {
                "swarm_orchestration": "SwarmManager activado",
                "tasks": [{"agent_id": "billing_agent", "payload": payload["billing"]}, {"agent_id": "feedback_agent", "payload": payload["feedback"]}]
            }
        else:
            target_agent = getattr(orchestrator, '_route_intent', lambda x: "unknown")(intent.lower())
            st.session_state.mcp_envelope_sent = {
                "jsonrpc": "2.0", "method": "tools/call", "params": {"name": target_agent, "arguments": payload}, "id": "mcp-call"
            }
            
        res = orchestrator.process_request(req)
        
        if is_swarm:
            st.session_state.mcp_envelope_received = {"swarm_status": "completed", "results": res.get("response", {}).get("results", []) if isinstance(res, dict) else res}
        else:
            st.session_state.mcp_envelope_received = {"jsonrpc": "2.0", "result": res.get("response", res) if isinstance(res, dict) else res, "id": "mcp-call"}
            
        if hasattr(ml, 'save_metrics'): ml.save_metrics()
        
        st.session_state.op_result = res
        return True
    except Exception as e:
        st.session_state.op_result = {"success": False, "error_handled": True, "final_message": "Error interno al procesar la solicitud."}
        return False

def show_result_box():
    if not st.session_state.op_result:
        return
        
    res = st.session_state.op_result
    
    if res.get("error_handled"):
        st.error(res["final_message"])
        return
        
    final_resp = res.get("response", {}) if isinstance(res, dict) else {}
    status_str = final_resp.get("status", "success") if isinstance(final_resp, dict) else "success"
    msg_str = res.get("final_message", "") if isinstance(res, dict) else str(res)
    
    is_escalated = status_str == "escalated"
    is_failed = (not res.get("success", False)) if isinstance(res, dict) else False
    has_conflict = "conflict_resolution" in final_resp or "Conflicto" in msg_str
    
    if is_failed: badge = '<span class="badge-error">Rechazado / Error</span>'
    elif is_escalated: badge = '<span class="badge-escalated">Escalado a Staff</span>'
    elif has_conflict: badge = '<span class="badge-info">Resuelto Automáticamente</span>'
    else: badge = '<span class="badge-success">Operación Completada</span>'
    
    target = res.get('target_agent', 'Orquestador') if isinstance(res, dict) else 'N/A'
    
    st.markdown(f"""
    <div class="result-box">
        <h4 style="margin-top:0;">📋 Resultado de la Operación</h4>
        <p><strong>Estado:</strong> {badge}</p>
        <p><strong>Atendido por IA:</strong> <code>{target}</code></p>
        <p><strong>Respuesta al Huésped:</strong><br/> <i>{msg_str}</i></p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🔍 Ver mensaje MCP/JSON técnico"):
        st.json(st.session_state.mcp_envelope_sent or {})
        st.json(st.session_state.mcp_envelope_received or {})

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
st.sidebar.markdown("### 🏨 Navegación")
views = [
    "Inicio", "Reservas", "Check-in Digital", "Atención al Huésped", 
    "Facturación / Check-out", "Feedback y Fidelización", 
    "Panel Técnico IA", "Escenarios de Prueba"
]
selected_view = st.sidebar.radio("Módulos", views)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reiniciar Sistema", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# -------------------------------------------------------------
# CABECERA GLOBAL (Excepto para paneles técnicos)
# -------------------------------------------------------------
if selected_view not in ["Panel Técnico IA", "Escenarios de Prueba"]:
    st.markdown('<div class="hotel-title">Sistema de Gestión Hotelera</div>', unsafe_allow_html=True)
    st.markdown('<div class="hotel-subtitle">Plataforma inteligente para reservas, check-in, atención al huésped, facturación y fidelización</div>', unsafe_allow_html=True)

# -------------------------------------------------------------
# 1. INICIO (DASHBOARD)
# -------------------------------------------------------------
if selected_view == "Inicio":
    
    r_activas = len(getattr(sm, 'get_active_reservations', lambda: [])())
    habitaciones = getattr(sm, '_rooms', [])
    h_disp = len([r for r in habitaciones if r.get("status") == "disponible"])
    checkins = len([g for g in getattr(sm, '_guests', {}).values() if g.get('stage') in ['checkin_completado', 'en_estadia', 'checkout_completado']])
    solicitudes = sum(len(g.get('service_requests', [])) for g in getattr(sm, '_guests', {}).values())
    facturas = len([g for g in getattr(sm, '_guests', {}).values() if g.get('stage') == 'checkout_completado'])
    feedbacks = len([g for g in getattr(sm, '_guests', {}).values() if g.get('feedback', {}).get('submitted')])
    
    metrics = getattr(ml, 'metrics', {})
    escalados = metrics.get("human_escalations", 0)
    swarms = metrics.get("swarms_executed", 0)
    
    st.markdown("### 📊 Dashboard de Operaciones en Tiempo Real")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="dashboard-card"><div class="dash-val">{h_disp}</div><div class="dash-label">Hab. Disponibles</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dashboard-card"><div class="dash-val">{r_activas}</div><div class="dash-label">Reservas Activas</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="dashboard-card"><div class="dash-val">{checkins}</div><div class="dash-label">Check-ins Hoy</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="dashboard-card"><div class="dash-val">{solicitudes}</div><div class="dash-label">Solicitudes Pendientes</div></div>', unsafe_allow_html=True)
    
    st.write("")
    
    c5, c6, c7, c8 = st.columns(4)
    c5.markdown(f'<div class="dashboard-card"><div class="dash-val">{facturas}</div><div class="dash-label">Facturas Emitidas</div></div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="dashboard-card"><div class="dash-val">{feedbacks}</div><div class="dash-label">Feedback Recibido</div></div>', unsafe_allow_html=True)
    c7.markdown(f'<div class="dashboard-card"><div class="dash-val">{escalados}</div><div class="dash-label">Casos Escalados (Staff)</div></div>', unsafe_allow_html=True)
    c8.markdown(f'<div class="dashboard-card"><div class="dash-val">{swarms}</div><div class="dash-label">Operaciones Complejas</div></div>', unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. RESERVAS
# -------------------------------------------------------------
elif selected_view == "Reservas":
    st.markdown("### 📅 Nueva Reserva")
    
    with st.form("form_reservas"):
        col1, col2 = st.columns(2)
        with col1:
            r_name = st.text_input("Nombre del huésped")
            r_doc = st.text_input("Documento de identidad")
            r_email = st.text_input("Correo electrónico")
        with col2:
            r_type = st.selectbox("Tipo de habitación", ["simple", "doble", "matrimonial", "suite"])
            r_guests = st.number_input("Número de huéspedes", min_value=1, max_value=5, value=1)
            r_dates = st.date_input("Fechas de estadía", value=(date.today(), date.today()))
            
        submitted = st.form_submit_button("Consultar disponibilidad y reservar", type="primary")
        
        if submitted:
            if not r_name:
                st.warning("El nombre es requerido.")
            else:
                payload = {
                    "action": "crear_reserva",
                    "guest_name": r_name,
                    "guest_email": r_email,
                    "document_number": r_doc,
                    "room_type": r_type,
                    "num_guests": r_guests,
                    "check_in_date": r_dates[0].isoformat() if isinstance(r_dates, tuple) and len(r_dates)>0 else date.today().isoformat(),
                    "check_out_date": r_dates[1].isoformat() if isinstance(r_dates, tuple) and len(r_dates)>1 else date.today().isoformat()
                }
                execute_operation(f"reservar habitacion {r_type}", payload)
                
    show_result_box()

# -------------------------------------------------------------
# 3. CHECK-IN DIGITAL
# -------------------------------------------------------------
elif selected_view == "Check-in Digital":
    st.markdown("### 🔑 Check-in Digital")
    
    with st.form("form_checkin"):
        col1, col2 = st.columns(2)
        with col1:
            c_code = st.text_input("ID de Reserva o Guest ID", placeholder="Ej. G_DEMO_01")
            c_doc = st.text_input("Documento de identidad")
        with col2:
            c_name = st.text_input("Nombre completo")
            c_valid = st.checkbox("Documento validado visualmente", value=True)
            
        submitted = st.form_submit_button("Validar check-in", type="primary")
        
        if submitted:
            if not c_code:
                st.warning("El ID es requerido.")
            else:
                # Si proveen nombre/doc se intenta validar identidad, sino confirmar checkin directo
                if c_name and c_doc:
                    payload = {"action": "validar_identidad", "guest_id": c_code, "guest_name": c_name, "document_type": "dni", "document_number": c_doc}
                    intent = "check-in identidad"
                else:
                    payload = {"action": "confirmar_checkin", "guest_id": c_code}
                    intent = "hacer check-in"
                    
                execute_operation(intent, payload)
                
    show_result_box()

# -------------------------------------------------------------
# 4. ATENCIÓN AL HUÉSPED
# -------------------------------------------------------------
elif selected_view == "Atención al Huésped":
    st.markdown("### 🛎️ Solicitudes de Huéspedes")
    
    with st.form("form_atencion"):
        a_id = st.text_input("ID del Huésped", placeholder="Ej. G_DEMO_01")
        a_room = st.text_input("Número de habitación")
        a_type = st.selectbox("Tipo de solicitud", ["limpieza", "mantenimiento", "restaurante", "informacion", "reclamo"])
        a_desc = st.text_area("Descripción detallada")
        
        submitted = st.form_submit_button("Enviar solicitud", type="primary")
        
        if submitted:
            if not a_id:
                st.warning("El ID del huésped es requerido.")
            else:
                payload = {
                    "action": "crear_solicitud",
                    "guest_id": a_id,
                    "room_number": a_room,
                    "service_category": a_type,
                    "description": a_desc or f"Solicitud de {a_type}"
                }
                execute_operation(f"pedir {a_type}", payload)
                
    show_result_box()

# -------------------------------------------------------------
# 5. FACTURACIÓN / CHECK-OUT
# -------------------------------------------------------------
elif selected_view == "Facturación / Check-out":
    st.markdown("### 💳 Facturación y Salida")
    
    with st.form("form_facturacion"):
        f_id = st.text_input("ID del Huésped", placeholder="Ej. G_DEMO_01")
        st.markdown("**Agregar Consumos (Opcional):**")
        col1, col2 = st.columns(2)
        with col1:
            f_cat = st.selectbox("Categoría", ["ninguno", "restaurante", "minibar", "lavanderia", "room_service", "otros"])
        with col2:
            f_amt = st.number_input("Monto ($)", min_value=0.0, value=0.0, step=1.0)
            
        f_method = st.selectbox("Método de pago", ["efectivo", "tarjeta_credito", "tarjeta_debito", "transferencia"])
        f_confirm = st.checkbox("Confirmar salida del huésped y liberar habitación")
        
        submitted = st.form_submit_button("Calcular factura y hacer check-out", type="primary")
        
        if submitted:
            if not f_id:
                st.warning("El ID del huésped es requerido.")
            elif not f_confirm:
                st.warning("Debe confirmar la salida marcando la casilla.")
            else:
                if f_cat != "ninguno" and f_amt > 0:
                    # Registrar consumo manualmente en memoria antes de facturar
                    if hasattr(sm, 'register_consumption'):
                        sm.register_consumption(f_id, {"type": f_cat, "amount": f_amt, "description": f"Consumo manual de {f_cat}"})
                
                payload = {
                    "action": "confirmar_checkout",
                    "guest_id": f_id,
                    "payment_method": f_method
                }
                execute_operation("hacer checkout factura", payload)
                
    show_result_box()

# -------------------------------------------------------------
# 6. FEEDBACK Y FIDELIZACIÓN
# -------------------------------------------------------------
elif selected_view == "Feedback y Fidelización":
    st.markdown("### ⭐ Encuesta de Satisfacción")
    
    with st.form("form_feedback"):
        fb_id = st.text_input("ID del Huésped", placeholder="Ej. G_DEMO_01")
        fb_rating = st.slider("Calificación de la estadía", 1, 5, 5)
        fb_comment = st.text_area("Comentarios del huésped")
        fb_promo = st.checkbox("Acepta recibir promociones y alertas", value=True)
        
        submitted = st.form_submit_button("Enviar feedback", type="primary")
        
        if submitted:
            if not fb_id:
                st.warning("El ID del huésped es requerido.")
            else:
                payload = {
                    "action": "recibir_feedback",
                    "guest_id": fb_id,
                    "rating": fb_rating,
                    "comment": fb_comment or "Sin comentarios adicionales."
                }
                intent = "dejar feedback excelente" if fb_rating >= 4 else "dejar feedback malo"
                execute_operation(intent, payload)
                
    show_result_box()

# -------------------------------------------------------------
# 7. PANEL TÉCNICO IA
# -------------------------------------------------------------
elif selected_view == "Panel Técnico IA":
    st.markdown("## ⚙️ Panel Técnico IA")
    st.markdown("Vista de auditoría para examinar la arquitectura multiagente subyacente.")
    
    tech_tabs = st.tabs(["Agentes", "MCP / JSON", "Memoria", "Event Bus", "Conflictos", "Swarms", "Métricas"])
    
    with tech_tabs[0]:
        st.markdown("#### Agentes de IA Activos")
        st.json({
            "Orquestador": "Enruta intenciones y maneja swarms",
            "ReservationAgent": "Maneja disponibilidad y reservas",
            "CheckinAgent": "Valida esquemas de identidad",
            "CustomerServiceAgent": "Resuelve o escala solicitudes",
            "BillingAgent": "Calcula consumos y factura",
            "FeedbackAgent": "Analiza sentimiento"
        })
        
    with tech_tabs[1]:
        st.markdown("#### Capa MCP (Model Context Protocol)")
        col_mcp1, col_mcp2 = st.columns(2)
        with col_mcp1:
            st.markdown("**Última Petición JSON-RPC**")
            st.json(st.session_state.mcp_envelope_sent or {})
        with col_mcp2:
            st.markdown("**Última Respuesta JSON-RPC**")
            st.json(st.session_state.mcp_envelope_received or {})
            
    with tech_tabs[2]:
        st.markdown("#### Memoria Compartida (Estado de Huéspedes)")
        try:
            all_guests = getattr(sm, 'get_all_guest_ids', lambda: [])()
            if all_guests:
                guest = st.selectbox("Seleccionar huésped:", all_guests)
                st.json(getattr(sm, 'get_guest', lambda x: {})(guest))
            else:
                st.info("Memoria vacía.")
        except: st.info("Error al leer memoria.")
            
    with tech_tabs[3]:
        st.markdown("#### Event Bus (Publicar/Suscribir)")
        try:
            events = getattr(eb, 'get_all_events', lambda: [])()
            if events: st.dataframe(events, use_container_width=True)
            else: st.info("Sin eventos.")
        except: st.info("Sin eventos.")
            
    with tech_tabs[4]:
        st.markdown("#### Conflictos Resueltos por el Sistema")
        resolver = getattr(orchestrator, "conflict_resolver", None)
        history = getattr(resolver, "_resolved_conflicts", [])
        if history:
            for h in history: st.json(h)
        else:
            st.info("No se han detectado conflictos.")
                
    with tech_tabs[5]:
        st.markdown("#### Operaciones Swarm (Coordinación de Agentes)")
        s_manager = getattr(orchestrator, "swarm_manager", None)
        s_history = getattr(s_manager, "get_swarm_history", lambda: [])()
        if s_history:
            for h in s_history: st.json(h)
        else:
            st.info("No se han ejecutado Swarms.")
                
    with tech_tabs[6]:
        st.markdown("#### Exportador de Métricas de Sistema")
        try:
            with open("metrics/results.json", "r") as f:
                st.json(json.load(f))
        except:
            st.info("Métricas no disponibles.")

# -------------------------------------------------------------
# 8. ESCENARIOS DE PRUEBA (Anterior Demo)
# -------------------------------------------------------------
elif selected_view == "Escenarios de Prueba":
    st.markdown("## 🧪 Escenarios de Prueba (Modo Simulación)")
    st.markdown("Ejecución rápida de casos de negocio empaquetados para validar la lógica y respuestas de la IA.")
    
    # Se restauran los escenarios del requerimiento original pero encapsulados
    TEST_SCENARIOS = {
        "Reserva Exitosa": {"intent": "reservar", "payload": {"action": "crear_reserva", "guest_name": "Juan Test", "room_type": "matrimonial"}, "pre_func": None},
        "Reserva Sin Disponibilidad": {"intent": "reservar suite", "payload": {"action": "crear_reserva", "guest_name": "Ana S", "room_type": "suite"}, "pre_func": lambda s: [s.update_room_status(r["room_id"], "ocupada") for r in s._rooms if r["room_type"] == "suite"] if hasattr(s, 'update_room_status') else None},
        "Check-in Válido": {"intent": "checkin", "payload": {"action": "confirmar_checkin", "guest_id": "G_DEMO_01"}, "pre_func": lambda s: [s.create_guest("Juan Test", "juan@test.com") if not s.guest_exists("G_DEMO_01") else None, s.update_reservation("G_DEMO_01", {"reservation_id": "RES-01", "guest_id": "G_DEMO_01", "room_type": "matrimonial", "status": "confirmada"}) if not s.get_reservation("G_DEMO_01") else None]},
        "Check-in Inválido": {"intent": "checkin falso", "payload": {"action": "validar_identidad", "guest_id": "G004", "guest_name": "M", "document_type": "dni", "document_number": "1"}, "pre_func": None},
        "Solicitud de Limpieza": {"intent": "limpieza", "payload": {"action": "crear_solicitud", "guest_id": "G_DEMO_01", "service_category": "limpieza", "description": "Limpiar"}, "pre_func": lambda s: s.create_guest("Juan Test", "") if not s.guest_exists("G_DEMO_01") else None},
        "Mantenimiento Escalado": {"intent": "mantenimiento", "payload": {"action": "crear_solicitud", "guest_id": "G_DEMO_01", "service_category": "mantenimiento", "description": "Gotea"}, "pre_func": lambda s: s.create_guest("Juan Test", "") if not s.guest_exists("G_DEMO_01") else None},
        "Check-out con Consumos": {"intent": "checkout", "payload": {"action": "confirmar_checkout", "guest_id": "G_DEMO_01", "payment_method": "tarjeta_credito"}, "pre_func": lambda s: [s.create_guest("Juan Test", "") if not s.guest_exists("G_DEMO_01") else None, s.update_reservation("G_DEMO_01", {"reservation_id": "RES-01", "guest_id": "G_DEMO_01", "room_type": "matrimonial", "room_assigned": "201", "status": "confirmada"}) if not s.get_reservation("G_DEMO_01") else None, s.update_checkin("G_DEMO_01", "completado", "201", True), s.register_consumption("G_DEMO_01", {"type": "minibar", "amount": 45.0, "description": "Snacks"}) if len(s.get_consumptions("G_DEMO_01")) == 0 else None]},
        "Feedback Positivo": {"intent": "feedback 5", "payload": {"action": "recibir_feedback", "guest_id": "G_DEMO_01", "rating": 5, "comment": "Genial."}, "pre_func": lambda s: s.create_guest("Juan Test", "") if not s.guest_exists("G_DEMO_01") else None},
        "Feedback Negativo": {"intent": "feedback 1", "payload": {"action": "recibir_feedback", "guest_id": "G005", "rating": 1, "comment": "Malo."}, "pre_func": None},
        "Conflicto Habitación": {"intent": "checkin", "payload": {"action": "confirmar_checkin", "guest_id": "G003"}, "pre_func": lambda s: s.update_room_status("203", "ocupada") if hasattr(s, 'update_room_status') else None},
        "Swarm Check-out+Queja": {"intent": "quiero hacer checkout y dejar queja", "payload": {"billing": {"action": "confirmar_checkout", "guest_id": "G001", "payment_method": "efectivo"}, "feedback": {"action": "recibir_feedback", "guest_id": "G001", "rating": 2, "comment": "Ruido."}}, "pre_func": None}
    }
    
    selected_test = st.selectbox("Seleccionar Prueba", list(TEST_SCENARIOS.keys()))
    
    if st.button("Ejecutar Prueba Simulada", type="primary"):
        data = TEST_SCENARIOS[selected_test]
        if data["pre_func"]:
            data["pre_func"](sm)
            
        is_swarm = "billing" in data["payload"]
        execute_operation(data["intent"], data["payload"], is_swarm)
        
    show_result_box()

