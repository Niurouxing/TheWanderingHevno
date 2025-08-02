# plugins/core_engine/tests/conftest.py

import pytest
import pytest_asyncio 
from typing import AsyncGenerator 

# 从平台核心导入
from backend.container import Container
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.engine import ExecutionEngine
from plugins.core_engine.registry import RuntimeRegistry
from plugins.core_engine.state import SnapshotStore
from plugins.core_engine.runtimes.base_runtimes import InputRuntime, SetWorldVariableRuntime
from plugins.core_engine.runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime

# 从其他插件导入，但我们只导入它们的注册函数
from plugins.core_llm import register_plugin as register_llm_plugin
from plugins.core_codex import register_plugin as register_codex_plugin

@pytest.fixture
def hook_manager() -> HookManager:
    """Provides a basic HookManager for unit tests."""
    return HookManager()