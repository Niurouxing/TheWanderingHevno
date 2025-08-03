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
from plugins.core_memoria import apply_pending_synthesis
# 从依赖插件 (core_llm) 的组件导入
from plugins.core_llm.models import LLMResponse, LLMResponseStatus, LLMError, LLMErrorType

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio



# --- Fixtures for creating mock contexts ---

@pytest.fixture
def mock_container() -> MagicMock:
    """
    A mock DI container.
    Ensures that resolve() returns the *same* mock instance for a given service name on every call.
    """
    container = MagicMock(spec=Container)
    
    # 【修改】添加 memoria_event_queue 的 mock
    mock_services = {
        "llm_service": AsyncMock(),
        "sandbox_store": MagicMock(spec=dict), # 不再需要
        "snapshot_store": MagicMock(),       # 不再需要
        "task_manager": AsyncMock(spec=BackgroundTaskManager),
        "memoria_event_queue": MagicMock(spec=dict) # 把它当成一个字典来 mock
    }
    
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


async def test_run_synthesis_task_submits_event_on_success(mock_container):
    """
    Test Case 3 (REWRITTEN & FIXED):
    Verify that the background task correctly calls the LLM and submits
    a 'memoria_synthesis_completed' event to its queue on success.
    """
    # --- Arrange ---
    # 1. Setup mock services from the container
    llm_service_mock = mock_container.resolve("llm_service")
    event_queue_mock = mock_container.resolve("memoria_event_queue")

    # 2. Configure mock responses and behavior
    llm_service_mock.request = AsyncMock(
        return_value=LLMResponse(status=LLMResponseStatus.SUCCESS, content="A summary of events.")
    )

    # 3. 【关键修复】明确配置 event_queue_mock 的行为
    #    为了模拟 `event_queue[sandbox_id].append(...)` 的完整流程，
    #    我们需要模拟字典的行为：
    #    a. 当检查 key 是否存在时，我们假装它不存在，以触发创建新列表的逻辑。
    #    b. 当通过 key 访问（__getitem__）时，返回一个我们能控制的真实列表。
    #    c. 当设置 key（__setitem__）时，让它正常工作。
    
    # 我们将要操作的真实列表
    actual_list_for_sandbox = []

    # 配置 MagicMock 以正确地模拟字典操作
    def getitem_side_effect(key):
        # 只有在请求我们指定的 sandbox_id 时，才返回我们准备的列表
        if key == sandbox_id:
            return actual_list_for_sandbox
        # 否则，返回一个新的 MagicMock，这是默认行为
        return MagicMock()

    event_queue_mock.__contains__.return_value = False
    event_queue_mock.__getitem__.side_effect = getitem_side_effect


    # 4. Setup task arguments
    sandbox_id = uuid.uuid4() # 必须在配置 side_effect 之后定义，因为它在 lambda 中被使用了
    synthesis_config_dict = {
        "model": "gemini/gemini-pro",
        "level": "summary",
        "prompt": "{events_text}",
        "enabled": True,
        "trigger_count": 2
    }
    entries_to_summarize_dicts = [
        {"content": "Entry 1"},
        {"content": "Entry 2"},
    ]

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

    # 2. An event was submitted to the queue
    
    # 2a. 验证 `event_queue[sandbox_id] = []` 这一行被调用过。
    event_queue_mock.__setitem__.assert_called_once_with(sandbox_id, [])

    # 2b. 【关键修复】现在我们直接检查我们自己创建的那个真实列表的内容，
    #     因为 `event_queue[sandbox_id].append(...)` 最终会操作到这个列表上。
    assert len(actual_list_for_sandbox) == 1
    
    submitted_event = actual_list_for_sandbox[0]
    assert submitted_event["type"] == "memoria_synthesis_completed"
    assert submitted_event["stream_name"] == "journal"
    assert submitted_event["content"] == "A summary of events."
    assert submitted_event["level"] == "summary"
    assert submitted_event["tags"] == ["synthesis", "auto-generated"]

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

async def test_apply_pending_synthesis_hook_updates_world_state(mock_exec_context):
    """
    Test Case 4: (Unit test for the hook implementation)
    Verify that the 'apply_pending_synthesis' hook function correctly
    processes events from its queue and modifies the world_state.
    """
    # --- Arrange ---
    # 1. Manually prepare the event queue and container mock within the context
    event_queue = {
        mock_exec_context.initial_snapshot.sandbox_id: [
            {
                "type": "memoria_synthesis_completed",
                "stream_name": "journal",
                "content": "This is a new summary.",
                "level": "reflection",
                "tags": ["auto"]
            }
        ]
    }
    
    # 2. Prepare the initial world state
    mock_exec_context.shared.world_state["memoria"] = {
        "__global_sequence__": 5,
        "journal": {
            "config": {},
            "entries": [],
            "synthesis_trigger_counter": 10 # Should be reset
        }
    }
    
    # 3. Setup the mock container inside the context to resolve the event queue
    #    这是关键，让钩子函数能找到队列
    mock_container = MagicMock(spec=Container)
    mock_container.resolve.return_value = event_queue
    # 我们可以通过这个后门将 mock container 注入到 context 中
    mock_exec_context.shared.services._container = mock_container

    # --- Act ---
    # 直接调用钩子函数，传入准备好的上下文
    await apply_pending_synthesis(mock_exec_context)

    # --- Assert ---
    # 1. The event should be removed from the queue
    assert not event_queue 

    # 2. The world state should be updated
    new_memoria = mock_exec_context.shared.world_state["memoria"]
    
    # 2a. Counter was reset
    assert new_memoria["journal"]["synthesis_trigger_counter"] == 0
    
    # 2b. A new entry was added
    assert len(new_memoria["journal"]["entries"]) == 1
    new_entry = new_memoria["journal"]["entries"][0]
    assert new_entry["content"] == "This is a new summary."
    assert new_entry["level"] == "reflection"
    assert new_entry["tags"] == ["auto"]
    
    # 2c. Global sequence was incremented
    assert new_memoria["__global_sequence__"] == 6