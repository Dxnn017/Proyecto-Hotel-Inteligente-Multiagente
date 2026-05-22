"""
Protocolo de Comunicación MCP (Model Context Protocol).

Implementa la máquina de estados y ruteador de MCP, permitiendo registrar herramientas
(los subagentes y sus acciones) y gestionar el ciclo de peticiones y respuestas JSON-RPC 2.0.
"""

from typing import Any, Callable, Dict, List
from mcp.messages import make_error, make_response, MCPError
from mcp.validator import MCPValidator


class MCPProtocol:
    """
    Protocolo MCP para el Hotel Inteligente.
    Actúa como servidor MCP interno para enrutar llamadas y documentar herramientas.
    """

    def __init__(self):
        # Almacena herramientas en el formato oficial de MCP:
        # { name: { "name": name, "description": desc, "inputSchema": schema, "handler": handler } }
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """
        Registra una herramienta MCP en el protocolo.
        
        Args:
            name: Nombre único de la herramienta (ej: 'reservation_agent').
            description: Descripción de lo que hace.
            input_schema: JSON Schema que define los parámetros esperados.
            handler: Función ejecutable que procesa la petición.
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """Retorna el listado oficial de herramientas registradas."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"]
            }
            for t in self._tools.values()
        ]

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Punto de entrada para procesar solicitudes MCP.
        Recibe una solicitud JSON-RPC 2.0, valida su estructura, ejecuta el método y devuelve la respuesta.
        
        Args:
            request: Diccionario con la estructura de solicitud JSON-RPC 2.0.
            
        Returns:
            Respuesta JSON-RPC 2.0 de éxito o error.
        """
        # 1. Validar formato JSON-RPC 2.0
        is_valid, err_msg = MCPValidator.validate_jsonrpc_request(request)
        if not is_valid:
            return make_error(MCPError.INVALID_REQUEST, err_msg)

        req_id = request["id"]
        method = request["method"]
        params = request.get("params", {})

        # 2. Ruteo de métodos estándar de MCP
        if method == "tools/list":
            return make_response({"tools": self.list_tools()}, req_id)

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return make_error(MCPError.INVALID_PARAMS, "El parámetro 'name' es requerido para 'tools/call'", request_id=req_id)

            if tool_name not in self._tools:
                return make_error(MCPError.METHOD_NOT_FOUND, f"La herramienta '{tool_name}' no existe en el registro MCP", request_id=req_id)

            tool = self._tools[tool_name]
            
            # 3. Validar payload/arguments contra el JSON Schema de la herramienta
            is_payload_valid, payload_err = MCPValidator.validate_agent_payload(arguments, tool["inputSchema"])
            if not is_payload_valid:
                return make_response({
                    "status": "failed",
                    "error": f"Error de validación JSON: {payload_err}",
                    "response_message": f"Error de validación JSON: {payload_err}"
                }, req_id)

            # 4. Ejecutar el handler correspondiente (llamar al subagente)
            try:
                result = tool["handler"](arguments)
                return make_response(result, req_id)
            except Exception as e:
                return make_error(
                    MCPError.AGENT_EXECUTION_ERROR,
                    f"Error de ejecución en la herramienta '{tool_name}': {str(e)}",
                    request_id=req_id
                )

        else:
            return make_error(MCPError.METHOD_NOT_FOUND, f"Método MCP '{method}' no soportado", request_id=req_id)
