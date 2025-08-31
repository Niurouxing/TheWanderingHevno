# plugins/core_engine/tests/test_skip_functionality.py

import pytest
from typing import Tuple

from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def skip_test_collections():
    """提供各种skip测试场景的GraphCollection集合"""
    
    # 测试简单的布尔值skip
    boolean_skip_collection = GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "should_skip", 
                    "skip": True,
                    "run": [{"runtime": "system.io.input", "config": {"value": "should not execute"}}]
                },
                {
                    "id": "should_run", 
                    "skip": False,
                    "run": [{"runtime": "system.io.input", "config": {"value": "should execute"}}]
                }
            ]
        }
    })
    
    # 测试宏表达式skip
    macro_skip_collection = GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "setup", 
                    "run": [{"runtime": "system.execute", "config": {"code": "moment.should_skip_next = True"}}]
                },
                {
                    "id": "conditional_skip", 
                    "depends_on": ["setup"],
                    "skip": "{{ moment.should_skip_next }}",
                    "run": [{"runtime": "system.io.input", "config": {"value": "should not execute"}}]
                },
                {
                    "id": "always_run",
                    "depends_on": ["setup"], 
                    "skip": "{{ not moment.should_skip_next }}",
                    "run": [{"runtime": "system.io.input", "config": {"value": "should execute"}}]
                }
            ]
        }
    })
    
    # 测试skip条件求值失败
    invalid_skip_collection = GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "invalid_skip", 
                    "skip": "{{ non_existent_variable }}",
                    "run": [{"runtime": "system.io.input", "config": {"value": "should not execute"}}]
                }
            ]
        }
    })
    
    # 测试依赖关系中的skip
    dependency_skip_collection = GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "A_normal", 
                    "run": [{"runtime": "system.io.input", "config": {"value": "A output"}}]
                },
                {
                    "id": "B_skipped", 
                    "depends_on": ["A_normal"],
                    "skip": True,
                    "run": [{"runtime": "system.io.input", "config": {"value": "B should not execute"}}]
                },
                {
                    "id": "C_dependent", 
                    "depends_on": ["B_skipped"],
                    "run": [{"runtime": "system.io.input", "config": {"value": "C runs after skipped B"}}]
                }
            ]
        }
    })
    
    return {
        "boolean_skip": boolean_skip_collection,
        "macro_skip": macro_skip_collection,
        "invalid_skip": invalid_skip_collection,
        "dependency_skip": dependency_skip_collection
    }


@pytest.mark.asyncio
class TestSkipFunctionality:
    
    async def test_boolean_skip_true(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        skip_test_collections: dict
    ):
        """测试当skip字段为True时，节点被跳过"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=skip_test_collections["boolean_skip"])
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        
        # 验证skip=True的节点返回空结果（被跳过）
        assert output["should_skip"] == {}
        
        # 验证skip=False的节点正常执行
        assert output["should_run"]["output"] == "should execute"
    
    async def test_boolean_skip_false(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable
    ):
        """测试当skip字段为False时，节点正常执行"""
        collection = GraphCollection.model_validate({
            "main": {
                "nodes": [
                    {
                        "id": "should_run", 
                        "skip": False,
                        "run": [{"runtime": "system.io.input", "config": {"value": "executed"}}]
                    }
                ]
            }
        })
        
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        assert output["should_run"]["output"] == "executed"
    
    async def test_macro_skip_evaluation(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        skip_test_collections: dict
    ):
        """测试skip字段中的宏表达式被正确求值"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=skip_test_collections["macro_skip"])
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        
        # setup节点正常执行
        assert "setup" in output
        
        # conditional_skip节点被跳过（因为moment.should_skip_next = True）
        assert output["conditional_skip"] == {}
        
        # always_run节点正常执行（因为not moment.should_skip_next = False）
        assert output["always_run"]["output"] == "should execute"
    
    async def test_invalid_skip_evaluation_fails_node(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        skip_test_collections: dict
    ):
        """测试skip条件求值失败时，节点执行失败"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=skip_test_collections["invalid_skip"])
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        
        # 验证节点因skip条件求值失败而失败
        assert "error" in output["invalid_skip"]
        assert "Failed to evaluate 'skip' condition" in output["invalid_skip"]["error"]
        assert output["invalid_skip"]["runtime"] == "engine.pre_check"
    
    async def test_skipped_node_allows_downstream_execution(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        skip_test_collections: dict
    ):
        """测试被跳过的节点不会阻断下游节点的执行"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=skip_test_collections["dependency_skip"])
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        
        # A节点正常执行
        assert output["A_normal"]["output"] == "A output"
        
        # B节点被跳过
        assert output["B_skipped"] == {}
        
        # C节点仍然能够执行（即使B被跳过）
        assert output["C_dependent"]["output"] == "C runs after skipped B"
    
    async def test_default_skip_behavior(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable
    ):
        """测试没有skip字段时的默认行为（不跳过）"""
        collection = GraphCollection.model_validate({
            "main": {
                "nodes": [
                    {
                        "id": "normal_node",
                        "run": [{"runtime": "system.io.input", "config": {"value": "normal execution"}}]
                    }
                ]
            }
        })
        
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        assert output["normal_node"]["output"] == "normal execution"