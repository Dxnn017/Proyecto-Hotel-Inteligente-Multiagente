# Guion de Defensa del Proyecto

## Presentación General
*Saludos al jurado.* Presentamos el "Hotel Inteligente con 5 Agentes de IA", un sistema diseñado para automatizar el ciclo de vida completo de un huésped utilizando una arquitectura multiagente jerárquica con flujo pipeline.

## Por qué esta Arquitectura
Decidimos usar una arquitectura **Jerárquica con Pipeline** porque:
- Un hotel sigue etapas secuenciales (Reserva -> Check-in -> Estadía -> Checkout -> Feedback).
- Un Orquestador centraliza la recepción, asegura que el payload (JSON) sea válido y previene que el huésped se salte pasos (ej. hacer check-in sin reserva).
- **Por qué NO Estrella Pura:** Porque las tareas dependen unas de otras, no son aisladas.
- **Por qué NO Malla Pura:** Generaría caos de comunicación. Imaginen al agente de limpieza hablando directo con facturación sin que la recepción (orquestador) sepa.

## Cumplimiento de Rúbrica
1. **Diseño Multiagente:** 5 agentes especializados sin solapamiento + 1 Orquestador.
2. **Implementación:** Código escrito simulando comportamientos mediante JSON Schemas y orquestación estructurada.
3. **Comunicación:** JSON validado con schemas estilo MCP, Memoria Compartida para el estado, y Event Bus para asincronismo y Swarms.
4. **Complejidad:** Manejamos Swarms (facturación + feedback) y resolución de conflictos (habitaciones ocupadas, consumos duplicados).

## Preguntas Frecuentes (FAQ para el jurado)
* **Q:** ¿Qué pasa si el huésped pide dos cosas a la vez?
  * **A:** El Orquestador detecta que es un "Swarm" (ej. Checkout y Queja). Llama al `SwarmManager` que delega tareas a los agentes correspondientes de forma coordinada.
* **Q:** ¿Cómo evitan que dos huéspedes reserven la misma habitación?
  * **A:** La memoria compartida actúa como fuente única de verdad. Si ocurre una colisión, el `conflict_resolver.py` detecta el estado "ocupada" y automáticamente asigna otra de igual o superior categoría, o escala a humano.
