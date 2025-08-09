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

@pytest.fixture
def memoria_sandbox_factory(sandbox_factory: callable) -> callable:
    """
    A convenience factory for memoria tests. It wraps the main sandbox_factory
    to simplify creating sandboxes with specific graph definitions and initial states.
    """
    async def _create(
        graph_collection_dict: dict,
        initial_lore: dict = None,
        initial_moment: dict = None
    ) -> Sandbox:
        graph_collection = GraphCollection.model_validate(graph_collection_dict)
        return await sandbox_factory(
            graph_collection=graph_collection,
            initial_lore=initial_lore or {},
            initial_moment=initial_moment or {}
        )
    return _create

# --- Integration Tests ---

async def test_memoria_add_and_query(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    memoria_sandbox_factory: callable
):
    """
    Tests the basic end-to-end functionality of adding and then querying a memory.
    """
    engine, container, _ = test_engine_setup

    sandbox = await memoria_sandbox_factory(
        graph_collection_dict={
            "main": {
                "nodes": [
                    {"id": "add", "run": [{"runtime": "memoria.add", "config": {"stream": "events", "content": "The player entered the village."}}]},
                    {"id": "query", "depends_on": ["add"], "run": [{"runtime": "memoria.query", "config": {"stream": "events", "latest": 1}}]}
                ]
            }
        }
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


async def test_memoria_aggregate_runtime(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    memoria_sandbox_factory: callable
):
    """
    Tests the full flow from adding, querying, to aggregating memories into a string.
    """
    engine, container, _ = test_engine_setup
    sandbox = await memoria_sandbox_factory(
        graph_collection_dict={
            "main": {
                "nodes": [
                    {"id": "add1", "run": [{"runtime": "memoria.add", "config": {"stream": "log", "content": "First event."}}]},
                    {"id": "add2", "run": [{"runtime": "memoria.add", "config": {"stream": "log", "content": "Second event."}}]},
                    {"id": "query", "depends_on": ["add1", "add2"], "run": [{"runtime": "memoria.query", "config": {"stream": "log", "latest": 2}}]},
                    {"id": "aggregate", "run": [{"runtime": "memoria.aggregate", "config": {
                        "entries": "{{ nodes.query.output }}",
                        "template": "Event #{sequence_id}: {content}",
                        "joiner": " | "
                    }}]}
                ]
            }
        }
    )

    final_sandbox = await engine.step(sandbox, {})
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None

    expected_string = "Event #1: First event. | Event #2: Second event."
    assert final_snapshot.run_output["aggregate"]["output"] == expected_string


async def test_complex_query_with_tags_and_levels(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    memoria_sandbox_factory: callable
):
    """
    Tests querying with multiple filters (tags and levels) to ensure correctness.
    """
    engine, container, _ = test_engine_setup
    sandbox = await memoria_sandbox_factory(
        graph_collection_dict={
            "main": {
                "nodes": [
                    {"id": "add1", "run": [{"runtime": "memoria.add", "config": {"stream": "all", "level": "event", "tags": ["combat"], "content": "A"}}]},
                    {"id": "add2", "run": [{"runtime": "memoria.add", "config": {"stream": "all", "level": "thought", "tags": ["player"], "content": "B"}}]},
                    {"id": "add3", "run": [{"runtime": "memoria.add", "config": {"stream": "all", "level": "event", "tags": ["social", "player"], "content": "C"}}]},
                    {"id": "query", "depends_on": ["add1", "add2", "add3"], "run": [{"runtime": "memoria.query", "config": {
                        "stream": "all",
                        "levels": ["event"],
                        "tags": ["player"]
                    }}]}
                ]
            }
        }
    )

    final_sandbox = await engine.step(sandbox, {})
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None
    
    query_output = final_snapshot.run_output["query"]["output"]
    assert len(query_output) == 1
    assert query_output[0]["content"] == "C"


async def test_synthesis_task_trigger_and_application(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    memoria_sandbox_factory: callable
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

    sandbox = await memoria_sandbox_factory(
        graph_collection_dict={
            "main": {"nodes": [{"id": "add_mem", "run": [{"runtime": "memoria.add", "config": {"stream": "story", "content": "Event X"}}]}
            ]}
        },
        initial_moment={
            "memoria": {
                "__global_sequence__": 0,
                "story": {
                    "config": {"auto_synthesis": {"enabled": True, "trigger_count": 2}},
                    "entries": [], "synthesis_trigger_counter": 0
                }
            }
        }
    )
    
    # Act 1: First event, counter becomes 1.
    sandbox = await engine.step(sandbox, {})
    
    # Act 2: Second event, counter becomes 2, synthesis is triggered.
    sandbox = await engine.step(sandbox, {})
    assert not queue.empty()
    
    # Manually execute the background task.
    task_func, args, kwargs = await queue.get()
    await task_func(container, *args, **kwargs)
    queue.task_done()
    llm_service_mock.request.assert_awaited_once()

    # 【修复】Act 3: 为沙盒设置一个无副作用的图，以触发钩子而不添加新记忆。
    sandbox.lore['graphs'] = {"main": {"nodes": [{"id": "noop", "run": []}]}}
    final_sandbox = await engine.step(sandbox, {})
    
    # Assert: The summary has been applied.
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None
    
    moment = final_snapshot.moment
    story_stream = moment["memoria"]["story"]
    
    # 期望结果: 2个原始事件 + 1个总结 = 3个条目
    assert len(story_stream["entries"]) == 3
    
    summary_entry = story_stream["entries"][-1]
    assert summary_entry["content"] == "A grand adventure began."
    assert summary_entry["level"] == "summary"
    assert story_stream["synthesis_trigger_counter"] == 0


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

    llm_service_mock.request.assert_awaited_once_with(model_name="test", prompt="- e1")
    assert sandbox_id in event_queue
    assert len(event_queue[sandbox_id]) == 1
    event = event_queue[sandbox_id][0]
    assert event["type"] == "memoria_synthesis_completed"
    assert event["content"] == "A summary."