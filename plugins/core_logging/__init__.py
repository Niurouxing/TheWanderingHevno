# plugins/core_logging/__init__.py
import os
import yaml
import logging
import logging.config
from pathlib import Path

from backend.core.contracts import Container, HookManager

PLUGIN_DIR = Path(__file__).parent

def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-logging 插件的注册入口。"""
    # 统一的入口消息
    print("--> 正在注册 [core-logging] 插件...")
    
    config_path = PLUGIN_DIR / "logging_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        logging_config = yaml.safe_load(f)
    
    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level and env_log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level_override = env_log_level.upper()
        logging_config['root']['level'] = log_level_override

    logging.config.dictConfig(logging_config)
    
    logger = logging.getLogger(__name__)
    
    # 统一的成功消息
    logger.info("插件 [core-logging] 注册成功。")