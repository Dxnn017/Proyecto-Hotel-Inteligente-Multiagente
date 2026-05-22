"""
Módulo de Métricas del Hotel Inteligente.

Registra métricas cuantitativas del sistema:
- Latencia por agente.
- Latencia total.
- Tasa de éxito / error.
- Uso simulado de tokens.
- Conflictos y escalaciones.
"""

import json
import os
from collections import defaultdict
from typing import Any

from config.settings import METRICS_FILE


class MetricsLogger:
    """Registra y persiste métricas de operación del sistema."""

    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency_sec": 0.0,
            "agent_latency_sec": defaultdict(float),
            "agent_calls": defaultdict(int),
            "estimated_token_usage": 0,
            "conflicts_detected": 0,
            "human_escalations": 0,
            "auto_resolved": 0
        }
        self._load_metrics()

    def _load_metrics(self):
        if os.path.exists(METRICS_FILE):
            try:
                with open(METRICS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if k in ["agent_latency_sec", "agent_calls"]:
                            for agent, val in v.items():
                                self.metrics[k][agent] = val
                        else:
                            self.metrics[k] = v
            except Exception:
                pass

    def save_metrics(self):
        """Guarda las métricas en results.json."""
        # Asegurar que la carpeta exista
        os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
        
        # Preparar para JSON
        to_save = {}
        for k, v in self.metrics.items():
            if isinstance(v, defaultdict):
                to_save[k] = dict(v)
            else:
                to_save[k] = v
                
        # Calcular derivadas
        if to_save["total_requests"] > 0:
            to_save["success_rate_percent"] = round((to_save["successful_requests"] / to_save["total_requests"]) * 100, 2)
            to_save["error_rate_percent"] = round((to_save["failed_requests"] / to_save["total_requests"]) * 100, 2)
            to_save["average_latency_sec"] = round(to_save["total_latency_sec"] / to_save["total_requests"], 3)
        else:
            to_save["success_rate_percent"] = 0.0
            to_save["error_rate_percent"] = 0.0
            to_save["average_latency_sec"] = 0.0

        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2, ensure_ascii=False)

    def log_latency(self, agent_id: str, latency_sec: float):
        self.metrics["agent_latency_sec"][agent_id] += latency_sec
        self.metrics["agent_calls"][agent_id] += 1
        self.metrics["total_latency_sec"] += latency_sec
        
    def log_success(self):
        self.metrics["total_requests"] += 1
        self.metrics["successful_requests"] += 1
        
    def log_error(self):
        self.metrics["total_requests"] += 1
        self.metrics["failed_requests"] += 1
        
    def log_tokens(self, tokens: int):
        self.metrics["estimated_token_usage"] += tokens
        
    def log_conflict(self):
        self.metrics["conflicts_detected"] += 1
        
    def log_escalation(self):
        self.metrics["human_escalations"] += 1
        
    def log_auto_resolve(self):
        self.metrics["auto_resolved"] += 1

    def print_summary(self):
        """Imprime un resumen de las métricas en consola."""
        total = self.metrics["total_requests"]
        if total == 0:
            print("\nNo hay métricas registradas.")
            return
            
        success_rate = (self.metrics["successful_requests"] / total) * 100
        avg_latency = self.metrics["total_latency_sec"] / total
        
        print("\n" + "="*50)
        print("📊 RESUMEN DE MÉTRICAS (Funcionales)")
        print("="*50)
        print(f"Escenarios Ejecutados: {total}")
        print(f"Éxito Funcional:       {success_rate:.1f}%")
        print(f"Errores Reales:        {self.metrics['failed_requests']}")
        print(f"Tasa Escalamiento:     {(self.metrics['human_escalations'] / total * 100):.1f}%")
        print(f"Latencia Promedio:     {avg_latency:.3f} s")
        print(f"Uso de Tokens (Est):   {self.metrics['estimated_token_usage']}")
        print(f"Conflictos Resueltos:  {self.metrics['conflicts_detected']}")
        print(f"Escalaciones a Humano: {self.metrics['human_escalations']}")
        print("="*50)
