# plugins/core_llm/utils.py
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def parse_provider_configs_from_env() -> Dict[str, Dict[str, Any]]:
    """从环境变量中解析所有自定义供应商的配置。"""
    configs = {}
    provider_ids_str = os.getenv("HEVNO_LLM_PROVIDERS", "")
    if not provider_ids_str:
        return configs
        
    provider_ids = [pid.strip() for pid in provider_ids_str.split(',') if pid.strip()]

    for pid in provider_ids:
        prefix = f"PROVIDER_{pid.upper()}_"
        mapping_str = os.getenv(f"{prefix}MODEL_MAPPING", "")
        model_mapping = {}
        if mapping_str:
            try:
                model_mapping = dict(
                    item.split(":", 1) for item in mapping_str.split(",") if ":" in item
                )
            except ValueError:
                logger.warning(f"Could not parse model_mapping for {pid}: {mapping_str}")

        configs[pid] = {
            "type": os.getenv(f"{prefix}TYPE"),
            "base_url": os.getenv(f"{prefix}BASE_URL"),
            "keys_env_var": os.getenv(f"{prefix}KEYS_ENV"),
            "model_mapping": model_mapping
        }
    return configs
