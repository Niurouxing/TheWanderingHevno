# plugins/core_engine/tests/conftest.py

import pytest
from typing import Tuple

# --- 核心修复：从项目顶层的 conftest_data.py 中导入所有数据 Fixture ---
# 这样，此目录下的所有测试文件就都能找到它们了。
from tests.conftest_data import *

# --- 核心修复：从项目顶层的 conftest.py 中导入核心 Fixture ---
# 这样可以确保我们使用的是同一个应用实例和客户端设置。
from tests.conftest import (
    app,
    client,
    event_loop,
    sandbox_factory,
    sandbox_in_db,
    test_client,
    test_engine_setup
)
from .robot_fixture import Robot

@pytest.fixture(autouse=True)
def force_llm_debug_mode(monkeypatch):
    """
    在所有测试运行期间，自动设置环境变量，强制使用 MockLLMService。
    """
    monkeypatch.setenv("HEVNO_LLM_DEBUG_MODE", "true")

# --- 专属于 codex 测试的 Fixture ---
# 将这个 Fixture 从 test_codex_runtime.py 移动到这里，
# 因为 test_concurrency.py 也需要它。
@pytest.fixture
def codex_sandbox_factory(sandbox_factory: callable) -> callable:
    """
    一个便利的包装器，将通用的 sandbox_factory 和 codex 测试数据结合起来。
    """
    async def _create_codex_sandbox(codex_data: dict) -> 'Sandbox':
        from plugins.core_engine.contracts import GraphCollection

        # 从 codex_data 中分离出图、lore 和 moment
        graph_collection_dict = codex_data.get("lore", {}).get("graphs", {})
        initial_lore = codex_data.get("lore", {})
        initial_moment = codex_data.get("moment", {})
        
        # 从 lore 数据中移除 'graphs'，因为它会被自动添加
        if 'graphs' in initial_lore:
            del initial_lore['graphs']
            
        graph_collection_obj = GraphCollection.model_validate(graph_collection_dict)

        # 调用父工厂
        return await sandbox_factory(
            graph_collection=graph_collection_obj,
            initial_lore=initial_lore,
            initial_moment=initial_moment
        )
    return _create_codex_sandbox

@pytest.fixture(scope="session")
def custom_object_storage_collection() -> GraphCollection:
    """
    测试存储和使用自定义类实例 (Robot)。
    """
    # 这个宏创建 Robot 实例并将其存入 moment
    create_robot_code = """
# 必须先导入类，因为宏的执行环境是独立的
from plugins.core_engine.tests.robot_fixture import Robot
moment.robots = [Robot('R2-D2'), Robot('C-3PO')]
"""
    
    # 这个宏加载 Robot 实例并调用其方法
    use_robot_code = """
# 加载 R2-D2 实例
r2 = moment.robots[0]
# 调用它的方法
r2.take_damage(25)
# 返回一个可序列化的值
r2.hp
"""
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "create_robots", "run": [{"runtime": "system.execute", "config": {"code": create_robot_code}}]},
        {"id": "use_robot", "depends_on": ["create_robots"], "run": [{"runtime": "system.execute", "config": {"code": use_robot_code}}]},
    ]}})