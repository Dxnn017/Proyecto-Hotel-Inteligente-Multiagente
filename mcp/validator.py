"""
Validador de Schemas para la Capa MCP.

Valida que las solicitudes cumplan con el protocolo JSON-RPC 2.0 y
que los payloads de los agentes coincidan con sus esquemas declarados.
"""

from typing import Any, Dict, Tuple
import jsonschema


# Esquema base para validar peticiones JSON-RPC 2.0 estándar
JSONRPC_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["jsonrpc", "method", "params", "id"],
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "method": {"type": "string", "minLength": 1},
        "params": {"type": "object"},
        "id": {"type": ["string", "number"]}
    }
}


class MCPValidator:
    """Validador central de MCP."""

    @staticmethod
    def validate_jsonrpc_request(request: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valida que un mensaje cumpla con la estructura JSON-RPC 2.0 de solicitud.
        
        Returns:
            Tuple[bool, str]: (Es válido, Mensaje de error si aplica)
        """
        try:
            jsonschema.validate(instance=request, schema=JSONRPC_REQUEST_SCHEMA)
            return True, ""
        except jsonschema.exceptions.ValidationError as e:
            return False, f"Estructura JSON-RPC 2.0 inválida: {e.message}"

    @staticmethod
    def validate_agent_payload(payload: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valida el payload de una solicitud específica contra el esquema de un agente.
        
        Args:
            payload: El diccionario del payload a validar.
            schema: El esquema JSON Schema de validación.
            
        Returns:
            Tuple[bool, str]: (Es válido, Mensaje de error si aplica)
        """
        try:
            jsonschema.validate(instance=payload, schema=schema)
            return True, ""
        except jsonschema.exceptions.ValidationError as e:
            return False, f"Error de validación contra esquema de agente: {e.message}"
