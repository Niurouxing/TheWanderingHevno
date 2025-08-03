# plugins/core_engine/tests/test_macros.py
import pytest
from uuid import uuid4

from plugins.core_engine.contracts import StateSnapshot, GraphCollection

@pytest.mark.asyncio
class TestAdvancedMacrosAndRuntimes:

    async def test_advanced_macros_with_depends_on(self, test_engine, advanced_macro_collection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=advanced_macro_collection,
            world_state={"game_difficulty": "easy"}
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        
        # Test 1: Function defined and used correctly
        assert final_snapshot.run_output["use_skill"]["output"] == 5.0

        # Test 2: LLM-proposed code executed correctly
        assert final_snapshot.world_state["game_difficulty"] == "hard"

    async def test_execute_runtime(self, test_engine, execute_runtime_collection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=execute_runtime_collection,
            world_state={"player_status": "normal"}
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        assert final_snapshot.world_state["player_status"] == "empowered"

    async def test_data_format_runtime(self, test_engine):
        engine, _, _ = test_engine
        graph = GraphCollection.model_validate({"main": {"nodes": [
            {"id": "data", "run": [{"runtime": "system.io.input", "config": {"value": [{"name": "A"}, {"name": "B"}]}}]},
            {"id": "formatter", "run": [{"runtime": "system.data.format", "config": {
                "items": "{{ nodes.data.output }}",
                "template": "- {item[name]}",
                "joiner": ", "
            }}]}
        ]}})
        snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph)
        final_snapshot = await engine.step(snapshot, {})
        assert final_snapshot.run_output["formatter"]["output"] == "- A, - B"

    async def test_data_parse_runtime(self, test_engine):
        engine, _, _ = test_engine
        llm_output = '{"result": "success", "value": 42}'
        graph = GraphCollection.model_validate({"main": {"nodes": [
            {"id": "parser", "run": [{"runtime": "system.data.parse", "config": {
                "text": llm_output,
                "format": "json"
            }}]}
        ]}})
        snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph)
        final_snapshot = await engine.step(snapshot, {})
        parsed_output = final_snapshot.run_output["parser"]["output"]
        assert parsed_output == {"result": "success", "value": 42}

    async def test_data_regex_runtime(self, test_engine):
        engine, _, _ = test_engine
        text = "Action: ATTACK, Target: GOBLIN"
        graph = GraphCollection.model_validate({"main": {"nodes": [
            {"id": "matcher", "run": [{"runtime": "system.data.regex", "config": {
                "text": text,
                "pattern": r"Action: (?P<action>\w+), Target: (?P<target>\w+)",
                "mode": "search"
            }}]}
        ]}})
        snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph)
        final_snapshot = await engine.step(snapshot, {})
        regex_output = final_snapshot.run_output["matcher"]["output"]
        assert regex_output == {"action": "ATTACK", "target": "GOBLIN"}