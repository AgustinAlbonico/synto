"""
Sistema de resolución de modelos por agente.
Lee config/models.yaml y asigna el modelo correcto a cada agente.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional

BASE_DIR = Path(__file__).parent.parent
MODELS_CONFIG_PATH = BASE_DIR / "config" / "models.yaml"

# Proveedor activo (del .env o default)
PROVIDER = os.getenv("MODEL_PROVIDER", "openrouter").lower()

# Alias de modelos (fallback si no hay config)
DEFAULT_PROFILES = {
    "premium": {
        "openrouter": "openrouter/anthropic/claude-sonnet-4",
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
    },
    "balanced": {
        "openrouter": "openrouter/google/gemini-2.0-flash-thinking-exp:free",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-haiku-3-20240307",
    },
    "economy": {
        "openrouter": "openrouter/meta-llama/llama-3.2-3b-instruct:free",
        "openai": "gpt-3.5-turbo",
        "anthropic": "claude-haiku-3-20240307",
    },
}


def _load_models_config() -> Dict:
    """Carga config/models.yaml."""
    if not MODELS_CONFIG_PATH.exists():
        return {}
    with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_model(agent_name: str) -> str:
    """
    Resuelve el modelo para un agente específico.
    
    Orden de resolución:
    1. Buscar en config/models.yaml el agente específico
    2. Si es un alias (premium/balanced/economy), resolver al modelo del proveedor
    3. Si no está, usar balanced como default
    
    Args:
        agent_name: Nombre del agente (ej: "HermesOrchestrator")
    
    Returns:
        ID del modelo para el proveedor activo
    """
    config = _load_models_config()
    
    # Buscar agente específico
    profile = config.get(agent_name)
    
    if profile is None:
        # Si no está definido, usar balanced por defecto
        profile = "balanced"
    
    if isinstance(profile, str):
        # Es un alias (premium/balanced/economy)
        profile = profile.lower()
        if profile in config and isinstance(config[profile], dict):
            # El profile está definido en el YAML con modelos por proveedor
            models_by_provider = config[profile]
        else:
            # Usar defaults
            models_by_provider = DEFAULT_PROFILES.get(profile, DEFAULT_PROFILES["balanced"])
        
        # Devolver modelo del proveedor activo
        model = models_by_provider.get(PROVIDER)
        if model is None:
            # Fallback a openrouter si el proveedor no tiene modelo definido
            model = models_by_provider.get("openrouter", DEFAULT_PROFILES["balanced"]["openrouter"])
        return model
    
    elif isinstance(profile, dict):
        # Es un diccionario con modelos por proveedor
        model = profile.get(PROVIDER)
        if model is None:
            model = profile.get("openrouter", DEFAULT_PROFILES["balanced"]["openrouter"])
        return model
    
    # Fallback total
    return DEFAULT_PROFILES["balanced"][PROVIDER]


def get_agent_config(agent_name: str) -> Dict:
    """
    Devuelve la config completa de un agente.
    
    Returns:
        Dict con: model, provider, temperature, etc.
    """
    model = resolve_model(agent_name)
    return {
        "model": model,
        "provider": PROVIDER,
    }


def list_all_assignments() -> Dict[str, str]:
    """
    Lista todos los agentes y sus modelos resueltos.
    Útil para debugging.
    """
    config = _load_models_config()
    agents = {}
    
    # Solo los que son agentes (no profiles)
    for key, value in config.items():
        if key not in ("premium", "balanced", "economy"):
            agents[key] = resolve_model(key)
    
    return agents


def reload_config():
    """Recarga la configuración desde disco."""
    global _config_cache
    _config_cache = None


# Cache
_config_cache = None
