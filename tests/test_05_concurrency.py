# tests/test_05_concurrency.py
import pytest
from uuid import uuid4

from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection


@pytest.mark.asyncio
class TestConcurrencyWithLock:
    """
    测试引擎的宏级原子锁是否能正确处理并发写入，防止竞态条件。
    """

    async def test_concurrent_writes_are_atomic_and_correct(
        self, 
        test_engine, # <-- 【修改】直接请求由 conftest.py 提供的 test_engine
        concurrent_write_collection: GraphCollection
    ):
        """
        验证两个并行节点对同一个 world_state 变量的多次修改是原子性的。
        
        【测试逻辑完全不变】
        这个测试的逻辑非常健壮，它验证了：
        1. 两个没有依赖关系的节点 `incrementer_A` 和 `incrementer_B` 会被并行执行。
        2. 每个节点内部的宏 `world.counter += 1` 是一个经典的 read-modify-write 操作，
           在没有锁的情况下极易出错。
        3. 引擎的 `global_write_lock` 会在执行每个宏脚本之前获取，
           确保整个脚本（即使是 for 循环）作为一个原子单元执行。
        4. 因此，最终的 `world.counter` 必须是确定且正确的值 (200)，而不是一个因竞态条件
           产生的随机值。
        """
        # 1. 准备初始状态
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=concurrent_write_collection,
            world_state={"counter": 0}  # 计数器从 0 开始
        )
        
        # 2. 执行图
        # 引擎将并行调度 incrementer_A 和 incrementer_B
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 3. 验证结果
        final_world_state = final_snapshot.world_state
        run_output = final_snapshot.run_output
        
        # 两个节点中的宏，每个都将计数器增加 100 次
        expected_final_count = 200

        print(f"Final counter value in world_state: {final_world_state.get('counter')}")
        print(f"Final counter value from reader node: {run_output.get('reader', {}).get('output')}")
        
        # 【核心断言】
        # 验证持久化的 world_state 中的最终值是否正确。
        # 如果没有锁，这个值几乎肯定会因为竞态条件而小于 200。
        # 我们的宏级原子锁保证了每个宏脚本的执行都是不可分割的，
        # 因此结果必须是确定和正确的。
        assert final_world_state.get("counter") == expected_final_count
        
        # 验证 reader 节点读取到的也是正确的值
        assert run_output["reader"]["output"] == expected_final_count

        # 验证两个写入节点都成功执行了
        assert "error" not in run_output.get("incrementer_A", {})
        assert "error" not in run_output.get("incrementer_B", {})