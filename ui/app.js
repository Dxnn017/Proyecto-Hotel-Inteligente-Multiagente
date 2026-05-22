/* ═══════════════════════════════════════════════════════════
   Hotel Inteligente – Lógica del Frontend
   ═══════════════════════════════════════════════════════════ */

// ── Estado global ────────────────────────────────────────────
let lastMcpRequest = null;
let lastMcpResponse = null;

// ── Navegación ───────────────────────────────────────────────

const SECTION_TITLES = {
    inicio:      { title: "Dashboard de Operaciones",         sub: "Vista general del estado del hotel en tiempo real" },
    reservas:    { title: "Gestión de Reservas",              sub: "Consulte disponibilidad y registre nuevas reservas" },
    checkin:     { title: "Check-in Digital",                 sub: "Valide la identidad del huésped y asigne habitación" },
    atencion:    { title: "Atención al Huésped",              sub: "Registre solicitudes de servicio y atención" },
    facturacion: { title: "Facturación y Check-out",          sub: "Consolide consumos y procese la salida del huésped" },
    feedback:    { title: "Feedback y Fidelización",          sub: "Capture la opinión del huésped y genere promociones" },
    tecnico:     { title: "Panel Técnico IA",                 sub: "Arquitectura multiagente, MCP, memoria y métricas" },
};

function navigateTo(sectionId) {
    // Ocultar todas las secciones
    document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
    // Activar la seleccionada
    const sec = document.getElementById("sec-" + sectionId);
    if (sec) sec.classList.add("active");

    // Actualizar links del sidebar
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    const link = document.querySelector(`.nav-link[data-section="${sectionId}"]`);
    if (link) link.classList.add("active");

    // Actualizar header
    const info = SECTION_TITLES[sectionId] || { title: "", sub: "" };
    document.getElementById("page-title").textContent = info.title;
    document.getElementById("page-subtitle").textContent = info.sub;

    // Si es inicio, recargar KPIs
    if (sectionId === "inicio") loadDashboard();
}

document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", e => {
        e.preventDefault();
        navigateTo(link.dataset.section);
    });
});

// ── Tabs del panel técnico ───────────────────────────────────

document.querySelectorAll(".tech-tab").forEach(tab => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".tech-tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".tech-panel").forEach(p => p.classList.remove("active"));
        tab.classList.add("active");
        const panel = document.getElementById(tab.dataset.tab);
        if (panel) panel.classList.add("active");
    });
});


// ══════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════

async function apiPost(url, body) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    return res.json();
}

async function apiGet(url) {
    const res = await fetch(url);
    return res.json();
}

function renderResult(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const resp = data.response || {};
    const msg = data.final_message || resp.response_message || "Operación procesada.";
    const agent = data.target_agent || "Orquestador";
    const success = data.success !== false;
    const status = resp.status || (success ? "success" : "error");

    let badgeClass, badgeText;
    if (!success)                    { badgeClass = "badge-error"; badgeText = "Error / Rechazado"; }
    else if (status === "escalated") { badgeClass = "badge-warn";  badgeText = "Escalado a Staff"; }
    else if (msg.includes("Conflicto") || msg.includes("reasign")) { badgeClass = "badge-info"; badgeText = "Resuelto Automáticamente"; }
    else                             { badgeClass = "badge-success"; badgeText = "Operación Exitosa"; }

    // Guardar MCP para el panel técnico
    if (data.mcp_request)  { lastMcpRequest = data.mcp_request; }
    if (data.mcp_response) { lastMcpResponse = data.mcp_response; }
    updateMcpPanel();

    const mcpId = "mcp-detail-" + containerId;
    container.innerHTML = `
        <div class="result-box">
            <h4>📋 Resultado de la Operación</h4>
            <p><strong>Estado:</strong> <span class="badge ${badgeClass}">${badgeText}</span></p>
            <p><strong>Atendido por:</strong> <code>${agent}</code></p>
            <p><strong>Respuesta:</strong><br><em>${msg}</em></p>
            <div class="mcp-toggle" onclick="document.getElementById('${mcpId}').classList.toggle('open')">
                🔍 Ver detalles técnicos (MCP / JSON)
            </div>
            <div class="mcp-detail" id="${mcpId}">
                <pre>${JSON.stringify(data, null, 2)}</pre>
            </div>
        </div>
    `;
}

function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) container.innerHTML = '<p><span class="spinner"></span> Procesando solicitud…</p>';
}

function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) container.innerHTML = `<div class="result-box"><p style="color:#DC2626;"><strong>⚠️ ${message}</strong></p></div>`;
}

function updateMcpPanel() {
    const reqEl = document.getElementById("mcp-request");
    const resEl = document.getElementById("mcp-response");
    if (reqEl && lastMcpRequest)  reqEl.textContent = JSON.stringify(lastMcpRequest, null, 2);
    if (resEl && lastMcpResponse) resEl.textContent = JSON.stringify(lastMcpResponse, null, 2);
}


// ══════════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════════

async function loadDashboard() {
    try {
        const d = await apiGet("/api/dashboard");
        const grid = document.getElementById("kpi-grid");
        if (!grid) return;
        grid.innerHTML = `
            <div class="kpi-card"><div class="kpi-value">${d.rooms_available}</div><div class="kpi-label">Hab. Disponibles</div></div>
            <div class="kpi-card"><div class="kpi-value">${d.active_reservations}</div><div class="kpi-label">Reservas Activas</div></div>
            <div class="kpi-card"><div class="kpi-value">${d.checkins_today}</div><div class="kpi-label">Check-ins</div></div>
            <div class="kpi-card"><div class="kpi-value">${d.service_requests}</div><div class="kpi-label">Solicitudes</div></div>
            <div class="kpi-card"><div class="kpi-value">${d.invoices}</div><div class="kpi-label">Facturas</div></div>
            <div class="kpi-card"><div class="kpi-value">${d.feedbacks}</div><div class="kpi-label">Feedback</div></div>
            <div class="kpi-card"><div class="kpi-value">${d.human_escalations}</div><div class="kpi-label">Escalaciones</div></div>
            <div class="kpi-card"><div class="kpi-value">${d.swarms_executed}</div><div class="kpi-label">Swarms</div></div>
        `;
    } catch { /* silently fail */ }
}


// ══════════════════════════════════════════════════════════════
// FORMULARIOS
// ══════════════════════════════════════════════════════════════

// ── Reservas ─────────────────────────────────────────────────
document.getElementById("form-reservas").addEventListener("submit", async e => {
    e.preventDefault();
    showLoading("result-reservas");
    try {
        const data = await apiPost("/api/reservations", {
            guest_name:     document.getElementById("res-name").value,
            document_number: document.getElementById("res-doc").value,
            guest_email:    document.getElementById("res-email").value,
            phone:          document.getElementById("res-phone").value,
            room_type:      document.getElementById("res-type").value,
            num_guests:     parseInt(document.getElementById("res-guests").value) || 1,
            check_in_date:  document.getElementById("res-checkin").value,
            check_out_date: document.getElementById("res-checkout").value,
        });
        renderResult("result-reservas", data);
    } catch (err) {
        showError("result-reservas", "No se pudo conectar con el servidor.");
    }
});

// ── Check-in ─────────────────────────────────────────────────
document.getElementById("form-checkin").addEventListener("submit", async e => {
    e.preventDefault();
    showLoading("result-checkin");
    try {
        const data = await apiPost("/api/checkin", {
            guest_id:        document.getElementById("chk-id").value,
            document_number: document.getElementById("chk-doc").value,
            guest_name:      document.getElementById("chk-name").value,
        });
        renderResult("result-checkin", data);
    } catch (err) {
        showError("result-checkin", "No se pudo conectar con el servidor.");
    }
});

// ── Atención ─────────────────────────────────────────────────
document.getElementById("form-atencion").addEventListener("submit", async e => {
    e.preventDefault();
    showLoading("result-atencion");
    try {
        const data = await apiPost("/api/service-request", {
            guest_id:         document.getElementById("srv-id").value,
            room_number:      document.getElementById("srv-room").value,
            service_category: document.getElementById("srv-type").value,
            description:      document.getElementById("srv-desc").value,
        });
        renderResult("result-atencion", data);
    } catch (err) {
        showError("result-atencion", "No se pudo conectar con el servidor.");
    }
});

// ── Facturación ──────────────────────────────────────────────
document.getElementById("form-facturacion").addEventListener("submit", async e => {
    e.preventDefault();
    showLoading("result-facturacion");
    try {
        const consumptions = [];
        const types = [
            { id: "bill-restaurant", type: "restaurante" },
            { id: "bill-minibar",    type: "minibar" },
            { id: "bill-laundry",    type: "lavanderia" },
            { id: "bill-room-service", type: "room_service" },
        ];
        types.forEach(t => {
            const val = parseFloat(document.getElementById(t.id).value) || 0;
            if (val > 0) consumptions.push({ type: t.type, amount: val, description: t.type });
        });

        const data = await apiPost("/api/billing", {
            guest_id:       document.getElementById("bill-id").value,
            payment_method: document.getElementById("bill-method").value,
            consumptions:   consumptions,
        });
        renderResult("result-facturacion", data);
    } catch (err) {
        showError("result-facturacion", "No se pudo conectar con el servidor.");
    }
});

// ── Feedback ─────────────────────────────────────────────────
document.getElementById("form-feedback").addEventListener("submit", async e => {
    e.preventDefault();
    showLoading("result-feedback");
    try {
        const data = await apiPost("/api/feedback", {
            guest_id: document.getElementById("fb-id").value,
            rating:   parseInt(document.getElementById("fb-rating").value),
            comment:  document.getElementById("fb-comment").value,
        });
        renderResult("result-feedback", data);
    } catch (err) {
        showError("result-feedback", "No se pudo conectar con el servidor.");
    }
});


// ══════════════════════════════════════════════════════════════
// PANEL TÉCNICO – Loaders
// ══════════════════════════════════════════════════════════════

async function loadMemory() {
    try {
        const d = await apiGet("/api/memory");
        document.getElementById("memory-json").textContent = JSON.stringify(d, null, 2);
    } catch { document.getElementById("memory-json").textContent = "Error al cargar."; }
}

async function loadEvents() {
    try {
        const d = await apiGet("/api/events");
        document.getElementById("events-json").textContent = JSON.stringify(d, null, 2);
    } catch { document.getElementById("events-json").textContent = "Error al cargar."; }
}

async function loadConflicts() {
    try {
        const d = await apiGet("/api/conflicts");
        document.getElementById("conflicts-json").textContent = JSON.stringify(d, null, 2);
    } catch { document.getElementById("conflicts-json").textContent = "Error al cargar."; }
}

async function loadSwarms() {
    try {
        const d = await apiGet("/api/swarms");
        document.getElementById("swarms-json").textContent = JSON.stringify(d, null, 2);
    } catch { document.getElementById("swarms-json").textContent = "Error al cargar."; }
}

async function loadMetrics() {
    try {
        const d = await apiGet("/api/metrics");
        document.getElementById("metrics-json").textContent = JSON.stringify(d, null, 2);
    } catch { document.getElementById("metrics-json").textContent = "Error al cargar."; }
}

async function executeSwarm() {
    try {
        document.getElementById("swarms-json").textContent = "Ejecutando swarm…";
        const d = await apiPost("/api/swarm/checkout-complaint", {
            guest_id: "G001",
            payment_method: "efectivo",
            rating: 2,
            comment: "Quiero irme y además hubo mucho ruido.",
        });
        document.getElementById("swarms-json").textContent = JSON.stringify(d, null, 2);
        lastMcpRequest = d.mcp_request;
        lastMcpResponse = d.mcp_response;
        updateMcpPanel();
    } catch { document.getElementById("swarms-json").textContent = "Error al ejecutar swarm."; }
}


// ── Inicialización ───────────────────────────────────────────
loadDashboard();
