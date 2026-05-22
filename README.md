# 🏨 Hotel Inteligente Multiagente

Un sistema de automatización basado en una arquitectura multiagente jerárquica para la gestión integral del ciclo de vida del huésped en un hotel. Este proyecto demuestra capacidades avanzadas de coordinación entre agentes de IA mediante el protocolo MCP (Model Context Protocol), comunicación asíncrona, memoria compartida y resolución autónoma de conflictos.

## 📋 Descripción General

El **Hotel Inteligente Multiagente** es una prueba de concepto tecnológica (PoC) diseñada para orquestar servicios hoteleros de principio a fin. El sistema traduce las interacciones en lenguaje natural de los huéspedes en acciones estructuradas del sistema y coordina a un equipo de agentes especializados para ejecutarlas, todo bajo un entorno de ejecución local.

## 🎯 El Problema

En la industria hotelera, los diferentes sistemas (reservas, check-in, mantenimiento, facturación, atención al cliente) suelen operar en silos. Cuando un huésped interactúa con el hotel, a menudo enfrenta tiempos de espera mientras el personal humano cruza información entre múltiples interfaces. Especialmente en situaciones de alta demanda o ante conflictos como sobreventa y errores de facturación, la falta de comunicación intersistemas genera malas experiencias.

## 💡 Solución Propuesta

La solución centraliza la intención del usuario a través de un **Agente Orquestador** inteligente que delega tareas específicas a **5 Subagentes Especializados**. Estos agentes operan en una topología jerárquica tipo *pipeline*, donde el orquestador actúa como un enrutador inteligente. Para permitir la comunicación, se ha diseñado una implementación robusta del protocolo **MCP (Model Context Protocol)** con JSON-RPC 2.0 y validaciones esquemáticas formales, asegurando la confiabilidad de las interacciones generativas.

## 🏗️ Arquitectura del Sistema

La arquitectura está construida sobre los siguientes pilares:

- **Topología Jerárquica:** Un orquestador central recibe la petición y enruta el flujo al agente correspondiente.
- **Memoria Compartida (Shared Memory):** Una fuente única de verdad para el estado del hotel (habitaciones, perfiles de huéspedes, consumos).
- **Bus de Eventos (Event Bus):** Un mecanismo asíncrono para publicar eventos de dominio (`reserva_confirmada`, `factura_generada`) permitiendo que el sistema sea reactivo.
- **Gestión de Conflictos:** Un módulo centralizado (`ConflictResolver`) que previene excepciones cuando recursos compartidos colisionan (ej. misma habitación para dos reservas).

## 🤖 Agentes Implementados

1. **Agente de Reservas:** Gestiona disponibilidad, fechas y registro inicial del huésped.
2. **Agente de Check-in:** Realiza validaciones de identidad, control de fraudes y asigna habitaciones reales.
3. **Agente de Atención al Cliente:** Filtra solicitudes. Si es limpieza, la auto-resuelve. Si es mantenimiento, la escala adecuadamente.
4. **Agente de Facturación:** Calcula impuestos, agrega consumos y emite la confirmación de check-out.
5. **Agente de Feedback:** Analiza sentimientos (NPS) del comentario final del usuario y emite promociones de lealtad inmediatas.

## 🔌 Capa MCP (Model Context Protocol)

El sistema integra una capa MCP robusta con:
- **`protocol.py`**: Router MCP que implementa los endpoints `tools/list` y `tools/call` oficiales.
- **`messages.py`**: Estructuras sólidas de validación de JSON-RPC 2.0 (Requests, Responses, Errors).
- **`validator.py`**: Motor de validación semántica con `jsonschema` para asegurar que el LLM del agente siempre cumpla las precondiciones antes de alterar la base de datos simulada.

## 🐝 Modo Swarm (Enjambre)

Cuando el Orquestador detecta que un solo mensaje del usuario tiene intenciones múltiples (Ej: *"Quiero pagar mi cuenta e irme, pero también quiero quejarme del ruido"*), se activa el **Swarm Manager**.
Este componente divide la solicitud original y despacha la ejecución concurrente y colaborativa del *Agente de Facturación* y el *Agente de Feedback*, unificando los resultados al final antes de contestarle al usuario.

## 📂 Estructura del Proyecto

```
hotel/
├── api_server.py             # Backend FastAPI – Interfaz Web principal
├── app.py                    # Interfaz alternativa en Streamlit
├── main.py                   # CLI – Demo por consola (terminal)
├── requirements.txt          # Dependencias del proyecto
├── ui/                       # Frontend HTML/CSS/JS de la aplicación web
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── agents/                   # Definición de Orquestador y 5 Subagentes
├── core/                     # Componentes centrales (SwarmManager, EventBus, Memoria)
├── data/                     # Almacenamiento local simulado (JSON)
├── docs/                     # Documentación técnica, diagramas y diseño
├── mcp/                      # Capa oficial del Model Context Protocol (JSON-RPC)
├── metrics/                  # Exportador de métricas y latencias (results.json)
├── schemas/                  # Archivos .json con jsonschema estricto para cada agente
└── tests/                    # Batería de pruebas unitarias y de integración (pytest)
```

## ⚙️ Requisitos

- Python 3.10 o superior
- pip (Administrador de paquetes de Python)

## 🚀 Despliegue Local

### Aplicación Web (FastAPI) — Recomendado

La interfaz web principal se ejecuta con FastAPI y presenta:
1. **Vista del Sistema Hotelero**: Formularios funcionales para Reservas, Check-in, Atención, Facturación y Feedback.
2. **Panel Técnico IA**: Auditoría de la arquitectura interna (MCP, Memoria, Event Bus, Swarms, Métricas).

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn api_server:app --reload
```

Luego abrir en el navegador: **http://127.0.0.1:8000**

### Otras formas de ejecución

```bash
# Demo por consola (todos los escenarios)
python main.py

# Pruebas automatizadas
pytest tests/

# Interfaz alternativa en Streamlit
streamlit run app.py
```

## 🔭 Mejoras Futuras

- Integrar Modelos de Lenguaje (LLMs) reales mediante APIs externas para reemplazar las simulaciones locales.
- Añadir conexión a una base de datos persistente (PostgreSQL o MongoDB) en lugar de memoria RAM.
- Generar autenticación con JWT para diferenciar roles de agentes vs staff administrativo.

## 👨‍💻 Autor

Proyecto desarrollado como demostración técnica de automatización inteligente y ecosistemas multiagente.
