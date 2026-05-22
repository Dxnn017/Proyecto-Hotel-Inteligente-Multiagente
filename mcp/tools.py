"""
Herramientas MCP (Model Context Protocol).

Define e integra los agentes del hotel inteligente como herramientas MCP,
permitiendo al Orquestador interactuar con ellos usando la API estándar de MCP.
"""

from typing import Dict, Any


def register_hotel_mcp_tools(protocol, orchestrator) -> None:
    """
    Registra cada uno de los subagentes especializados del hotel como herramientas MCP
    dentro del protocolo MCP provisto.
    
    Args:
        protocol: Instancia de MCPProtocol.
        orchestrator: Instancia de OrchestratorAgent.
    """
    
    # 1. Herramienta: Agente de Reservas
    if "reservation_agent" in orchestrator.agents:
        protocol.register_tool(
            name="reservation_agent",
            description=(
                "Gestiona consultas de disponibilidad, creación de nuevas reservas, "
                "modificaciones y cancelaciones de reservas en el sistema local."
            ),
            input_schema=orchestrator.schemas.get("reservation_agent", {}),
            handler=orchestrator.agents["reservation_agent"].process
        )
        
    # 2. Herramienta: Agente de Check-in
    if "checkin_agent" in orchestrator.agents:
        protocol.register_tool(
            name="checkin_agent",
            description=(
                "Realiza el check-in digital del huésped. Valida la identidad (DNI, pasaporte) "
                "e interactúa con el sistema de habitaciones para asignar una disponible."
            ),
            input_schema=orchestrator.schemas.get("checkin_agent", {}),
            handler=orchestrator.agents["checkin_agent"].process
        )
        
    # 3. Herramienta: Agente de Atención al Cliente
    if "customer_service_agent" in orchestrator.agents:
        protocol.register_tool(
            name="customer_service_agent",
            description=(
                "Atiende y resuelve solicitudes de servicio hechas por los huéspedes (como "
                "limpieza o mantenimiento). Decide si se auto-resuelve o si requiere escalamiento humano."
            ),
            input_schema=orchestrator.schemas.get("customer_service_agent", {}),
            handler=orchestrator.agents["customer_service_agent"].process
        )
        
    # 4. Herramienta: Agente de Facturación
    if "billing_agent" in orchestrator.agents:
        protocol.register_tool(
            name="billing_agent",
            description=(
                "Calcula consumos adicionales, aplica descuentos e impuestos, genera facturas y "
                "gestiona el folio/check-out financiero final de forma automática."
            ),
            input_schema=orchestrator.schemas.get("billing_agent", {}),
            handler=orchestrator.agents["billing_agent"].process
        )
        
    # 5. Herramienta: Agente de Feedback
    if "feedback_agent" in orchestrator.agents:
        protocol.register_tool(
            name="feedback_agent",
            description=(
                "Procesa comentarios de los huéspedes, calcula la calificación, detecta el "
                "sentimiento e inicia promociones de fidelización o alertas para casos insatisfechos."
            ),
            input_schema=orchestrator.schemas.get("feedback_agent", {}),
            handler=orchestrator.agents["feedback_agent"].process
        )
