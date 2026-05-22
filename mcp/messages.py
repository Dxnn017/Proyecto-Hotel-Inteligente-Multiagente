"""
Módulo de Mensajes de MCP (Model Context Protocol).

Define las estructuras de datos y funciones auxiliares para construir
mensajes con formato JSON-RPC 2.0, el estándar oficial de comunicación en MCP.
"""

import uuid
from typing import Any, Dict, Optional


class MCPError:
    """Códigos de error estándar de JSON-RPC 2.0 y MCP."""
    
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # Errores específicos del Hotel Inteligente
    VALIDATION_ERROR = -32001
    CONFLIC_ERROR = -32002
    AGENT_EXECUTION_ERROR = -32003


def make_request(method: str, params: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Crea una solicitud formateada en JSON-RPC 2.0.
    
    Args:
        method: Nombre de la herramienta o método MCP a llamar (ej: 'tools/call').
        params: Parámetros del método.
        request_id: Identificador único de la petición. Si no se provee, se autogenera.
        
    Returns:
        Diccionario con la estructura JSON-RPC 2.0 de solicitud.
    """
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id or f"req-{uuid.uuid4().hex[:8]}"
    }


def make_response(result: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Crea una respuesta de éxito en JSON-RPC 2.0.
    
    Args:
        result: El resultado de la ejecución.
        request_id: Identificador único de la petición original.
        
    Returns:
        Diccionario con la estructura JSON-RPC 2.0 de respuesta.
    """
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    }


def make_error(code: int, message: str, data: Optional[Any] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Crea una respuesta de error en JSON-RPC 2.0.
    
    Args:
        code: Código de error numérico.
        message: Explicación del error.
        data: Datos adicionales del error (opcional).
        request_id: Identificador único de la petición original.
        
    Returns:
        Diccionario con la estructura JSON-RPC 2.0 de error.
    """
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": code,
            "message": message,
            "data": data or {}
        },
        "id": request_id
    }
