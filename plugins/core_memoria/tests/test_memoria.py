# plugins/core_memoria/tests/test_memoria.py

import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# 从平台核心契约导入
from backend.core.contracts import (
    Container, 
    BackgroundTaskManager,
    HookManager
)
# 从依赖插件 (core_engine) 的契约中导入
from plugins.core_engine.contracts import (
    Sandbox, 
    StateSnapshot, 
    GraphCollection, 
    ExecutionContext, 
    SharedContext, 
)
# 从本插件的组件导入
from plugins.core_memoria.runtimes import MemoriaAddRuntime, MemoriaQueryRuntime, MemoriaAggregateRuntime
from plugins.core_memoria.tasks import run_synthesis_task
# 从依赖插件 (core_llm) 的组件导入
from plugins.core_llm.models import LLMResponse, LLMResponseStatus, LLMError, LLMErrorType

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio



# --- Fixtures for creating mock contexts ---

@pytest.fixture
def mock_container() -> MagicMock:
    """
    A mock DI container.
    [FIX] Ensures that resolve() returns the *same* mock instance for a given service name on every call.
    """
    container = MagicMock(spec=Container)
    
    # Create the dictionary of mock services ONCE.
    mock_services = {
        "llm_service": AsyncMock(),
        "sandbox_store": MagicMock(spec=dict),
        "snapshot_store": MagicMock(),
        "task_manager": AsyncMock(spec=BackgroundTaskManager)
    }
    
    # The lambda now just performs a lookup in the stable, pre-existing dictionary.
    container.resolve.side_effect = lambda name: mock_services.get(name)
    
    return container

@pytest.fixture
def mock_shared_context(mock_container) -> SharedContext:
    """A mock shared context for execution."""
    shared = SharedContext(
        world_state={},
        session_info={},
        global_write_lock=asyncio.Lock(),
        services=MagicMock()
    )
    shared.services.task_manager = mock_container.resolve("task_manager")
    return shared

@pytest.fixture
def mock_exec_context(mock_shared_context) -> ExecutionContext:
    """A mock full execution context for runtimes."""
    sandbox_id = uuid.uuid4()
    graph_collection = GraphCollection.model_validate({"main": {"nodes": []}})
    snapshot = StateSnapshot(sandbox_id=sandbox_id, graph_collection=graph_collection)

    return ExecutionContext(
        shared=mock_shared_context,
        initial_snapshot=snapshot,
        hook_manager=AsyncMock(spec=HookManager) 
    )


# --- Test Cases ---

async def test_memoria_add_and_query(mock_exec_context):
    """
    Test Case 1: (Happy Path)
    Verify that adding a memory entry correctly updates the world state,
    and that a subsequent query can retrieve it.
    """
    # --- Arrange ---
    add_runtime = MemoriaAddRuntime()
    query_runtime = MemoriaQueryRuntime()
    
    add_config = {"stream": "events", "content": "The player entered the village."}
    
    # --- Act ---
    add_result = await add_runtime.execute(add_config, mock_exec_context)
    
    # --- Assert ---
    # 1. Assert add_runtime output
    assert "output" in add_result
    assert add_result["output"]["content"] == "The player entered the village."

    # 2. Assert world_state was modified
    world_state = mock_exec_context.shared.world_state
    assert "memoria" in world_state
    assert world_state["memoria"]["events"]["entries"][0]["content"] == "The player entered the village."

    # 3. Assert query_runtime can retrieve the data
    query_config = {"stream": "events"}
    query_result = await query_runtime.execute(query_config, mock_exec_context)
    
    assert "output" in query_result
    assert len(query_result["output"]) == 1
    assert query_result["output"][0]["content"] == "The player entered the village."


async def test_synthesis_task_trigger(mock_exec_context):
    """
    Test Case 2:
    Verify that the background synthesis task is triggered when the count is met.
    """
    # --- Arrange ---
    runtime = MemoriaAddRuntime()
    task_manager_mock = mock_exec_context.shared.services.task_manager

    # Configure world state for auto-synthesis
    mock_exec_context.shared.world_state["memoria"] = {
        "__global_sequence__": 0,
        "story": {
            "config": {
                "auto_synthesis": {
                    "enabled": True,
                    "trigger_count": 2, # Trigger after 2 entries
                }
            },
            "entries": [],
            "synthesis_trigger_counter": 0
        }
    }

    # --- Act & Assert ---
    # First call: should not trigger task
    await runtime.execute({"stream": "story", "content": "Event 1"}, mock_exec_context)
    task_manager_mock.submit_task.assert_not_called()
    assert mock_exec_context.shared.world_state["memoria"]["story"]["synthesis_trigger_counter"] == 1

    # Second call: should trigger task
    await runtime.execute({"stream": "story", "content": "Event 2"}, mock_exec_context)
    
    # Assert task was submitted
    task_manager_mock.submit_task.assert_called_once()
    
    call_args = task_manager_mock.submit_task.call_args
    assert call_args.args[0] == run_synthesis_task
    assert call_args.kwargs['sandbox_id'] == mock_exec_context.initial_snapshot.sandbox_id
    assert call_args.kwargs['stream_name'] == "story"
    assert isinstance(call_args.kwargs['synthesis_config'], dict)
    assert len(call_args.kwargs['entries_to_summarize_dicts']) == 2
    assert call_args.kwargs['entries_to_summarize_dicts'][0]["content"] == "Event 1"


async def test_run_synthesis_task_success(mock_container):
    """
    Test Case 3: (End-to-End for the task)
    Verify that the background task correctly calls the LLM,
    creates a new snapshot, and updates the sandbox head.
    """
    # --- Arrange ---
    # Setup mock services from the container
    llm_service_mock = mock_container.resolve("llm_service")
    sandbox_store_mock = mock_container.resolve("sandbox_store")
    snapshot_store_mock = mock_container.resolve("snapshot_store")

    # The mock for the 'request' method is now correctly configured on the stable 'llm_service_mock' instance.
    llm_service_mock.request = AsyncMock(
        return_value=LLMResponse(status=LLMResponseStatus.SUCCESS, content="A summary of events.")
    )

    # Setup initial state
    sandbox_id = uuid.uuid4()
    initial_snapshot_id = uuid.uuid4()
    
    initial_snapshot = StateSnapshot(
        id=initial_snapshot_id,
        sandbox_id=sandbox_id,
        graph_collection=GraphCollection.model_validate({"main": {"nodes": []}}),
        world_state={
            "memoria": {
                "__global_sequence__": 2,
                "journal": {
                    "config": {"auto_synthesis": {"enabled": True, "trigger_count": 2}},
                    "entries": [
                        {"id": uuid.uuid4(), "sequence_id": 1, "content": "Entry 1", "level": "event", "tags":[]},
                        {"id": uuid.uuid4(), "sequence_id": 2, "content": "Entry 2", "level": "event", "tags":[]},
                    ],
                    "synthesis_trigger_counter": 2 # Counter is high
                }
            }
        }
    )
    sandbox = Sandbox(id=sandbox_id, name="Test Sandbox", head_snapshot_id=initial_snapshot_id)

    # Populate stores
    snapshot_store_mock.get.return_value = initial_snapshot
    sandbox_store_mock.get.return_value = sandbox

    # Task arguments
    synthesis_config_dict = {"model": "gemini/gemini-pro", "level": "summary", "prompt": "{events_text}", "enabled": True, "trigger_count": 2}
    entries_to_summarize_dicts = initial_snapshot.world_state["memoria"]["journal"]["entries"]

    # --- Act ---
    await run_synthesis_task(
        mock_container,
        sandbox_id,
        "journal",
        synthesis_config_dict,
        entries_to_summarize_dicts
    )

    # --- Assert ---
    # 1. LLM was called correctly
    llm_service_mock.request.assert_awaited_once_with(
        model_name="gemini/gemini-pro",
        prompt="- Entry 1\n- Entry 2"
    )

    # 2. A new snapshot was saved
    snapshot_store_mock.save.assert_called_once()
    saved_snapshot: StateSnapshot = snapshot_store_mock.save.call_args[0][0]

    # 3. The new snapshot has the correct data
    assert saved_snapshot.id != initial_snapshot_id
    assert saved_snapshot.parent_snapshot_id == initial_snapshot_id
    
    # 4. The world state in the new snapshot contains the summary
    new_memoria = saved_snapshot.world_state["memoria"]
    assert len(new_memoria["journal"]["entries"]) == 3
    summary_entry = new_memoria["journal"]["entries"][-1]
    assert summary_entry["content"] == "A summary of events."
    assert summary_entry["level"] == "summary"
    assert summary_entry["sequence_id"] == 3

    # 5. The sandbox's head was updated to point to the new snapshot
    assert sandbox.head_snapshot_id == saved_snapshot.id


async def test_memoria_add_creates_stream_if_not_exists(mock_exec_context):
    """
    测试用例：`memoria.add` 边缘情况
    验证当向一个不存在的流中添加记忆时，该流会被自动创建。
    """
    # --- Arrange ---
    runtime = MemoriaAddRuntime()
    # 确保 world_state 为空，没有任何 memoria 数据
    mock_exec_context.shared.world_state = {}
    
    # --- Act ---
    await runtime.execute({"stream": "new_stream", "content": "First entry"}, mock_exec_context)
    
    # --- Assert ---
    world_state = mock_exec_context.shared.world_state
    assert "memoria" in world_state
    assert "new_stream" in world_state["memoria"]
    assert len(world_state["memoria"]["new_stream"]["entries"]) == 1
    assert world_state["memoria"]["new_stream"]["entries"][0]["content"] == "First entry"

async def test_memoria_query_with_filters_and_ordering(mock_exec_context):
    """
    测试用例：`memoria.query` 综合测试
    验证各种过滤和排序参数是否按预期工作。
    """
    # --- Arrange ---
    add_runtime = MemoriaAddRuntime()
    query_runtime = MemoriaQueryRuntime()

    # 填充一些测试数据
    await add_runtime.execute({"stream": "log", "content": "Event A", "level": "info"}, mock_exec_context)
    await add_runtime.execute({"stream": "log", "content": "Event B", "level": "info", "tags": ["combat"]}, mock_exec_context)
    await add_runtime.execute({"stream": "log", "content": "Event C", "level": "milestone", "tags": ["quest", "important"]}, mock_exec_context)
    await add_runtime.execute({"stream": "log", "content": "Event D", "level": "info", "tags": ["combat"]}, mock_exec_context)

    # --- Act & Assert ---
    # 1. 按 level 过滤
    result = await query_runtime.execute({"stream": "log", "levels": ["milestone"]}, mock_exec_context)
    assert len(result["output"]) == 1
    assert result["output"][0]["content"] == "Event C"

    # 2. 按 tag 过滤
    result = await query_runtime.execute({"stream": "log", "tags": ["combat"]}, mock_exec_context)
    assert len(result["output"]) == 2
    assert {e["content"] for e in result["output"]} == {"Event B", "Event D"}

    # 3. 按最新的 N 条过滤
    result = await query_runtime.execute({"stream": "log", "latest": 2}, mock_exec_context)
    assert len(result["output"]) == 2
    assert {e["content"] for e in result["output"]} == {"Event C", "Event D"}

    # 4. 按降序排序
    result = await query_runtime.execute({"stream": "log", "order": "descending"}, mock_exec_context)
    assert result["output"][0]["content"] == "Event D" # Event D 是最后添加的，sequence_id 最高
    assert result["output"][-1]["content"] == "Event A"
    
    # 5. 查询不存在的 tag，返回空列表
    result = await query_runtime.execute({"stream": "log", "tags": ["nonexistent"]}, mock_exec_context)
    assert result["output"] == []


async def test_memoria_aggregate_runtime(mock_exec_context):
    """
    测试用例：`memoria.aggregate` 运行时
    验证聚合功能，包括自定义模板和空列表处理。
    """
    # --- Arrange ---
    aggregate_runtime = MemoriaAggregateRuntime()
    entries_list = [
        {"level": "info", "content": "Hello"},
        {"level": "info", "content": "World"},
    ]
    
    # --- Act & Assert ---
    # 1. 默认模板
    result = await aggregate_runtime.execute({"entries": entries_list}, mock_exec_context)
    assert result["output"] == "Hello\n\nWorld"
    
    # 2. 自定义模板和连接符
    config = {
        "entries": entries_list,
        "template": "[{level}] {content}",
        "joiner": " | "
    }
    result = await aggregate_runtime.execute(config, mock_exec_context)
    assert result["output"] == "[info] Hello | [info] World"

    # 3. 空列表输入
    result = await aggregate_runtime.execute({"entries": []}, mock_exec_context)
    assert result["output"] == ""


async def test_run_synthesis_task_handles_llm_failure(mock_container):
    """
    测试用例：`run_synthesis_task` 失败路径
    验证当 LLM 调用失败时，任务会优雅地退出，不会创建新的快照。
    """
    # --- Arrange ---
    llm_service_mock = mock_container.resolve("llm_service")
    sandbox_store_mock = mock_container.resolve("sandbox_store")
    snapshot_store_mock = mock_container.resolve("snapshot_store")

    # 配置 LLM 服务返回一个错误响应
    llm_service_mock.request = AsyncMock(
        return_value=LLMResponse(
            status=LLMResponseStatus.ERROR,
            error_details=LLMError(
                error_type=LLMErrorType.PROVIDER_ERROR,
                message="Server is down",
                is_retryable=True
            )
        )
    )

    # 准备和成功案例中一样的初始状态
    sandbox_id = uuid.uuid4()
    initial_snapshot_id = uuid.uuid4()
    initial_snapshot = StateSnapshot(id=initial_snapshot_id, sandbox_id=sandbox_id, graph_collection=GraphCollection.model_validate({"main": {"nodes": []}}), world_state={"memoria": {}})
    sandbox = Sandbox(id=sandbox_id, name="Test Sandbox", head_snapshot_id=initial_snapshot_id)

    snapshot_store_mock.get.return_value = initial_snapshot
    sandbox_store_mock.get.return_value = sandbox

    # --- Act ---
    await run_synthesis_task(
        mock_container,
        sandbox_id,
        "journal",
        {}, # config
        []  # entries
    )

    # --- Assert ---
    # LLM 被调用了
    llm_service_mock.request.assert_awaited_once()
    # 关键：断言 `save` 方法从未被调用，因为流程在 LLM 失败后就退出了
    snapshot_store_mock.save.assert_not_called()
    # 关键：断言沙盒的头指针没有改变
    assert sandbox.head_snapshot_id == initial_snapshot_id