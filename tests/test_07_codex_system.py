# tests/test_07_codex_system.py

import pytest
from uuid import uuid4

from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

@pytest.mark.asyncio
class TestCodexSystem:
    """
    对 Hevno Codex 系统的集成测试 (system.invoke 运行时)。
    这个测试类现在完全依赖 conftest.py 来提供配置好的 test_engine。
    """

    async def test_basic_invoke_always_on(
        self,
        test_engine, 
        codex_basic_data: dict
    ):
        """
        测试 `system.invoke` 的基本功能：
        - 从 `world.codices` 加载法典。
        - 激活 `always_on` 条目。
        - 渲染内容并按优先级拼接。
        """
        graph_collection = GraphCollection.model_validate(codex_basic_data["graph"])
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph_collection,
            world_state={"codices": codex_basic_data["codices"]}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        invoke_output = output["invoke_test"]["output"]

        assert isinstance(invoke_output, str)
        # 优先级: greeting (10) > intro (5)。顺序是确定的。
        expected_text = "你好，冒险者！\n\n欢迎来到这个奇幻的世界。"
        assert invoke_output == expected_text

    async def test_invoke_keyword_and_priority(
        self,
        test_engine, 
        codex_keyword_and_priority_data: dict
    ):
        """
        测试 `on_keyword` 触发模式和 `priority` 排序。
        """
        graph_collection = GraphCollection.model_validate(codex_keyword_and_priority_data["graph"])
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph_collection,
            world_state={"codices": codex_keyword_and_priority_data["codices"]}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output

        # --- Test invoke_weather ---
        weather_output = output["invoke_weather"]["output"]
        assert isinstance(weather_output, str)
        # source: "今天的魔法天气怎么样？" 匹配 "魔法天气" (priority 30)
        assert "魔法能量今天异常活跃" in weather_output
        assert "阳光明媚" not in weather_output
        assert "下着大雨" not in weather_output

        # --- Test invoke_mood ---
        mood_output = output["invoke_mood"]["output"]
        assert isinstance(mood_output, str)
        # source: "我很开心，因为天气很好。" 匹配 "开心" (priority 5)
        assert "你看起来很高兴。" in mood_output
        assert "你似乎有些低落。" not in mood_output

    async def test_invoke_macro_evaluation_and_trigger_context(
        self,
        test_engine, 
        codex_macro_eval_data: dict
    ):
        """
        测试条目内部宏的正确求值和 `trigger` 上下文的访问。
        还测试 `debug` 模式的输出结构。
        """
        graph_collection = GraphCollection.model_validate(codex_macro_eval_data["graph"])
        initial_world_state = {
            "codices": codex_macro_eval_data["codices"],
            "is_night": False,  # night_info 将被禁用
            "player_level": 5,  # level_message 将被启用，高优先级
            "hidden_keyword": "秘密" # secret_keyword_entry 将被启用
        }
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph_collection,
            world_state=initial_world_state
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        invoke_result = output["get_weather_report"]["output"]

        # 1. 验证是调试模式输出
        assert isinstance(invoke_result, dict)
        assert "final_text" in invoke_result
        assert "trace" in invoke_result

        final_text = invoke_result["final_text"]
        trace = invoke_result["trace"]

        # 2. 验证内容
        assert "现在是白天" not in final_text # is_enabled 宏求值为 False
        assert "你的等级是：5级。" in final_text
        assert "你提到了'秘密'，这是一个秘密信息。" in final_text
        assert "原始输入是：'请告诉我关于秘密和夜幕下的世界。'。" in final_text

        # 3. 验证优先级和顺序 (最高优先级在最前面)
        # priority: level_message (100) > secret_keyword_entry (50) > always_on (1)
        assert final_text.find("你的等级是：5级。") < final_text.find("你提到了'秘密'")
        assert final_text.find("你提到了'秘密'") < final_text.find("原始输入是：'请告诉我")

        # 4. 验证 trace 信息
        rejected_ids = {entry["id"] for entry in trace["rejected_entries"]}
        assert "night_info" in rejected_ids
        assert any("is_enabled macro returned false" in e["reason"] for e in trace["rejected_entries"] if e["id"] == "night_info")
        
        activated_ids = {entry["id"] for entry in trace["initial_activation"]}
        assert activated_ids == {"level_message", "secret_keyword_entry", "always_on_with_trigger_info"}

        secret_entry_trace = next(e for e in trace["initial_activation"] if e["id"] == "secret_keyword_entry")
        assert secret_entry_trace["matched_keywords"] == ["秘密"]

    async def test_invoke_recursion_enabled(
        self,
        test_engine, 
        codex_recursion_data: dict
    ):
        """
        测试 `recursion_enabled` 模式下，条目内容能触发新的条目，
        且遵循优先级规则。
        """
        graph_collection = GraphCollection.model_validate(codex_recursion_data["graph"])
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph_collection,
            world_state={"codices": codex_recursion_data["codices"]}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        invoke_result = output["recursive_invoke"]["output"]

        assert isinstance(invoke_result, dict)
        final_text = invoke_result["final_text"]
        trace = invoke_result["trace"]
        
        # 【修正】根据您的 codex_recursion_data fixture 的具体内容，我重新推导了正确的输出顺序。
        # 初始池: [A(10), D(5)] -> 渲染 A (内容 "引出B")
        # 递归触发 B -> 当前池: [B(20), D(5)] -> 渲染 B (内容 "引出C")
        # 递归触发 C -> 当前池: [C(30), D(5)] -> 渲染 C
        # 当前池: [D(5)] -> 渲染 D
        # 最终拼接时，是按渲染顺序来的。所以正确的渲染顺序是 A -> B -> C -> D
        expected_rendered_order = [
            "这是关于A的信息，它引出B。",
            "B被A触发了，它又引出C。",
            "C被B触发了，这是最终信息。",
            "这是一个总是存在的背景信息。",
        ]
        
        # 断言最终的文本拼接顺序
        assert final_text.split("\n\n") == expected_rendered_order

        # Trace 日志中的渲染顺序也应该是 A -> B -> C -> D
        rendered_order_ids = [e["id"] for e in trace["evaluation_log"] if e["status"] == "rendered"]
        assert rendered_order_ids == ["entry_A", "entry_B", "entry_C", "entry_D_always_on"]
        
        # 验证 trace 的激活记录
        assert len(trace["initial_activation"]) == 2 # A 和 D
        assert len(trace["recursive_activations"]) == 2 # B 和 C

    async def test_invoke_invalid_codex_structure_error(
        self,
        test_engine, 
        codex_invalid_structure_data: dict
    ):
        """
        测试 `world.codices` 结构无效时，`system.invoke` 能捕获错误。
        """
        graph_collection = GraphCollection.model_validate(codex_invalid_structure_data["graph"])
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph_collection,
            world_state={"codices": codex_invalid_structure_data["codices"]}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        invoke_result = output["invoke_invalid"]

        assert "error" in invoke_result
        assert "Invalid codex structure" in invoke_result["error"]
        assert "Input should be a valid string" in invoke_result["error"]

    async def test_invoke_nonexistent_codex_error(
        self,
        test_engine, 
        codex_nonexistent_codex_data: dict
    ):
        """
        测试 `system.invoke` 尝试从不存在的法典中读取时能捕获错误。
        """
        graph_collection = GraphCollection.model_validate(codex_nonexistent_codex_data["graph"])
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph_collection,
            world_state={"codices": codex_nonexistent_codex_data["codices"]}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        invoke_result = output["invoke_nonexistent"]

        assert "error" in invoke_result
        assert "Codex 'nonexistent_codex' not found" in invoke_result["error"]
        
    async def test_invoke_concurrent_world_writes(
        self,
        test_engine, 
        codex_concurrent_world_write_data: dict
    ):
        """
        测试 `system.invoke` 内部宏对 `world_state` 的并发写入是否原子安全。
        """
        graph_collection = GraphCollection.model_validate(codex_concurrent_world_write_data["graph"])
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph_collection,
            world_state={
                "codices": codex_concurrent_world_write_data["codices"],
                "counter": 0
            }
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        
        assert "error" not in output["invoke_and_increment"]

        # 由于所有条目共享同一个关键字，它们会被并发求值。
        # 即使它们有优先级，在渲染阶段（content evaluation）的求值是并发的，
        # 依赖于宏级原子锁来保证最终结果的正确性。
        # 初始 0 + 3 + 2 + 1 = 6。
        expected_counter = 6
        assert final_snapshot.world_state["counter"] == expected_counter
        assert output["read_counter"]["output"] == expected_counter

        # 最终文本的拼接顺序依然由优先级决定
        invoke_text = output["invoke_and_increment"]["output"]
        assert invoke_text.find("Incremented 3.") < invoke_text.find("Incremented 2.")
        assert invoke_text.find("Incremented 2.") < invoke_text.find("Incremented 1.")