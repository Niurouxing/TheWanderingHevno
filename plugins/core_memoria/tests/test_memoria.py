# plugins/core_memoria/tests/test_memoria.py

import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock
from typing import Tuple, cast

import pytest

# Core contracts
from backend.core.contracts import Container, BackgroundTaskManager, HookManager
from plugins.core_engine.contracts import Sandbox, ExecutionEngineInterface, StateSnapshot, GraphCollection
from plugins.core_llm.contracts import LLMResponse, LLMResponseStatus

# Plugin-specific components to test
from plugins.core_memoria.tasks import run_synthesis_task

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


# --- Integration Tests ---

async def test_memoria_add_and_query(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    sandbox_factory: callable
):
    """
    Tests the basic end-to-end functionality of adding and then querying a memory.
    """
    engine, container, _ = test_engine_setup

    # 直接使用通用的 sandbox_factory
    sandbox = await sandbox_factory(
        graph_collection=GraphCollection.model_validate({
            "main": {
                "nodes": [
                    {"id": "add", "run": [{"runtime": "memoria.add", "config": {"stream": "events", "content": "The player entered the village."}}]},
                    {"id": "query", "depends_on": ["add"], "run": [{"runtime": "memoria.query", "config": {"stream": "events", "latest": 1}}]}
                ]
            }
        })
    )

    final_sandbox = await engine.step(sandbox, {})
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None

    moment = final_snapshot.moment
    assert "memoria" in moment and "events" in moment["memoria"]
    assert len(moment["memoria"]["events"]["entries"]) == 1
    assert moment["memoria"]["events"]["entries"][0]["content"] == "The player entered the village."

    query_output = final_snapshot.run_output["query"]["output"]
    assert len(query_output) == 1
    assert query_output[0]["content"] == "The player entered the village."



async def test_complex_query_with_tags_and_levels(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    sandbox_factory: callable
):
    """
    Tests querying with multiple filters (tags and levels) to ensure correctness.
    """
    engine, container, _ = test_engine_setup

    # 直接使用通用的 sandbox_factory
    sandbox = await sandbox_factory(
        graph_collection=GraphCollection.model_validate({
            "main": {
                "nodes": [
                    {"id": "add1", "run": [{"runtime": "memoria.add", "config": {"stream": "all", "level": "event", "tags": ["combat"], "content": "A"}}]},
                    {"id": "add2", "run": [{"runtime": "memoria.add", "config": {"stream": "all", "level": "thought", "tags": ["player"], "content": "B"}}]},
                    {"id": "add3", "run": [{"runtime": "memoria.add", "config": {"stream": "all", "level": "event", "tags": ["social", "player"], "content": "C"}}]},
                    {"id": "query", "depends_on": ["add1", "add2", "add3"], "run": [{"runtime": "memoria.query", "config": {
                        "stream": "all",
                        "levels": ["event"],
                        "tags": ["player"] # 查询 level是event 且 tags包含player 的条目
                    }}]}
                ]
            }
        })
    )

    final_sandbox = await engine.step(sandbox, {})
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None
    
    query_output = final_snapshot.run_output["query"]["output"]
    assert len(query_output) == 1
    assert query_output[0]["content"] == "C" # 只有 C 同时满足两个条件

async def test_query_format_message_list(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    sandbox_factory: callable
):
    """
    Tests the new `format: "message_list"` option in memoria.query.
    It should correctly filter and transform entries into the LLM message format.
    """
    engine, container, _ = test_engine_setup

    sandbox = await sandbox_factory(
        graph_collection=GraphCollection.model_validate({
            "main": {
                "nodes": [
                    # Simulate a conversation history
                    {"id": "add_user1", "run": [{"runtime": "memoria.add", "config": {"stream": "chat", "level": "user", "content": "Hello, who are you?"}}]},
                    {"id": "add_model1", "depends_on": ["add_user1"], "run": [{"runtime": "memoria.add", "config": {"stream": "chat", "level": "model", "content": "I am an AI assistant."}}]},
                    # Add an event that should be filtered out
                    {"id": "add_event", "depends_on": ["add_model1"], "run": [{"runtime": "memoria.add", "config": {"stream": "chat", "level": "event", "content": "The system rebooted."}}]},
                    {"id": "add_user2", "depends_on": ["add_event"], "run": [{"runtime": "memoria.add", "config": {"stream": "chat", "level": "user", "content": "What can you do?"}}]},
                    # The actual query node to test
                    {"id": "query_messages", "depends_on": ["add_user2"], "run": [{"runtime": "memoria.query", "config": {
                        "stream": "chat",
                        "latest": 4, # Should get all 4 entries before format
                        "format": "message_list" # The feature under test
                    }}]}
                ]
            }
        })
    )

    final_sandbox = await engine.step(sandbox, {})
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None
    
    # Assert
    query_output = final_snapshot.run_output["query_messages"]["output"]
    
    # 1. The output should be a list of 3 messages, as the "event" level is filtered out.
    assert isinstance(query_output, list)
    assert len(query_output) == 3
    
    # 2. Check the content and structure of each message
    expected_messages = [
        {"role": "user", "content": "Hello, who are you?"},
        {"role": "model", "content": "I am an AI assistant."},
        {"role": "user", "content": "What can you do?"}
    ]
    
    # The 'latest' filter works on sequence_id, and the format filter is applied after.
    # So we get the last 4 entries, then filter to 3 messages.
    # The order is ascending by default.
    assert query_output[0] == expected_messages[0]
    assert query_output[1] == expected_messages[1]
    assert query_output[2] == expected_messages[2]

    # 3. Let's double check the number of entries in the moment state, it should be 4
    moment = final_snapshot.moment
    assert len(moment["memoria"]["chat"]["entries"]) == 4


async def test_synthesis_task_trigger_and_application(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    sandbox_factory: callable
):
    """
    Tests the full auto-synthesis flow: triggering a background task via
    memoria.add, and applying the result on a subsequent step.
    """
    engine, container, _ = test_engine_setup

    llm_service_mock = container.resolve("llm_service")
    llm_service_mock.request = AsyncMock(
        return_value=LLMResponse(status=LLMResponseStatus.SUCCESS, content="A grand adventure began.")
    )
    
    task_manager = cast(BackgroundTaskManager, container.resolve("task_manager"))
    queue = task_manager._queue

    # Arrange:
    #1. 定义一个能执行两次 memoria.add 的图。
    #2. 从一个完全干净的 initial_moment 开始。
    sandbox = await sandbox_factory(
        graph_collection=GraphCollection.model_validate({
            "main": {"nodes": [
                {"id": "add_1", "run": [{"runtime": "memoria.add", "config": {"stream": "story", "content": "Event 1"}}]},
                {"id": "add_2", "depends_on": ["add_1"], "run": [{"runtime": "memoria.add", "config": {"stream": "story", "content": "Event 2"}}]}
            ]}
        }),
        initial_moment={
            "memoria": {
                "__global_sequence__": 0,
                "story": {
                    "config": {"auto_synthesis": {"enabled": True, "trigger_count": 2}},
                    "entries": [],
                    "synthesis_trigger_counter": 0
                }
            }
        }
    )
    
    # Act 1: 一次性执行包含两次 add 的图。
    # 第一次 add: counter -> 1
    # 第二次 add: counter -> 2, 满足 trigger_count, 触发合成任务。
    sandbox = await engine.step(sandbox, {})
    assert not queue.empty(), "Synthesis task should have been submitted to the queue"
    
    # Manually execute the background task to simulate completion.
    task_func, args, kwargs = await queue.get()
    await task_func(container, *args, **kwargs)
    queue.task_done()
    llm_service_mock.request.assert_awaited_once()

    # Act 2: Run a no-op step. This will trigger the `before_graph_execution` hook,
    # which in turn calls `apply_pending_synthesis` to apply the completed summary.
    sandbox.lore['graphs'] = {"main": {"nodes": [{"id": "noop", "run": []}]}}
    final_sandbox = await engine.step(sandbox, {})
    
    # Assert: The summary has been correctly applied to the moment state.
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None
    
    moment = final_snapshot.moment
    story_stream = moment["memoria"]["story"]
    
    #期望的结果现在是正确的: 2个原始事件 + 1个总结 = 3个条目
    assert len(story_stream["entries"]) == 3
    
    original_entry_1 = story_stream["entries"][0]
    original_entry_2 = story_stream["entries"][1]
    summary_entry = story_stream["entries"][2]

    assert original_entry_1["content"] == "Event 1"
    assert original_entry_2["content"] == "Event 2"
    assert summary_entry["content"] == "A grand adventure began."
    assert summary_entry["level"] == "summary"
    assert story_stream["synthesis_trigger_counter"] == 0 # Counter should be reset after synthesis.

# --- Unit Test ---

async def test_run_synthesis_task_unit_test():
    """Unit test for the `run_synthesis_task` pure function logic."""
    mock_container = MagicMock(spec=Container)
    llm_service_mock = AsyncMock()
    llm_service_mock.request.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="A summary.")
    
    event_queue = {}
    
    mock_container.resolve.side_effect = lambda name: {
        "llm_service": llm_service_mock,
        "memoria_event_queue": event_queue
    }.get(name)

    sandbox_id = uuid.uuid4()
    
    await run_synthesis_task(
        mock_container,
        sandbox_id=sandbox_id,
        stream_name="journal",
        synthesis_config={"model": "test", "prompt": "{events_text}", "level": "summary"},
        entries_to_summarize_dicts=[{"content": "e1"}]
    )

    # FIX: The keyword argument for the model is `model_name`, not `model`.
    llm_service_mock.request.assert_awaited_once_with(model_name="test", prompt="- e1")
    assert sandbox_id in event_queue
    assert len(event_queue[sandbox_id]) == 1
    event = event_queue[sandbox_id][0]
    assert event["type"] == "memoria_synthesis_completed"
    assert event["content"] == "A summary."