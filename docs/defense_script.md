# Guion de Defensa del Proyecto

## Presentación General
*Saludos al jurado.* Presentamos el "Hotel Inteligente con 5 Agentes de IA", un sistema diseñado para automatizar el ciclo de vida completo de un huésped utilizando una arquitectura multiagente jerárquica con flujo pipeline.

---

## Por qué esta Arquitectura
Decidimos usar una arquitectura **Jerárquica con Pipeline** porque:
- Un hotel sigue etapas secuenciales claras (Reserva -> Check-in -> Estadía -> Checkout -> Feedback).
- Un Orquestador centraliza la recepción, asegura que el payload (JSON) sea válido y previene que el huésped se salte pasos (ej. hacer check-in sin reserva).
- **Por qué NO Estrella Pura:** Porque las tareas dependen unas de otras, no son aisladas.
- **Por qué NO Malla Pura:** Generaría caos de comunicación. Imaginen al agente de limpieza hablando directo con facturación sin que la recepción (orquestador) sepa.

---

## Cumplimiento de Rúbrica
1.  **Diseño Multiagente:** 5 agentes especializados sin solapamiento + 1 Orquestador.
2.  **Implementación:** Código escrito simulando comportamientos mediante JSON Schemas y orquestación estructurada.
3.  **Comunicación:** Capa MCP oficial con JSON-RPC 2.0 y schemas strict, Memoria Compartida para el estado, y Event Bus para asincronismo y Swarms.
4.  **Complejidad:** Manejamos Swarms (facturación + feedback) y resolución de conflictos (habitaciones ocupadas, consumos duplicados).

---

## Preguntas Frecuentes (FAQ para el jurado)
*   **Q:** ¿Qué pasa si el huésped pide dos cosas a la vez?
    *   **A:** El Orquestador detecta que es un "Swarm" (ej. Checkout y Queja). Llama al `SwarmManager` que delega tareas a los agentes correspondientes de forma coordinada.
*   **Q:** ¿Cómo evitan que dos huéspedes reserven la misma habitación?
    *   **A:** La memoria compartida actúa como fuente única de verdad. Si ocurre una colisión, el `conflict_resolver.py` detecta el estado "ocupada" y automáticamente asigna otra de igual o superior categoría, o escala a humano.

---

## 🚀 Cómo Demostrar el Despliegue Local con Streamlit

Cuando expongas el proyecto ante tu jurado o profesor, sigue este orden para defender la nota de **Excelente 20/20**:

### 1. Pantalla Principal y Encabezado
*   **Qué mostrar:** La cabecera elegante con el nombre del proyecto, el logo de hotel y el banner informativo de color azul.
*   **Qué decir:** *"Hemos desarrollado un panel web local interactivo de alta fidelidad con Streamlit. Esto nos permite simular peticiones en tiempo real, visualizar la telemetría del sistema y auditar el comportamiento de los agentes sin depender de consolas oscuras."*

### 2. Panel de Métricas Cuantitativas
*   **Qué mostrar:** Las tarjetas superiores de `Éxito Funcional`, `Swarms Ejecutados`, `Conflictos Resueltos`, `Latencia` y `Tokens`.
*   **Qué decir:** *"El sistema recopila métricas operacionales detalladas de cada agente. Vemos la latencia promedio en milisegundos y el consumo simulado de tokens para medir el costo operativo de cada interacción de IA."*

### 3. Ejecución de Escenarios
*   **Qué mostrar:** Selecciona el **Escenario 1** en la barra lateral y presiona **"Ejecutar escenario"**. Luego muestra el resultado verde de éxito. Repite con el **Escenario 10** (Conflicto) y el **Escenario 11** (Swarm).
*   **Qué decir:** *"Podemos ejecutar cualquiera de los 11 escenarios. Por ejemplo, al correr el check-in con una habitación ocupada (Escenario 10), el sistema no falla; activa el resolvedor de conflictos para reubicar al huésped en milisegundos. Al ejecutar Checkout + Queja (Escenario 11), el orquestador lidera un Swarm de agentes en paralelo."*

### 4. Inspección de Mensajes MCP (JSON-RPC)
*   **Qué mostrar:** Dirígete a la pestaña **"Mensajes MCP (JSON-RPC)"**. Muestra la estructura de la petición con el método `tools/call` y los argumentos válidos.
*   **Qué decir:** *"Para asegurar un estándar moderno de desarrollo de agentes, implementamos el Model Context Protocol (MCP) de Anthropic. Toda la comunicación interna utiliza envolturas oficiales JSON-RPC 2.0 y valida estrictamente los payloads mediante JSON-schema antes de llamar a las herramientas de IA."*

### 5. Memoria Compartida e Historial
*   **Qué mostrar:** Abre la pestaña **"Memoria Compartida"**. Selecciona el huésped `G_DEMO_01` en el desplegable y muestra la bitácora de conversación y el estado detallado.
*   **Qué decir:** *"La Memoria Compartida (`SharedMemory`) es la fuente única de la verdad del hotel. Aquí persistimos el perfil completo del huésped (etapa, consumos, lealtad e historial de mensajes) para asegurar consistencia e impedir errores lógicos."*

### 6. Event Bus
*   **Qué mostrar:** Pestaña **"Event Bus"**. Muestra la tabla con el listado de eventos de tipo pub-sub publicados.
*   **Qué decir:** *"Usamos una arquitectura orientada a eventos. Cuando un agente completa una tarea (ej. registrar checkout), publica un evento en el Event Bus (`checkout_confirmado`). Los demás componentes reaccionan reactivamente a estos cambios."*

### 7. Rúbrica y Conclusión
*   **Qué mostrar:** La tabla final de **"Cumplimiento de Rúbrica"** al final de la página.
*   **Qué decir:** *"Como se observa, el proyecto cumple rigurosamente el 100% de la rúbrica exigida en el curso: diseño multiagente óptimo, implementación modular en Python validada con pytest, comunicación por MCP y Swarms complejos. Todo el código es auditable y está documentado para sustentar la calificación sobresaliente."*
