# plugins/core_engine/tests/conftest.py

import pytest
from typing import List, Tuple
from uuid import UUID
from httpx import AsyncClient

# 导入这个文件需要的 Pydantic 模型
from plugins.core_engine.contracts import GraphCollection


# ---- 这里只定义本模块（core_engine）测试专属的、可复用的fixtures ----



@pytest.fixture(scope="session")
def custom_object_storage_collection() -> GraphCollection:
    """
    测试存储和使用自定义类实例 (Robot)。
    这个 fixture 与 engine 的宏执行紧密相关，放在这里是合理的。
    """
    # 这个宏创建 Robot 实例并将其存入 moment
    create_robot_code = """
# 必须先导入类，因为宏的执行环境是独立的
from plugins.core_engine.tests.robot_fixture import Robot
moment.robots = [Robot('R2-D2'), Robot('C-3PO')]
"""
    # 这个宏加载 Robot 实例并调用其方法
    use_robot_code = """
# 加载 R2-D2 实例
r2 = moment.robots[0]
r2.take_damage(25)
# 返回一个可序列化的值
r2.hp
"""
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "create_robots", "run": [{"runtime": "system.execute", "config": {"code": create_robot_code}}]},
        {"id": "use_robot", "depends_on": ["create_robots"], "run": [{"runtime": "system.execute", "config": {"code": use_robot_code}}]},
    ]}})


# API 辅助函数 fixtures
@pytest.fixture(scope="session")
def mutate_resource_api():
    """Fixture to provide a callable for making resource mutation API calls."""
    async def _mutate_resource(client: AsyncClient, sandbox_id: UUID, mutations: List[dict]):
        from plugins.core_engine.contracts import MutateResourceRequest
        
        request_body = MutateResourceRequest(mutations=mutations).model_dump(mode='json')
        response = await client.post(
            f"/api/sandboxes/{sandbox_id}/resource:mutate",
            json=request_body
        )
        return response
    return _mutate_resource

@pytest.fixture(scope="session")
def query_resource_api():
    """Fixture to provide a callable for making resource query API calls."""
    async def _query_resource(client: AsyncClient, sandbox_id: UUID, paths: List[str]) -> dict:
        request_body = {"paths": paths}
        response = await client.post(
            f"/api/sandboxes/{sandbox_id}/resource:query",
            json=request_body
        )
        assert response.status_code == 200, f"Query failed: {response.text}"
        return response.json()["results"]
    return _query_resource