# plugins/core_engine/tests/test_foundations.py

import pytest
from typing import Tuple

# --- 核心导入变更 ---
from backend.core.contracts import Container, HookManager
from plugins.core_engine.contracts import (
    GraphCollection,
    Sandbox, # 导入 Sandbox 模型，用于引擎执行测试
    ExecutionEngineInterface,
)
from plugins.core_engine.dependency_parser import build_dependency_graph_async
from plugins.core_engine.registry import RuntimeRegistry
from plugins.core_engine.runtimes.io_runtimes import InputRuntime

# 标记此文件中的所有测试都是异步的
pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
class TestDependencyParser:
    """
    【单元测试】
    测试依赖解析器 (`dependency_parser`) 的功能。
    这部分测试不执行引擎，只验证从图定义中静态提取依赖关系的能力。
    """

    @pytest.fixture
    def runtime_registry(self) -> RuntimeRegistry:
        """为依赖解析器提供一个简单的运行时注册表。"""
        registry = RuntimeRegistry()
        # 注册一个简单的运行时，以便解析器可以查找其依赖配置
        registry.register("test", InputRuntime)
        return registry

    async def test_simple_dependency_inference(self, runtime_registry: RuntimeRegistry):
        """测试：能否从宏 `{{ nodes.A.output }}` 中正确推断出对节点 A 的依赖。"""
        # 使用 `moment.` 作为示例，尽管对于解析器来说它只是普通文本，
        # 但这能保持与新规范的一致性。
        nodes = [
            {"id": "A", "run": []}, 
            {"id": "B", "run": [{"runtime": "test", "config": {"value": "{{ nodes.A.output }}"}}]}
        ]
        
        deps = await build_dependency_graph_async(nodes, runtime_registry)
        
        assert deps["B"] == {"A"}
        assert deps.get("A", set()) == set()

    async def test_explicit_dependency_with_depends_on(self, runtime_registry: RuntimeRegistry):
        """测试：`depends_on` 字段能否被正确解析为显式依赖。"""
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ moment.some_var }}"}}]}
        ]
        
        deps = await build_dependency_graph_async(nodes, runtime_registry)
        
        assert deps["B"] == {"A"}
        
    async def test_combined_implicit_and_explicit_dependencies(self, runtime_registry: RuntimeRegistry):
        """测试：能否正确合并来自宏推断和 `depends_on` 字段的依赖。"""
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "run": []},
            {"id": "C", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ nodes.B.output }}"}}]}
        ]
        
        deps = await build_dependency_graph_async(nodes, runtime_registry)
        
        assert deps["C"] == {"A", "B"}


@pytest.mark.asyncio
class TestEnginePreExecutionChecks:
    """
    【集成测试】
    测试引擎在执行前进行的验证，如循环检测和图结构校验。
    """
    
    async def test_engine_detects_dependency_cycle(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        cyclic_collection: GraphCollection
    ):
        """【已重构】测试引擎能否在执行前检测到图中的依赖环。"""
        engine, _, _ = test_engine_setup
        
        # Arrange: 使用工厂创建一个包含循环依赖图的沙盒。
        sandbox = await sandbox_factory(graph_collection=cyclic_collection)
        
        # Act & Assert: 断言调用 engine.step 会因为循环检测而抛出 ValueError。
        # 异常的检测点在 GraphRun 初始化阶段。
        with pytest.raises(ValueError, match="Cycle detected"):
            await engine.step(sandbox, {})

    async def test_graph_collection_validation_fails_without_main(self, invalid_graph_no_main: dict):
        """
        【模型单元测试】
        测试 GraphCollection Pydantic 模型本身的验证逻辑。
        缺少 'main' 图的字典在模型验证时就会失败。
        """
        with pytest.raises(ValueError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate(invalid_graph_no_main)