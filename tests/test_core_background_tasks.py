# tests/test_core_background_tasks.py

import pytest
import asyncio
from uuid import uuid4, UUID
from typing import Tuple

# --- 核心修改：修正导入路径 ---
# 从核心契约中导入接口和数据模型
from backend.core.contracts import (
    HookManager, StateSnapshot,
    BackgroundTaskManager as BackgroundTaskManagerInterface,
    SnapshotStoreInterface,
    GraphCollection,
    ExecutionEngineInterface,
    # 【修改】从契约中只导入抽象的 Container 接口，用于类型提示
    Container as ContainerInterface 
)
# 从具体实现位置导入具体的类
from backend.container import Container # 【新增】导入具体的 Container 实现
from plugins.core_engine.engine import ExecutionEngine
# ------------------------------------

# pytest 标记，表示此文件中的所有测试都是异步的
pytestmark = pytest.mark.asyncio


class TestBackgroundTaskManager:
    """
    对 BackgroundTaskManager 核心机制的单元测试。
    """

    async def test_submit_and_execute_task(self):
        """
        测试：能否成功提交并执行一个简单的后台任务。
        """
        task_completed_event = asyncio.Event()
        result_capture = []
    
        # 类型提示使用接口是好的实践
        async def mock_task(container: ContainerInterface, a: int, b: int):
            result_capture.append(a + b)
            task_completed_event.set()
    
        # 1. 准备
        # 【修正】直接实例化具体的 Container 实现类
        container = Container() 
        
        # 同样，直接从实现导入并实例化 BackgroundTaskManager
        from backend.core.tasks import BackgroundTaskManager
        task_manager = BackgroundTaskManager(container)
        task_manager.start()

        # 2. 执行
        task_manager.submit_task(mock_task, 5, 10)

        # 3.断言
        await asyncio.wait_for(task_completed_event.wait(), timeout=1.0)
        
        assert len(result_capture) == 1
        assert result_capture[0] == 15

        # 4. 清理
        await task_manager.stop()


class TestBackgroundTaskIntegration:
    """
    集成测试，验证从引擎事件到后台任务执行的完整流程。
    """
    
    @pytest.fixture
    def test_components(self, test_engine: Tuple[ExecutionEngineInterface, ContainerInterface, HookManager]):
        """
        一个辅助 fixture，用于解包由 test_engine 返回的元组。
        类型提示使用接口。
        """
        return test_engine

    async def test_engine_step_triggers_background_task(
        self,
        test_components: Tuple[ExecutionEngineInterface, ContainerInterface, HookManager],
        linear_collection: GraphCollection
    ):
        """
        测试：执行一次引擎 step 是否能通过钩子触发一个后台任务。
        """
        engine, container, hook_manager = test_components
        
        task_completed_event = asyncio.Event()
        result_capture = []

        async def mock_summary_task(container: ContainerInterface, snapshot_id: UUID):
            snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
            snapshot = snapshot_store.get(snapshot_id)
            
            result_capture.append({
                "id": snapshot.id,
                "parent_id": snapshot.parent_snapshot_id
            })
            task_completed_event.set()

        async def mock_snapshot_committed_hook(snapshot: StateSnapshot, container: ContainerInterface):
            task_manager: BackgroundTaskManagerInterface = container.resolve("task_manager")
            task_manager.submit_task(mock_summary_task, snapshot.id)

        hook_manager.add_implementation(
            "snapshot_committed",
            mock_snapshot_committed_hook,
            plugin_name="<test>"
        )

        sandbox_id = uuid4()
        initial_snapshot = StateSnapshot(
            sandbox_id=sandbox_id,
            graph_collection=linear_collection,
        )
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        snapshot_store.save(initial_snapshot)

        new_snapshot = await engine.step(initial_snapshot, {"user_input": "start"})

        assert new_snapshot is not None
        assert new_snapshot.parent_snapshot_id == initial_snapshot.id

        await asyncio.wait_for(task_completed_event.wait(), timeout=2.0)

        assert len(result_capture) == 1
        assert result_capture[0]["id"] == new_snapshot.id
        assert result_capture[0]["parent_id"] == initial_snapshot.id

        hook_manager._hooks.pop("snapshot_committed", None)