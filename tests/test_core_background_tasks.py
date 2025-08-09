# tests/test_core_background_tasks.py (已修复)

import pytest
import asyncio
from uuid import uuid4, UUID
from typing import Tuple

from backend.core.contracts import (
    HookManager,
    BackgroundTaskManager as BackgroundTaskManagerInterface,
    Container as ContainerInterface 
)

from plugins.core_engine.contracts import (
    StateSnapshot,
    SnapshotStoreInterface,
    GraphCollection,
    ExecutionEngineInterface,
    Sandbox # <--- 导入 Sandbox
)

from backend.container import Container
from plugins.core_engine.engine import ExecutionEngine

# pytest 标记
pytestmark = pytest.mark.asyncio


class TestBackgroundTaskManager:
    """对 BackgroundTaskManager 核心机制的单元测试。"""

    async def test_submit_and_execute_task(self):
        # ... (这个测试类保持不变，因为它不依赖 fixture) ...
        task_completed_event = asyncio.Event()
        result_capture = []
    
        async def mock_task(container: ContainerInterface, a: int, b: int):
            result_capture.append(a + b)
            task_completed_event.set()
    
        container = Container()
        from backend.core.tasks import BackgroundTaskManager
        task_manager = BackgroundTaskManager(container)
        task_manager.start()

        task_manager.submit_task(mock_task, 5, 10)

        await asyncio.wait_for(task_completed_event.wait(), timeout=1.0)
        
        assert len(result_capture) == 1
        assert result_capture[0] == 15

        await task_manager.stop()


class TestBackgroundTaskIntegration:
    """【已重构】集成测试，验证从引擎事件到后台任务执行的完整流程。"""
    
    @pytest.fixture
    def test_components(self, test_engine_setup: Tuple[ExecutionEngineInterface, ContainerInterface, HookManager]):
        """
        辅助 fixture，依赖于正确的 `test_engine_setup` fixture。
        """
        return test_engine_setup

    async def test_engine_step_triggers_background_task(
        self,
        test_components: Tuple[ExecutionEngineInterface, ContainerInterface, HookManager],
        sandbox_factory: callable, # <--- 使用新的 sandbox_factory
        linear_collection: GraphCollection
    ):
        """
        【已重构】测试：执行一次引擎 step 是否能通过钩子触发一个后台任务。
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
            # 钩子现在在一个新快照被提交后触发
            # 快照是 StateSnapshot(frozen=True)，所以 snapshot.id 是安全的
            task_manager.submit_task(mock_summary_task, snapshot.id)

        # 注册钩子实现
        hook_manager.add_implementation(
            "snapshot_committed",
            mock_snapshot_committed_hook,
            plugin_name="<test>"
        )

        # 1. Arrange: 使用 sandbox_factory 创建测试环境
        sandbox = sandbox_factory(
            graph_collection=linear_collection,
            initial_moment={"message": "start"}
        )
        initial_snapshot_id = sandbox.head_snapshot_id

        # 2. Act: 执行一步
        # engine.step 现在接收并返回 Sandbox 对象
        updated_sandbox = await engine.step(sandbox, {"user_input": "continue"})
        
        new_snapshot_id = updated_sandbox.head_snapshot_id

        # 3. Assert: 验证引擎执行和后台任务
        assert new_snapshot_id is not None
        assert new_snapshot_id != initial_snapshot_id

        # 等待后台任务完成
        await asyncio.wait_for(task_completed_event.wait(), timeout=2.0)

        assert len(result_capture) == 1
        assert result_capture[0]["id"] == new_snapshot_id
        assert result_capture[0]["parent_id"] == initial_snapshot_id

        # 4. 清理
        hook_manager._hooks.pop("snapshot_committed", None)