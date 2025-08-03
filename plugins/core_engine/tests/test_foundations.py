# plugins/core_engine/tests/test_foundations.py
import pytest
from uuid import uuid4

# 从平台核心导入
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.contracts import StateSnapshot
from plugins.core_engine.dependency_parser import build_dependency_graph_async
from plugins.core_engine.models import GraphCollection, GenericNode

@pytest.mark.asyncio
class TestDependencyParser:
    """测试依赖解析器。"""

    @pytest.fixture
    def hook_manager(self) -> HookManager:
        return HookManager()

    async def test_simple_dependency(self, hook_manager: HookManager):
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"runtime": "test", "config": {"value": "{{ nodes.A.output }}"}}]}]
        # 【修正】直接传递字典列表，而不是 GenericNode 对象列表
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["B"] == {"A"}

    async def test_explicit_dependency_with_depends_on(self, hook_manager: HookManager):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ world.some_var }}"}}]}
        ]
        # 【修正】直接传递字典列表
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["B"] == {"A"}
        
    async def test_combined_dependencies(self, hook_manager: HookManager):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "run": []},
            {"id": "C", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ nodes.B.output }}"}}]}
        ]
        # 【修正】直接传递字典列表
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["C"] == {"A", "B"}

@pytest.mark.asyncio
class TestEnginePreExecutionChecks:
    """测试引擎在执行前进行的验证。"""
    
    async def test_detects_cycle(self, test_engine, cyclic_collection):
        """测试引擎能否在执行前检测到图中的依赖环。"""
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        # 这里的调用是正确的，因为 engine.step 期望接收一个 StateSnapshot，
        # 而 StateSnapshot 内部的图定义就是 Pydantic 模型。
        # 错误只存在于直接调用 build_dependency_graph_async 的单元测试中。
        with pytest.raises(ValueError, match="Cycle detected"):
            await engine.step(initial_snapshot, {})

    async def test_invalid_graph_no_main_raises_error(self, invalid_graph_no_main):
        """测试缺少 'main' 图的 GraphCollection 在模型验证时会失败。"""
        with pytest.raises(ValueError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate(invalid_graph_no_main)