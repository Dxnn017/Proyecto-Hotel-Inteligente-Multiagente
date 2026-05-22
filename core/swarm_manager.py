"""
Swarm Manager del Hotel Inteligente.

Implementa Swarms para ejecutar tareas colaborativas entre agentes.
Un Swarm se activa cuando una solicitud del huésped requiere la
intervención coordinada de más de un agente.

Casos de uso:
1. checkout_y_feedback: Facturación + Feedback simultáneos.
2. cambio_habitacion_y_limpieza: Check-in + Atención al Cliente.
3. temporada_alta: Reservas + Check-in coordinados.
"""

import uuid
from datetime import datetime
from typing import Any


class SwarmTask:
    """Representa una tarea individual dentro de un Swarm."""

    def __init__(self, agent_id: str, task_type: str, payload: dict):
        self.task_id = f"ST-{uuid.uuid4().hex[:8]}"
        self.agent_id = agent_id
        self.task_type = task_type
        self.payload = payload
        self.status = "pending"
        self.result = None
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "status": self.status,
            "result": self.result,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class Swarm:
    """Representa un Swarm: un grupo de tareas colaborativas entre agentes."""

    def __init__(self, swarm_name: str, guest_id: str, description: str = ""):
        self.swarm_id = f"SW-{uuid.uuid4().hex[:8]}"
        self.swarm_name = swarm_name
        self.guest_id = guest_id
        self.description = description
        self.tasks: list[SwarmTask] = []
        self.status = "created"
        self.created_at = datetime.now().isoformat()
        self.completed_at = None
        self.results: list[dict] = []

    def add_task(self, agent_id: str, task_type: str, payload: dict) -> SwarmTask:
        """Añade una tarea al Swarm."""
        task = SwarmTask(agent_id, task_type, payload)
        self.tasks.append(task)
        return task

    def get_participating_agents(self) -> list[str]:
        """Retorna los agentes participantes."""
        return list(set(t.agent_id for t in self.tasks))

    def to_dict(self) -> dict[str, Any]:
        return {
            "swarm_id": self.swarm_id,
            "swarm_name": self.swarm_name,
            "guest_id": self.guest_id,
            "description": self.description,
            "status": self.status,
            "participating_agents": self.get_participating_agents(),
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "results": self.results,
        }


class SwarmManager:
    """
    Gestor de Swarms del sistema multiagente.

    Crea, ejecuta y coordina Swarms para tareas que requieren
    la colaboración de múltiples agentes.
    """

    def __init__(self, shared_memory, event_bus):
        """
        Inicializa el SwarmManager.

        Args:
            shared_memory: Instancia de SharedMemory.
            event_bus: Instancia de EventBus.
        """
        self.memory = shared_memory
        self.event_bus = event_bus
        self._swarms: list[Swarm] = []

    def create_swarm(
        self,
        swarm_name: str,
        guest_id: str,
        tasks: list[dict],
        description: str = "",
    ) -> Swarm:
        """
        Crea un nuevo Swarm con las tareas especificadas.

        Args:
            swarm_name: Nombre del swarm.
            guest_id: ID del huésped.
            tasks: Lista de tareas [{agent_id, task_type, payload}].
            description: Descripción del swarm.

        Returns:
            El Swarm creado.
        """
        swarm = Swarm(swarm_name, guest_id, description)

        for task_def in tasks:
            swarm.add_task(
                agent_id=task_def["agent_id"],
                task_type=task_def["task_type"],
                payload=task_def.get("payload", {}),
            )

        self._swarms.append(swarm)
        return swarm

    def execute_swarm(self, swarm: Swarm, agents: dict) -> dict[str, Any]:
        """
        Ejecuta un Swarm, delegando cada tarea al agente correspondiente.

        Args:
            swarm: El Swarm a ejecutar.
            agents: Diccionario {agent_id: instancia_agente}.

        Returns:
            Resultado consolidado del Swarm.
        """
        swarm.status = "executing"
        all_results = []

        for task in swarm.tasks:
            task.started_at = datetime.now().isoformat()
            task.status = "executing"

            agent = agents.get(task.agent_id)
            if agent:
                try:
                    result = agent.process(task.payload)
                    task.result = result
                    task.status = "completed"
                    all_results.append({
                        "task_id": task.task_id,
                        "agent_id": task.agent_id,
                        "status": "success",
                        "result": result,
                    })
                except Exception as e:
                    task.status = "failed"
                    task.result = {"error": str(e)}
                    all_results.append({
                        "task_id": task.task_id,
                        "agent_id": task.agent_id,
                        "status": "failed",
                        "error": str(e),
                    })
            else:
                task.status = "failed"
                task.result = {"error": f"Agente {task.agent_id} no encontrado"}
                all_results.append({
                    "task_id": task.task_id,
                    "agent_id": task.agent_id,
                    "status": "failed",
                    "error": f"Agente {task.agent_id} no encontrado",
                })

            task.completed_at = datetime.now().isoformat()

        # Determinar estado final del Swarm
        failed = [r for r in all_results if r["status"] == "failed"]
        swarm.status = "completed" if not failed else "partial_failure"
        swarm.completed_at = datetime.now().isoformat()
        swarm.results = all_results

        # Publicar evento del swarm
        self.event_bus.publish(
            event_type="swarm_ejecutado",
            agent_id="swarm_manager",
            guest_id=swarm.guest_id,
            data={
                "swarm_id": swarm.swarm_id,
                "swarm_name": swarm.swarm_name,
                "agents": swarm.get_participating_agents(),
                "tasks_total": len(swarm.tasks),
                "tasks_completed": len(all_results) - len(failed),
                "tasks_failed": len(failed),
                "status": swarm.status,
            },
        )

        return {
            "swarm_id": swarm.swarm_id,
            "swarm_name": swarm.swarm_name,
            "status": swarm.status,
            "participating_agents": swarm.get_participating_agents(),
            "results": all_results,
            "summary": {
                "total_tasks": len(swarm.tasks),
                "completed": len(all_results) - len(failed),
                "failed": len(failed),
            },
        }

    def get_swarm_history(self) -> list[dict[str, Any]]:
        """Retorna el historial de todos los Swarms ejecutados."""
        return [s.to_dict() for s in self._swarms]

    def get_swarm_count(self) -> int:
        """Retorna el número de Swarms ejecutados."""
        return len(self._swarms)

    def clear(self) -> None:
        """Limpia el historial de Swarms."""
        self._swarms.clear()
