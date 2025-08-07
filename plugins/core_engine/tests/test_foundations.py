import pytest
from typing import Tuple

# --- 修改 imports ---
from backend.core.contracts import Container, HookManager
from plugins.core_engine.contracts import (
    GraphCollection,
    Sandbox,  # <--- 【新】导入 Sandbox
    ExecutionEngineInterface,
)
from plugins.core_engine.dependency_parser import build_dependency_graph_async
from plugins.core_engine.registry import RuntimeRegistry
from plugins.core_engine.runtimes.io_runtimes import InputRuntime


@pytest.mark.asyncio
class TestDependencyParser:
    """测试依赖解析器。"""

    @pytest.fixture
    def runtime_registry(self) -> RuntimeRegistry:
        """创建一个包含一个名为 'test' 的简单运行时的注册表。"""
        registry = RuntimeRegistry()
        registry.register("test", InputRuntime)
        return registry

    # --- 测试用例本身逻辑不变，但宏的内容可以更新以保持一致性 ---

    async def test_simple_dependency(self, runtime_registry: RuntimeRegistry):
        # 使用 `moment.` 作为示例，尽管对于解析器来说无所谓
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"runtime": "test", "config": {"value": "{{ nodes.A.output }}"}}]}]
        
        deps = await build_dependency_graph_async(nodes, runtime_registry)
        
        assert deps["B"] == {"A"}
        assert deps.get("A", set()) == set()

    async def test_explicit_dependency_with_depends_on(self, runtime_registry: RuntimeRegistry):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ moment.some_var }}"}}]}
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
    
    async def test_detects_cycle(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        cyclic_collection: GraphCollection
    ):
        """【已重构】测试引擎能否在执行前检测到图中的依赖环。"""
        engine, _, _ = test_engine_setup
        
        # Arrange: 使用工厂创建沙盒
        sandbox = sandbox_factory(graph_collection=cyclic_collection)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cycle detected"):
            await engine.step(sandbox, {})

    def test_invalid_graph_no_main_raises_error(self, invalid_graph_no_main: dict):
        """【保持不变】测试缺少 'main' 图的 GraphCollection 在模型验证时会失败。"""
        with pytest.raises(ValueError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate(invalid_graph_no_main)