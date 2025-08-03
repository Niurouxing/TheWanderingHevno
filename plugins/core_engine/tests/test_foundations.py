# plugins/core_engine/tests/test_foundations.py
import pytest
from uuid import uuid4

# --- 修改 imports ---
# 从平台核心导入
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.contracts import StateSnapshot
from plugins.core_engine.dependency_parser import build_dependency_graph_async
from plugins.core_engine.models import GraphCollection, GenericNode
from plugins.core_engine.registry import RuntimeRegistry # <-- 新增导入
from plugins.core_engine.runtimes.io_runtimes import InputRuntime # <-- 新增导入, 用于注册一个真实的运行时


@pytest.mark.asyncio
class TestDependencyParser:
    """测试依赖解析器。"""

    # --- 新增一个 fixture 来提供 RuntimeRegistry ---
    @pytest.fixture
    def runtime_registry(self) -> RuntimeRegistry:
        """
        创建一个包含一个名为 'test' 的简单运行时的注册表。
        这样我们的测试用例就能正确解析了。
        """
        registry = RuntimeRegistry()
        # 注册一个真实的运行时类，这样 get_runtime_class 才能工作
        registry.register("test", InputRuntime)
        return registry

    # --- 修改所有测试用例的签名和调用 ---

    async def test_simple_dependency(self, runtime_registry: RuntimeRegistry):
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"runtime": "test", "config": {"value": "{{ nodes.A.output }}"}}]}]
        
        # 将 runtime_registry 传递给函数
        deps = await build_dependency_graph_async(nodes, runtime_registry)
        
        assert deps["B"] == {"A"}
        assert deps.get("A", set()) == set()

    async def test_explicit_dependency_with_depends_on(self, runtime_registry: RuntimeRegistry):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ world.some_var }}"}}]}
        ]
        
        deps = await build_dependency_graph_async(nodes, runtime_registry)
        
        assert deps["B"] == {"A"}
        
    async def test_combined_dependencies(self, runtime_registry: RuntimeRegistry):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "run": []},
            {"id": "C", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ nodes.B.output }}"}}]}
        ]
        
        deps = await build_dependency_graph_async(nodes, runtime_registry)
        
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