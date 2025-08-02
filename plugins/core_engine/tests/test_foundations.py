# plugins/core_engine/tests/test_foundations.py

import pytest

# 从平台核心导入
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.dependency_parser import build_dependency_graph_async

@pytest.mark.asyncio
class TestDependencyParser:
    """测试依赖解析器，它是引擎的基础功能。"""

    # Migrated from test_01_foundations.py
    async def test_simple_dependency(self, hook_manager: HookManager):
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"runtime": "test", "config": {"value": "{{ nodes.A.output }}"}}]}]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["B"] == {"A"}

    # Migrated from test_01_foundations.py
    async def test_explicit_dependency_with_depends_on(self, hook_manager: HookManager):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ world.some_var }}"}}]}
        ]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["B"] == {"A"}
        
    # Migrated from test_01_foundations.py
    async def test_combined_dependencies(self, hook_manager: HookManager):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "run": []},
            {"id": "C", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ nodes.B.output }}"}}]}
        ]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["C"] == {"A", "B"}