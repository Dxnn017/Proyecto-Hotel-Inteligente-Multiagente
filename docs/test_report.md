# Reporte de Pruebas Automatizadas

El sistema cuenta con un suite completo de pruebas desarrolladas en Pytest. Estas pruebas aseguran la integridad, comunicación y correcto manejo de excepciones por parte de los agentes.

## Cobertura de Pruebas

| Módulo / Agente | Caso de Prueba | Resultado Esperado | Resultado Obtenido |
|-----------------|----------------|--------------------|--------------------|
| Reservas | Reserva Exitosa | Status = Success, Reservation ID generado | PASA |
| Reservas | Sin Disponibilidad | Status = Failed, Rechazado por sistema | PASA |
| Check-in | Datos Válidos | Status = Success, Check-in completado | PASA |
| Check-in | Datos Inválidos | Status = Failed, Validation errors > 0 | PASA |
| Atención al Cliente | Limpieza (Auto) | Status = Success, Resuelto auto | PASA |
| Atención al Cliente | Mantenimiento | Status = Escalated, Requiere humano | PASA |
| Facturación | Consumos | Status = Success, Total > 0 | PASA |
| Facturación | Checkout Confirmado | Status = Success, Factura generada y estado cerrado | PASA |
| Feedback | Positivo | Status = Success, Promoción generada | PASA |
| Feedback | Negativo | Status = Success, Alerta generada | PASA |
| Orquestador | Enrutamiento | Status = Success, Asigna agente correcto | PASA |
| Orquestador | Schema Validation | Status = Failed, Error de validación | PASA |
| Orquestador | Swarm Detection | Status = Success, Delegación a Swarm Manager | PASA |
| Casos Extremos | Check-in sin reserva| Status = Failed, Redirección a Reservas | PASA |
| Casos Extremos | Conflicto Habitación| Status = Resolved, Nueva habitación asignada | PASA |

## Resumen de Métricas (Éxito Funcional)
> [!NOTE]
> **Éxito Funcional vs Error del Sistema:**
> Los escenarios negativos como "Sin Disponibilidad", "Datos Inválidos" o "Feedback Negativo" son **pruebas controladas** y escenarios esperados. Si el sistema responde con un rechazo o escalamiento correcto según las reglas del negocio, se considera un **Éxito Funcional**. Solo las excepciones no manejadas o errores de enrutamiento cuentan como fallos (Errores Reales).

Al ejecutar las pruebas o la demo, el archivo `metrics/results.json` consolida:
- **Tasa de Éxito Funcional:** Porcentaje de requests procesadas correctamente (incluyendo rechazos esperados y escalamientos).
- **Errores Reales:** Conteo de fallos técnicos del sistema.
- **Tasa de Escalamiento:** Porcentaje de casos que requirieron intervención humana.
- **Latencia:** Milisegundos por ejecución de agente.
- **Tokens (Simulado):** Conteo base para evaluar costos.
