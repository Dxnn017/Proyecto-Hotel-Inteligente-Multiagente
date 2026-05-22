# Proceso Propuesto (TO-BE) con Agentes IA

## Descripción del proceso automatizado
El sistema multiagente implementa un flujo ininterrumpido (pipeline), transparente para el huésped. 

### Procesos por Etapa
1. **Reserva (Agente de Reservas):** El huésped chatea. El orquestador envía el JSON al Agente de Reservas. Se revisa la memoria compartida y se bloquea la habitación instantáneamente.
2. **Check-in (Agente de Check-in):** El huésped sube una foto de su DNI. El Agente valida con reglas estrictas, asocia la habitación reservada y emite una "llave digital".
3. **Estadía (Agente de Atención):** El huésped pide toallas. El agente clasifica la petición como rutinaria y notifica al personal (auto-resolución). Si reporta una gotera, lo escala como mantenimiento.
4. **Facturación (Agente de Facturación):** Todos los consumos (restaurante, minibar) se publican en el Event Bus. Al pedir check-out, el agente suma todo en segundos y confirma el pago.
5. **Feedback (Agente de Feedback):** Si el huésped se queja, el agente de feedback genera una alerta. Si es frecuente y elogia, le envía un código de descuento para su próxima visita de inmediato.

## Beneficios
- Orquestación en tiempo real.
- Cero filas.
- Comunicación estructurada JSON/MCP.
- Resolución de conflictos inmediata y transparente.
