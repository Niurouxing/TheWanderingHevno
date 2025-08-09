# plugins/core_memoria/tests/test_memoria.py (已修复)

import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

# 从平台核心契约导入
from backend.core.contracts import Container, BackgroundTaskManager, HookManager
# 从依赖插件 (core_engine) 的契约中导入
from plugins.core_engine.contracts import Sandbox, ExecutionEngineInterface, StateSnapshot
# 从本插件的组件导入
from plugins.core_memoria.tasks import run_synthesis_task
# 从依赖插件 (core_llm) 的组件导入
from plugins.core_llm.contracts import LLMResponse, LLMResponseStatus, LLMError, LLMErrorType
from typing import Tuple # 导入 Tuple

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


# --- 集成测试 (Integration Tests) ---

async def test_memoria_add_and_query(
    memoria_test_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    memoria_sandbox_factory: callable
):
    """
    集成测试：验证 memoria.add 和 memoria.query 在引擎中的端到端行为。
    """
    # 为 container 和 hook_manager 使用有意义的变量名
    engine, container, _ = memoria_test_setup

    # Arrange: 创建一个沙盒，并定义一个使用 memoria 运行时的图
    sandbox = memoria_sandbox_factory(
        graph_collection_dict={
            "main": {
                "nodes": [
                    {"id": "add_memory", "run": [{"runtime": "memoria.add", "config": {"stream": "events", "content": "The player entered the village."}}]},
                    {"id": "query_memory", "depends_on": ["add_memory"], "run": [{"runtime": "memoria.query", "config": {"stream": "events", "latest": 1}}]}
                ]
            }
        }
    )

    # Act: 执行一步
    final_sandbox = await engine.step(sandbox, {})

    # Assert: 检查最终快照的 moment 和 run_output
    # 现在使用正确的 'container' 变量来解析服务
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)

    # 1. 检查 moment 状态
    moment = final_snapshot.moment
    assert "memoria" in moment
    assert "events" in moment["memoria"]
    assert len(moment["memoria"]["events"]["entries"]) == 1
    assert moment["memoria"]["events"]["entries"][0]["content"] == "The player entered the village."

    # 2. 检查节点输出
    run_output = final_snapshot.run_output
    query_output = run_output["query_memory"]["output"]
    assert len(query_output) == 1
    assert query_output[0]["content"] == "The player entered the village."


async def test_synthesis_task_trigger_and_application(
    memoria_test_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    memoria_sandbox_factory: callable
):
    """
    集成测试：验证自动综合任务的完整流程。
    """
    # 为 container 使用有意义的变量名
    engine, container, _ = memoria_test_setup

    # Arrange
    # 1. Mock LLM service to return a predictable summary
    llm_service_mock = container.resolve("llm_service")
    llm_service_mock.request = AsyncMock(
        return_value=LLMResponse(status=LLMResponseStatus.SUCCESS, content="A grand adventure began.")
    )

    # 2. 创建一个沙盒，其 lore 中包含触发综合的配置
    sandbox = memoria_sandbox_factory(
        graph_collection_dict={
            "main": {"nodes": [{"id": "add_mem", "run": [{"runtime": "memoria.add", "config": {"stream": "story", "content": "Event {{ moment.counter }}"}}]}]},
            "second_step": {"nodes": [{"id": "noop", "run": [{"runtime": "system.io.log", "config": {"message": "second step"}}]}]}
        },
        initial_moment={
            "memoria": {
                "__global_sequence__": 0,
                "story": {
                    "config": {
                        "auto_synthesis": {"enabled": True, "trigger_count": 2}
                    },
                    "entries": [],
                }
            },
            "counter": 0
        }
    )
    
    # Act: 连续执行两次，第二次应该会触发综合
    sandbox.lore['graphs']['main']['nodes'][0]['run'][0]['config']['content'] = "Event 1"
    sandbox = await engine.step(sandbox, {})
    
    sandbox.lore['graphs']['main']['nodes'][0]['run'][0]['config']['content'] = "Event 2"
    sandbox = await engine.step(sandbox, {})
    
    # Assert (after step 2): 任务已被提交
    task_manager: BackgroundTaskManager = container.resolve("task_manager")
    # 等待后台任务执行完成
    await asyncio.sleep(0.1)
    llm_service_mock.request.assert_awaited_once()

    # Act (step 3): 执行一个空操作，触发 `before_graph_execution` 钩子
    sandbox.lore['graphs'] = {"main": {"nodes": [{"id": "noop", "run": []}]}}
    final_sandbox = await engine.step(sandbox, {})
    
    # Assert (after step 3): 总结已被应用
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    moment = final_snapshot.moment
    
    story_stream = moment["memoria"]["story"]
    assert len(story_stream["entries"]) == 3 # 2 events + 1 summary
    summary_entry = story_stream["entries"][-1]
    assert summary_entry["content"] == "A grand adventure began."
    assert summary_entry["level"] == "summary"
    assert story_stream["synthesis_trigger_counter"] == 0

# ... (单元测试部分保持不变，因为它不使用 memoria_test_setup) ...
async def test_run_synthesis_task_unit_test():
    """单元测试：验证 `run_synthesis_task` 纯函数的逻辑。"""
    # Arrange
    mock_container = MagicMock(spec=Container)
    llm_service_mock = AsyncMock()
    llm_service_mock.request.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="A summary.")
    
    # 模拟 `memoria_event_queue` 字典
    event_queue = {}
    
    mock_container.resolve.side_effect = lambda name: {
        "llm_service": llm_service_mock,
        "memoria_event_queue": event_queue
    }.get(name)

    sandbox_id = uuid.uuid4()
    
    # Act
    await run_synthesis_task(
        mock_container,
        sandbox_id=sandbox_id,
        stream_name="journal",
        synthesis_config={"model": "test", "prompt": "{events_text}", "level": "summary"},
        entries_to_summarize_dicts=[{"content": "e1"}]
    )

    # Assert
    llm_service_mock.request.assert_awaited_once_with(model_name="test", prompt="- e1")
    assert sandbox_id in event_queue
    assert len(event_queue[sandbox_id]) == 1
    event = event_queue[sandbox_id][0]
    assert event["type"] == "memoria_synthesis_completed"
    assert event["content"] == "A summary."