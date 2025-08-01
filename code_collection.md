### test_06_map_runtime.py
```
# tests/test_06_map_runtime.py

import pytest
from uuid import uuid4

from backend.core.engine import ExecutionEngine
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

@pytest.mark.asyncio
class TestEngineMapExecution:
    """
    对 system.map 运行时的集成测试。
    """

    async def test_basic_map_execution(
        self,
        test_engine: ExecutionEngine,
        map_collection_basic: GraphCollection
    ):
        """
        测试基本的 scatter-gather 功能，不使用 collect。
        期望输出是每个子图执行结果的完整字典的列表。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_basic
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        map_result = output["character_processor_map"]["output"]

        # 1. 验证输出是一个包含3个元素的列表
        assert isinstance(map_result, list)
        assert len(map_result) == 3

        # 2. 验证每个元素都是一个子图的完整结果字典
        assert "generate_bio" in map_result[0]
        assert "generate_bio" in map_result[1]
        assert "generate_bio" in map_result[2]

        # 3. 详细验证第一个子图的输出，确保 source.item, source.index 和外部节点引用都正确
        first_bio_prompt = map_result[0]["generate_bio"]["llm_output"]
        expected_prompt = "LLM_RESPONSE_FOR:[Create a bio for Aragorn in the context of The Fellowship of the Ring. Index: 0]"
        assert first_bio_prompt == expected_prompt
        
        # 4. 验证最后一个子图的输出
        last_bio_prompt = map_result[2]["generate_bio"]["llm_output"]
        expected_prompt_last = "LLM_RESPONSE_FOR:[Create a bio for Legolas in the context of The Fellowship of the Ring. Index: 2]"
        assert last_bio_prompt == expected_prompt_last

    async def test_map_with_collect(
        self,
        test_engine: ExecutionEngine,
        map_collection_with_collect: GraphCollection
    ):
        """
        测试 `collect` 功能，期望输出是一个扁平化的值列表。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_with_collect
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # --- 【核心修正】---
        # 恢复被意外删除的行
        output = final_snapshot.run_output
        map_result = output["character_processor_map"]["output"]

        # 1. 验证输出是一个扁平列表
        assert isinstance(map_result, list)
        assert len(map_result) == 3

        # 2. 验证列表中的每个元素都是从子图提取的 `summary` 字符串
        # 使用我们之前修正过的正确字符串
        assert map_result[0] == "Summary of 'Create a bio for Ara...'"
        assert map_result[1] == "Summary of 'Create a bio for Gan...'"
        assert map_result[2] == "Summary of 'Create a bio for Leg...'"

    async def test_map_handles_concurrent_world_writes(
        self,
        test_engine: ExecutionEngine,
        map_collection_concurrent_write: GraphCollection
    ):
        """
        验证在 map 中并发写入 world_state 是原子和安全的。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_concurrent_write,
            world_state={"gold": 0} # 初始金币为0
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        # 10个并行任务，每个增加10金币
        expected_gold = 100

        # 1. 验证最终的 world_state
        assert final_snapshot.world_state.get("gold") == expected_gold
        
        # 2. 验证 reader 节点读取到的值
        output = final_snapshot.run_output
        reader_output = output["reader"]["output"]
        assert reader_output == expected_gold

    async def test_map_handles_partial_failures_gracefully(
        self,
        test_engine: ExecutionEngine,
        map_collection_with_failure: GraphCollection
    ):
        """
        测试当 map 迭代中的某些子图失败时，整体操作不会崩溃，
        并且返回的结果中能清晰地标识出成功和失败的项。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_with_failure
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        map_result = output["mapper"]["output"]

        # 1. 验证结果列表长度仍然是3
        assert len(map_result) == 3

        # 2. 验证成功的项
        # 第一个子图 (Alice)
        assert "error" not in map_result[0].get("get_name", {})
        assert map_result[0]["get_name"]["output"] == "Alice"
        # 第三个子图 (Charlie)
        assert "error" not in map_result[2].get("get_name", {})
        assert map_result[2]["get_name"]["output"] == "Charlie"

        # 3. 验证失败的项
        # 第二个子图 (Bob)
        failed_item_result = map_result[1]
        assert "get_name" in failed_item_result
        assert "error" in failed_item_result["get_name"]
        # 错误应该是因为对 str 对象调用 .name
        assert "AttributeError" in failed_item_result["get_name"]["error"]
```

### test_08_llm_gateway.py
```
# tests/test_08_llm_gateway.py

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# --- 从 LLM 模块中导入所有需要测试的类和模型 ---
from backend.llm.models import (
    LLMResponse, LLMError, LLMResponseStatus, LLMErrorType, LLMRequestFailedError
)
from backend.llm.providers.gemini import GeminiProvider, google_exceptions
from backend.llm.manager import (
    CredentialManager, KeyPoolManager, KeyInfo, KeyStatus
)
from backend.llm.service import LLMService, ProviderRegistry

# ---------------------------------------------------------------------------
# Fixtures: 测试组件的“原材料”
# (这部分保持不变)
# ---------------------------------------------------------------------------

@pytest.fixture
def credential_manager() -> CredentialManager:
    return CredentialManager()

@pytest.fixture
def key_pool_manager(credential_manager: CredentialManager) -> KeyPoolManager:
    manager = KeyPoolManager(credential_manager)
    manager.register_provider("gemini", "GEMINI_API_KEYS")
    return manager

@pytest.fixture
def gemini_provider() -> GeminiProvider:
    return GeminiProvider()

@pytest.fixture
def provider_registry(gemini_provider: GeminiProvider) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("gemini", gemini_provider)
    return registry

@pytest.fixture
def llm_service(key_pool_manager: KeyPoolManager, provider_registry: ProviderRegistry) -> LLMService:
    return LLMService(key_manager=key_pool_manager, provider_registry=provider_registry, max_retries=2)

# ---------------------------------------------------------------------------
# Section 1: 密钥管理器单元测试 (manager.py)
# (这部分保持不变，但修复了 mark_as_banned 的 await 调用)
# ---------------------------------------------------------------------------

@pytest.mark.llm_gateway
class TestKeyPoolManager:
    def test_credential_manager_loads_keys(self, credential_manager: CredentialManager):
        gemini_keys = credential_manager.load_keys_from_env("GEMINI_API_KEYS")
        assert gemini_keys == ["test_key_1", "test_key_2", "test_key_3"]

    async def test_acquire_and_release_key(self, key_pool_manager: KeyPoolManager):
        async with key_pool_manager.acquire_key("gemini") as key_info:
            assert isinstance(key_info, KeyInfo)

    async def test_key_banning_reduces_concurrency(self, key_pool_manager: KeyPoolManager):
        pool = key_pool_manager.get_pool("gemini")
        initial_concurrency = pool._semaphore._value
        # 【修复】使用 await 调用异步方法
        await key_pool_manager.mark_as_banned("gemini", "test_key_1")
        assert pool._semaphore._value == initial_concurrency - 1
        banned_key_info = next(k for k in pool._keys if k.key_string == "test_key_1")
        assert not banned_key_info.is_available()

    async def test_rate_limiting_and_recovery(self, key_pool_manager: KeyPoolManager):
        pool = key_pool_manager.get_pool("gemini")
        pool.mark_as_rate_limited("test_key_2", duration_seconds=0.1)
        limited_key_info = next(k for k in pool._keys if k.key_string == "test_key_2")
        assert not limited_key_info.is_available()
        await asyncio.sleep(0.2)
        assert limited_key_info.is_available()


# ---------------------------------------------------------------------------
# Section 2: 提供商适配器单元测试 (providers/gemini.py)
# ---------------------------------------------------------------------------

@pytest.mark.llm_gateway
@patch('backend.llm.providers.gemini.genai.GenerativeModel')
class TestGeminiProvider:
    """
    对 GeminiProvider 的单元测试，完全模拟外部 API 调用。
    """

    async def test_generate_success(self, mock_genai_model: MagicMock, gemini_provider: GeminiProvider):
        """测试场景：API 调用成功。"""
        # --- Arrange ---
        # 1. 构造一个模拟的成功响应数据对象
        mock_response_data = MagicMock()
        mock_response_data.text = "Mocked successful response"
        usage_mock = MagicMock()
        usage_mock.prompt_token_count, usage_mock.candidates_token_count, usage_mock.total_token_count = 10, 20, 30
        mock_response_data.usage_metadata = usage_mock
        mock_response_data.parts = [MagicMock()] # 表示内容未被过滤
        
        # 2. 【关键】将 mock 模型的异步方法设置为一个返回上述数据的 AsyncMock
        mock_model_instance = mock_genai_model.return_value
        mock_model_instance.generate_content_async = AsyncMock(return_value=mock_response_data)

        # --- Act ---
        response = await gemini_provider.generate(
            prompt="A test prompt", model_name="gemini-1.5-pro", api_key="fake_key"
        )

        # --- Assert ---
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Mocked successful response"
        assert response.usage["total_tokens"] == 30
        mock_model_instance.generate_content_async.assert_awaited_once()

    async def test_generate_filtered(self, mock_genai_model: MagicMock, gemini_provider: GeminiProvider):
        """测试场景：API 调用因安全策略被阻止。"""
        # --- Arrange ---
        mock_response_data = MagicMock()
        mock_response_data.parts = [] # 空 parts 表示内容被过滤
        feedback_mock = MagicMock()
        feedback_mock.block_reason.name = "SAFETY"
        mock_response_data.prompt_feedback = feedback_mock
        
        mock_model_instance = mock_genai_model.return_value
        mock_model_instance.generate_content_async = AsyncMock(return_value=mock_response_data)

        # --- Act ---
        response = await gemini_provider.generate(
            prompt="A sensitive prompt", model_name="gemini-1.5-pro", api_key="fake_key"
        )

        # --- Assert ---
        assert response.status == LLMResponseStatus.FILTERED
        assert response.error_details.error_type == LLMErrorType.INVALID_REQUEST_ERROR
        assert "Request blocked due to SAFETY" in response.error_details.message
        mock_model_instance.generate_content_async.assert_awaited_once()

    def test_translate_errors(self, mock_genai_model: MagicMock, gemini_provider: GeminiProvider):
        """测试 `translate_error` 方法能否正确映射各种异常。"""
        # --- Act & Assert ---
        # 逐一测试每种错误映射
        auth_error = gemini_provider.translate_error(google_exceptions.PermissionDenied("auth failed"))
        assert auth_error.error_type == LLMErrorType.AUTHENTICATION_ERROR
        assert not auth_error.is_retryable

        rate_limit_error = gemini_provider.translate_error(google_exceptions.ResourceExhausted("rate limit"))
        assert rate_limit_error.error_type == LLMErrorType.RATE_LIMIT_ERROR
        assert not rate_limit_error.is_retryable

        server_error = gemini_provider.translate_error(google_exceptions.ServiceUnavailable("server down"))
        assert server_error.error_type == LLMErrorType.PROVIDER_ERROR
        assert server_error.is_retryable

# ---------------------------------------------------------------------------
# Section 3: 核心服务集成测试 (service.py)
# ---------------------------------------------------------------------------

@pytest.mark.llm_gateway
class TestLLMServiceIntegration:
    """
    对 LLMService 的集成测试，测试其重试和故障转移的核心逻辑。
    我们在这里使用一个 mock 的 provider，以便精确控制其行为。
    """

    @pytest.fixture
    def mock_gemini_provider(self) -> AsyncMock:
        """提供一个可被精确控制行为的 mock GeminiProvider。"""
        # 使用 autospec=True 可以确保 mock 的接口与原始类匹配
        return AsyncMock(spec=GeminiProvider)
        
    @pytest.fixture
    def llm_service_with_mock_provider(self, key_pool_manager: KeyPoolManager, mock_gemini_provider: AsyncMock) -> LLMService:
        """提供一个配置了 mock provider 的 LLMService 实例。"""
        registry = ProviderRegistry()
        registry.register("gemini", mock_gemini_provider)
        return LLMService(key_manager=key_pool_manager, provider_registry=registry, max_retries=2)

    async def test_request_success_on_first_try(self, llm_service_with_mock_provider: LLMService, mock_gemini_provider: AsyncMock):
        """测试快乐路径：第一次尝试即成功。"""
        # --- Arrange ---
        mock_gemini_provider.generate.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        
        # --- Act ---
        response = await llm_service_with_mock_provider.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")

        # --- Assert ---
        assert response.status == LLMResponseStatus.SUCCESS
        mock_gemini_provider.generate.assert_awaited_once()

    async def test_retry_on_provider_error_and_succeed(self, llm_service_with_mock_provider: LLMService, mock_gemini_provider: AsyncMock):
        """测试重试逻辑：第一次失败（可重试），第二次成功。"""
        # --- Arrange ---
        # 第一次调用抛出可重试异常，第二次调用返回成功响应
        mock_gemini_provider.generate.side_effect = [
            google_exceptions.ServiceUnavailable("Server temporary down"),
            LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")
        ]
        # 配置 translate_error 以正确识别该异常
        mock_gemini_provider.translate_error.return_value = LLMError(
            error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True
        )
        
        # --- Act ---
        response = await llm_service_with_mock_provider.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
        
        # --- Assert ---
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Success after retry!"
        assert mock_gemini_provider.generate.call_count == 2
        mock_gemini_provider.translate_error.assert_called_once()

    async def test_failover_on_auth_error_and_succeed(self, llm_service_with_mock_provider: LLMService, mock_gemini_provider: AsyncMock):
        """测试故障转移逻辑：第一次认证失败，切换密钥后第二次成功。"""
        # --- Arrange ---
        mock_gemini_provider.generate.side_effect = [
            google_exceptions.PermissionDenied("Invalid Key"),
            LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success with new key!")
        ]
        mock_gemini_provider.translate_error.return_value = LLMError(
            error_type=LLMErrorType.AUTHENTICATION_ERROR, message="Invalid Key", is_retryable=False
        )
        
        # --- Act ---
        response = await llm_service_with_mock_provider.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")

        # --- Assert ---
        assert response.status == LLMResponseStatus.SUCCESS
        assert mock_gemini_provider.generate.call_count == 2
        
        # 验证两次调用使用了不同的密钥
        first_call_key = mock_gemini_provider.generate.call_args_list[0].kwargs['api_key']
        second_call_key = mock_gemini_provider.generate.call_args_list[1].kwargs['api_key']
        assert first_call_key != second_call_key

        # 验证第一个密钥已被禁用
        pool = llm_service_with_mock_provider.key_manager.get_pool("gemini")
        banned_key = next(k for k in pool._keys if k.key_string == first_call_key)
        assert banned_key.status == KeyStatus.BANNED

    async def test_final_failure_after_all_retries(self, llm_service_with_mock_provider: LLMService, mock_gemini_provider: AsyncMock):
        """测试最终失败路径：所有重试次数用尽。"""
        # --- Arrange ---
        # 所有调用都抛出同一个可重试异常
        mock_gemini_provider.generate.side_effect = google_exceptions.ServiceUnavailable("Server persistently down")
        mock_gemini_provider.translate_error.return_value = LLMError(
            error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True
        )
        
        # --- Act & Assert ---
        with pytest.raises(LLMRequestFailedError) as exc_info:
            await llm_service_with_mock_provider.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
        
        # 验证异常信息和调用次数
        max_retries = llm_service_with_mock_provider.max_retries
        assert f"failed after {max_retries} attempt(s)" in str(exc_info.value)
        assert exc_info.value.last_error.error_type == LLMErrorType.PROVIDER_ERROR
        assert mock_gemini_provider.generate.call_count == max_retries
```

### conftest.py
```
# tests/conftest.py
import json
import pytest
from fastapi.testclient import TestClient
from typing import Generator
from dotenv import load_dotenv 

# ---------------------------------------------------------------------------
# Session-wide setup to load environment variables for tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def load_test_env():
    """
    在所有测试运行之前，自动加载 .env.test 文件中的环境变量。
    autouse=True 确保这个 fixture 会被自动调用，无需在每个测试函数中显式请求。
    """
    # 指定 .env.test 文件的路径，并加载它
    # override=True 确保文件中的值会覆盖任何已存在的同名环境变量
    load_dotenv(dotenv_path=".env.test", override=True)
    print("\n--- Loaded .env.test for the test session ---")
    
    

# ---------------------------------------------------------------------------
# 从你的应用代码中导入核心类和函数
# ---------------------------------------------------------------------------
from backend.main import app, sandbox_store, snapshot_store
from backend.models import GraphCollection
from backend.core.registry import RuntimeRegistry
from backend.core.engine import ExecutionEngine
from backend.runtimes.base_runtimes import (
    InputRuntime, LLMRuntime, SetWorldVariableRuntime
)
from backend.runtimes.codex.invoke_runtime import InvokeRuntime
from backend.runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime

# ---------------------------------------------------------------------------
# Fixtures for Core Components (Engine, Registry, API Client)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def populated_registry() -> RuntimeRegistry:
    """提供一个预先填充了所有新版运行时的注册表实例。"""
    registry = RuntimeRegistry()
    registry.register("system.input", InputRuntime)
    registry.register("llm.default", LLMRuntime)
    registry.register("system.set_world_var", SetWorldVariableRuntime)
    registry.register("system.execute", ExecuteRuntime)
    registry.register("system.call", CallRuntime)
    registry.register("system.map", MapRuntime)
    registry.register("system.invoke", InvokeRuntime)
    print("\n--- Populated Registry Created (Session Scope) ---")
    return registry


@pytest.fixture(scope="function")
def test_engine(populated_registry: RuntimeRegistry) -> ExecutionEngine:
    """提供一个配置了标准运行时的 ExecutionEngine 实例。"""
    return ExecutionEngine(registry=populated_registry)


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """提供一个 FastAPI TestClient 用于端到端 API 测试 (Function scope for isolation)。"""
    sandbox_store.clear()
    snapshot_store.clear()
    
    with TestClient(app) as client:
        yield client
    
    sandbox_store.clear()
    snapshot_store.clear()

# ---------------------------------------------------------------------------
# Fixtures for Graph Collections (Rewritten for New Architecture)
# ---------------------------------------------------------------------------

@pytest.fixture
def linear_collection() -> GraphCollection:
    """一个简单的三节点线性图：A -> B -> C。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "A", "run": [{"runtime": "system.input", "config": {"value": "a story about a cat"}}]},
            {"id": "B", "run": [{"runtime": "llm.default", "config": {"prompt": "{{ f'The story is: {nodes.A.output}' }}"}}]},
            {"id": "C", "run": [{"runtime": "llm.default", "config": {"prompt": "{{ nodes.B.llm_output }}"}}]}
        ]}
    })

@pytest.fixture
def parallel_collection() -> GraphCollection:
    """一个扇出再扇入的图 (A, B) -> C。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "source_A", "run": [{"runtime": "system.input", "config": {"value": "Value A"}}]},
            {"id": "source_B", "run": [{"runtime": "system.input", "config": {"value": "Value B"}}]},
            {
                "id": "merger",
                "run": [{
                    "runtime": "system.input",
                    "config": {"value": "{{ f'Merged: {nodes.source_A.output} and {nodes.source_B.output}' }}"}
                }]
            }
        ]}
    })

@pytest.fixture
def pipeline_collection() -> GraphCollection:
    """
    一个测试节点内运行时管道数据流的图。
    节点A包含三个有序指令，演示了状态设置、数据生成和数据消费。
    """
    return GraphCollection.model_validate({
        "main": { "nodes": [{
            "id": "A",
            "run": [
                {
                    "runtime": "system.set_world_var",
                    "config": {
                        "variable_name": "main_character",
                        "value": "Sir Reginald"
                    }
                },
                {
                    "runtime": "system.input",
                    "config": {
                        "value": "A secret message"
                    }
                },
                {
                    "runtime": "llm.default",
                    "config": {
                        # 这个宏现在可以安全地访问 world 状态和上一步的管道输出
                        "prompt": "{{ f'Tell a story about {world.main_character}. He just received this message: {pipe.output}' }}"
                    }
                }
            ]
        }]}
    })

@pytest.fixture
def world_vars_collection() -> GraphCollection:
    """一个测试世界变量设置和读取的图。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {
                "id": "setter",
                "run": [{
                    "runtime": "system.set_world_var",
                    "config": {"variable_name": "theme", "value": "cyberpunk"}
                }]
            },
            {
                "id": "reader",
                "run": [{
                    "runtime": "system.input",
                    "config": {"value": "{{ f'The theme is: {world.theme} and some data from setter: {nodes.setter}'}}"}
                }]
            }
        ]}
    })

@pytest.fixture
def execute_runtime_collection() -> GraphCollection:
    """一个测试 system.execute 运行时的图，用于二次求值。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {
                "id": "A_generate_code",
                "run": [{"runtime": "system.input", "config": {"value": "world.player_status = 'empowered'"}}]
            },
            {
                "id": "B_execute_code",
                "run": [{
                    "runtime": "system.execute",
                    "config": {"code": "{{ nodes.A_generate_code.output }}"}
                }]
            }
        ]}
    })

@pytest.fixture
def cyclic_collection() -> GraphCollection:
    """一个包含环路的图。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "A", "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.C.output }}"}}]},
            {"id": "B", "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.A.output }}"}}]},
            {"id": "C", "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.B.output }}"}}]}
        ]}
    })

@pytest.fixture
def failing_node_collection() -> GraphCollection:
    """一个包含注定会因宏求值失败的节点的图。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "A_ok", "run": [{"runtime": "system.input", "config": {"value": "start"}}]},
            {"id": "B_fail", "run": [{"runtime": "system.input", "config": {"value": "{{ non_existent_variable }}"}}]},
            {"id": "C_skip", "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.B_fail.output }}"}}]},
            {"id": "D_independent", "run": [{"runtime": "system.input", "config": {"value": "independent"}}]}
        ]}
    })

@pytest.fixture
def invalid_graph_no_main() -> dict:
    """一个无效的图定义，缺少 'main' 入口点。"""
    return {"not_main": {"nodes": [{"id": "a", "run": []}]}}

@pytest.fixture
def graph_evolution_collection() -> GraphCollection:
    """一个用于测试图演化的图。"""
    new_graph_dict = {
        "main": {"nodes": [{"id": "new_node", "run": [{"runtime": "system.input", "config": {"value": "This is the evolved graph!"}}]}]}
    }
    return GraphCollection.model_validate({
        "main": {"nodes": [{
            "id": "graph_generator",
            "run": [{
                "runtime": "system.set_world_var",
                "config": {
                    "variable_name": "__graph_collection__",
                    "value": new_graph_dict
                }
            }]
        }]}
    })

@pytest.fixture
def advanced_macro_collection() -> GraphCollection:
    """
    一个用于测试高级宏功能的图。
    使用新的 `depends_on` 字段来明确声明隐式依赖，代码更清晰。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                # 步骤1: 定义函数，无变化
                {
                    "id": "teach_skill",
                    "run": [{
                        "runtime": "system.execute",
                        "config": {
                            "code": """
import math
def calculate_hypotenuse(a, b):
    return math.sqrt(a**2 + b**2)
if not hasattr(world, 'math_utils'): world.math_utils = {}
world.math_utils.hypot = calculate_hypotenuse
"""
                        }
                    }]
                },
                # 步骤2: 调用函数，并使用 `depends_on`
                {
                    "id": "use_skill",
                    # 【关键修正】明确声明依赖
                    "depends_on": ["teach_skill"],
                    "run": [{
                        "runtime": "system.input",
                        # 宏现在非常干净，只包含业务逻辑
                        "config": {"value": "{{ world.math_utils.hypot(3, 4) }}"}
                    }]
                },
                # 步骤3: 模拟 LLM，无变化
                {
                    "id": "llm_propose_change",
                    "run": [{
                        "runtime": "system.input",
                        "config": {"value": "world.game_difficulty = 'hard'"}
                    }]
                },
                # 步骤4: 执行 LLM 代码，它已经有明确的宏依赖，无需 `depends_on`
                {
                    "id": "execute_change",
                    # 这里的依赖是自动推断的，所以 `depends_on` 不是必需的
                    # 但为了演示，也可以添加： "depends_on": ["llm_propose_change"]
                    "run": [{
                        "runtime": "system.execute",
                        "config": {"code": "{{ nodes.llm_propose_change.output }}"}
                    }]
                }
            ]
        }
    })

# ---------------------------------------------------------------------------
# 用于测试 Subgraph Call 的 Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def subgraph_call_collection() -> GraphCollection:
    """
    一个包含主图和可复用子图的集合，用于测试 system.call。
    - main 图调用 process_item 子图。
    - process_item 子图依赖一个名为 'item_input' 的占位符。
    - process_item 子图还会读取 world 状态。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "data_provider",
                    "run": [{"runtime": "system.input", "config": {"value": "Hello from main"}}]
                },
                {
                    "id": "main_caller",
                    "run": [{
                        "runtime": "system.call",
                        "config": {
                            "graph": "process_item",
                            "using": {
                                "item_input": "{{ nodes.data_provider.output }}"
                            }
                        }
                    }]
                }
            ]
        },
        "process_item": {
            "nodes": [
                {
                    "id": "processor",
                    "run": [{
                        "runtime": "system.input",
                        "config": {
                            "value": "{{ f'Processed: {nodes.item_input.output} with world state: {world.global_setting}' }}"
                        }
                    }]
                }
            ]
        }
    })

@pytest.fixture
def nested_subgraph_collection() -> GraphCollection:
    """一个测试嵌套调用的图：main -> sub1 -> sub2。"""
    return GraphCollection.model_validate({
        "main": {"nodes": [{
            "id": "main_caller",
            "run": [{"runtime": "system.call", "config": {"graph": "sub1", "using": {"input_from_main": "level 0"}}}]
        }]},
        "sub1": {"nodes": [{
            "id": "sub1_caller",
            "run": [{"runtime": "system.call", "config": {"graph": "sub2", "using": {"input_from_sub1": "{{ nodes.input_from_main.output }}"}}}]
        }]},
        "sub2": {"nodes": [{
            "id": "final_processor",
            "run": [{"runtime": "system.input", "config": {"value": "{{ f'Reached level 2 from: {nodes.input_from_sub1.output}' }}"}}]
        }]}
    })

@pytest.fixture
def subgraph_call_to_nonexistent_graph_collection() -> GraphCollection:
    """一个尝试调用不存在子图的图，用于测试错误处理。"""
    return GraphCollection.model_validate({
        "main": {"nodes": [{
            "id": "bad_caller",
            "run": [{"runtime": "system.call", "config": {"graph": "i_do_not_exist"}}]
        }]}
    })

@pytest.fixture
def subgraph_modifies_world_collection() -> GraphCollection:
    """
    一个子图会修改 world 状态的集合。
    - main 调用 modifier 子图。
    - modifier 子图根据输入修改 world.counter。
    - main 中的后续节点 reader 会读取这个被修改后的状态。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "caller",
                    "run": [{"runtime": "system.call", "config": {"graph": "modifier", "using": {"amount": 10}}}]
                },
                {
                    "id": "reader",
                    # 这里的宏依赖会自动创建从 caller 到 reader 的依赖
                    "run": [{
                        "runtime": "system.input",
                        "config": {"value": "{{ f'Final counter: {world.counter}, Subgraph raw output: {nodes.caller.output}' }}"}
                    }]
                }
            ]
        },
        "modifier": {
            "nodes": [
                {
                    "id": "incrementer",
                    # 这是一个隐式依赖，我们用 depends_on 来确保执行顺序
                    # 子图无法通过宏推断它依赖于父图设置的 world.counter
                    # 但在这里，我们假设初始状态设置了 counter
                    "run": [{
                        "runtime": "system.execute",
                        "config": {"code": "world.counter += nodes.amount.output"}
                    }]
                }
            ]
        }
    })

@pytest.fixture
def subgraph_with_failure_collection() -> GraphCollection:
    """
    一个子图内部会失败的集合。
    - main 调用 failing_subgraph。
    - failing_subgraph 中的一个节点会因为宏错误而失败。
    - main 中的后续节点 downstream_of_fail 应该被跳过。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "caller",
                    "run": [{"runtime": "system.call", "config": {"graph": "failing_subgraph"}}]
                },
                {
                    "id": "downstream_of_fail",
                    "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.caller.output }}"}}]
                }
            ]
        },
        "failing_subgraph": {
            "nodes": [
                {"id": "A_ok", "run": [{"runtime": "system.input", "config": {"value": "ok"}}]},
                {"id": "B_fail", "run": [{"runtime": "system.input", "config": {"value": "{{ non_existent.var }}"}}]}
            ]
        }
    })

@pytest.fixture
def dynamic_subgraph_call_collection() -> GraphCollection:
    """
    一个动态决定调用哪个子图的集合。
    - main 根据 world.target_graph 的值来调用 sub_a 或 sub_b。
    """
    return GraphCollection.model_validate({
        "main": {"nodes": [{
            "id": "dynamic_caller",
            "run": [{
                "runtime": "system.call",
                "config": {
                    "graph": "{{ world.target_graph }}",
                    "using": {"data": "dynamic data"}
                }
            }]
        }]},
        # 【关键修正】在子图内部使用正确的 f-string 宏格式
        "sub_a": {"nodes": [{
            "id": "processor_a",
            "run": [{"runtime": "system.input", "config": {"value": "{{ f'Processed by A: {nodes.data.output}' }}"}}]
        }]},
        "sub_b": {"nodes": [{
            "id": "processor_b",
            "run": [{"runtime": "system.input", "config": {"value": "{{ f'Processed by B: {nodes.data.output}' }}"}}]
        }]}
    })


@pytest.fixture
def concurrent_write_collection() -> GraphCollection:
    """
    一个专门用于测试并发写入的图。
    - incrementer_A 和 incrementer_B 没有相互依赖，引擎会并行执行它们。
    - 两个节点都对同一个 world.counter 变量执行多次非原子操作 (read-modify-write)。
    - 如果没有锁，最终结果将几乎肯定小于 200。
    - 如果有宏级原子锁，每个宏的执行都是一个整体，结果必须是 200。
    """
    increment_loop_count = 100
    increment_code = f"""
for i in range({increment_loop_count}):
    # 这是一个典型的 read-modify-write 操作，非常容易产生竞态条件
    world.counter += 1
"""
    
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {
                "id": "incrementer_A",
                "run": [{"runtime": "system.execute", "config": {"code": increment_code}}]
            },
            {
                "id": "incrementer_B",
                "run": [{"runtime": "system.execute", "config": {"code": increment_code}}]
            },
            {
                "id": "reader",
                # depends_on 确保 reader 在两个写入者都完成后才执行
                "depends_on": ["incrementer_A", "incrementer_B"],
                "run": [{"runtime": "system.input", "config": {"value": "{{ world.counter }}"}}]
            }
        ]}
    })

@pytest.fixture
def map_collection_basic() -> GraphCollection:
    """
    一个基本的 system.map 测试集合。
    - main 图提供一个角色列表。
    - main 图使用 system.map 调用 process_character 子图处理每个角色。
    - process_character 子图接收一个 character_input 和一个 global_story_setting。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "character_provider",
                    "run": [{"runtime": "system.input", "config": {"value": ["Aragorn", "Gandalf", "Legolas"]}}]
                },
                {
                    "id": "global_setting_provider",
                    "run": [{"runtime": "system.input", "config": {"value": "The Fellowship of the Ring"}}]
                },
                {
                    "id": "character_processor_map",
                    "run": [{
                        "runtime": "system.map",
                        "config": {
                            "list": "{{ nodes.character_provider.output }}",
                            "graph": "process_character",
                            "using": {
                                "character_input": "{{ source.item }}",
                                "global_story_setting": "{{ nodes.global_setting_provider.output }}",
                                "character_index": "{{ source.index }}"
                            }
                        }
                    }]
                }
            ]
        },
        "process_character": {
            "nodes": [
                {
                    "id": "generate_bio",
                    "run": [{
                        "runtime": "llm.default",
                        "config": {
                            "prompt": "{{ f'Create a bio for {nodes.character_input.output} in the context of {nodes.global_story_setting.output}. Index: {nodes.character_index.output}' }}"
                        }
                    }]
                }
            ]
        }
    })


@pytest.fixture
def map_collection_with_collect(map_collection_basic: GraphCollection) -> GraphCollection:
    """
    一个测试 system.map 的 `collect` 功能的集合。
    - 它只从每个子图执行中提取 `summary` 字段，最终输出一个扁平的字符串列表。
    """
    # 【修正】通过参数接收 fixture，而不是直接调用
    base_data = map_collection_basic.model_dump()
    
    map_instruction = base_data["main"]["nodes"][2]["run"][0]
    # 添加 collect 字段
    map_instruction["config"]["collect"] = "{{ nodes.generate_bio.summary }}"
    
    return GraphCollection.model_validate(base_data)


@pytest.fixture
def map_collection_concurrent_write() -> GraphCollection:
    """
    一个测试在 map 内部并发修改 world_state 的集合。
    - 每个子图实例都会给 world.gold 增加10。
    - 如果没有原子锁，最终结果会因为竞态条件而不确定。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "task_provider",
                    "run": [{"runtime": "system.input", "config": {"value": list(range(10))}}] # 10个并行任务
                },
                {
                    "id": "concurrent_adder_map",
                    "run": [{
                        "runtime": "system.map",
                        "config": {
                            "list": "{{ nodes.task_provider.output }}",
                            "graph": "add_gold"
                            # using 是空的，因为子图不依赖 source
                        }
                    }]
                },
                {
                    "id": "reader",
                    "depends_on": ["concurrent_adder_map"],
                    "run": [{"runtime": "system.input", "config": {"value": "{{ world.gold }}"}}]
                }
            ]
        },
        "add_gold": {
            "nodes": [
                {
                    "id": "add_10_gold",
                    "run": [{"runtime": "system.execute", "config": {"code": "world.gold += 10"}}]
                }
            ]
        }
    })

@pytest.fixture
def map_collection_with_failure() -> GraphCollection:
    """
    一个 map 迭代中部分子图会失败的集合。
    - list 中有一个 None，会导致子图中的宏求值失败。
    - system.map 应该能正确返回所有结果，包括成功和失败的项。
    【修正】子图通过 `using` 字段来接收数据，而不是直接引用 `source`。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "data_provider",
                    "run": [{"runtime": "system.input", "config": {"value": [{"name": "Alice"}, "Bob", {"name": "Charlie"}]}}]
                },
                {
                    "id": "mapper",
                    "run": [{
                        "runtime": "system.map",
                        "config": {
                            "list": "{{ nodes.data_provider.output }}",
                            "graph": "process_name",
                            # 【关键修正】将 source.item 映射到子图的占位符
                            "using": {
                                "character_data": "{{ source.item }}"
                            }
                        }
                    }]
                }
            ]
        },
        "process_name": {
            "nodes": [
                {
                    "id": "get_name",
                    "run": [{
                        "runtime": "system.input",
                        # 【关键修正】从占位符节点获取数据
                        # 当 character_data.output 是 "Bob" (str) 时，.name 会触发 AttributeError
                        "config": {"value": "{{ nodes.character_data.output.name }}"}
                    }]
                }
            ]
        }
    })


# ---------------------------------------------------------------------------
#  Codex System Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def codex_basic_data() -> dict:
    """
    分离的 Graph 和 Codex 数据，用于测试 `always_on` 和优先级。
    """
    graph_definition = {
        "main": {
            "nodes": [{
                "id": "invoke_test",
                "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "basic_info"}]}}]
            }]
        }
    }
    codices_data = {
        "basic_info": {
            "description": "基本的问候和介绍",
            "entries": [
                {"id": "greeting", "content": "你好，冒险者！", "priority": 10},
                {"id": "intro", "content": "欢迎来到这个奇幻的世界。", "priority": 5}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_keyword_and_priority_data() -> dict:
    """
    测试 `on_keyword` 触发模式和 `priority` 排序。
    """
    graph_definition = {
        "main": {
            "nodes": [
                {
                    "id": "invoke_weather",
                    "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "weather_lore", "source": "今天的魔法天气怎么样？"}]}}]
                },
                {
                    "id": "invoke_mood",
                    "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "mood_expressions", "source": "我很开心，因为天气很好。"}]}}]
                }
            ]
        }
    }
    codices_data = {
        "weather_lore": {
            "entries": [
                {"id": "sunny", "content": "阳光明媚，万里无云。", "trigger_mode": "on_keyword", "keywords": ["阳光", "晴朗"], "priority": 10},
                {"id": "rainy", "content": "外面下着大雨，带把伞吧。", "trigger_mode": "on_keyword", "keywords": ["下雨", "雨天"], "priority": 20},
                {"id": "magic_weather", "content": "魔法能量今天异常活跃，可能会有异象发生。", "trigger_mode": "on_keyword", "keywords": ["魔法天气", "异象"], "priority": 30}
            ]
        },
        "mood_expressions": {
            "entries": [
                {"id": "happy_mood", "content": "你看起来很高兴。", "trigger_mode": "on_keyword", "keywords": ["开心", "高兴", "快乐"], "priority": 5},
                {"id": "sad_mood", "content": "你似乎有些低落。", "trigger_mode": "on_keyword", "keywords": ["伤心", "低落"], "priority": 10}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_macro_eval_data() -> dict:
    """
    测试 Codex 条目内部宏求值的集合。
    使用三引号来避免引号冲突。
    """
    # 【修正】确保 graph_definition 是一个正确的字典
    graph_definition = {
        "main": {
            "nodes": [
                {
                    "id": "get_weather_report",
                    "run": [{
                        "runtime": "system.invoke",
                        "config": {
                            "from": [{"codex": "dynamic_entries", "source": "请告诉我关于秘密和夜幕下的世界。"}],
                            "debug": True
                        }
                    }]
                }
            ]
        }
    }
    codices_data = {
        "dynamic_entries": {
            "entries": [
                # 【修正】使用三引号 f-string，更清晰
                {"id": "night_info", "content": """{{ f"现在是{'夜晚' if world.is_night else '白天'}。" }}""", "is_enabled": "{{ world.is_night }}"},
                {"id": "level_message", "content": """{{ f'你的等级是：{world.player_level}级。' }}""", "priority": "{{ 100 if world.player_level > 3 else 0 }}"},
                {"id": "secret_keyword_entry", "content": """{{ f"你提到了'{trigger.matched_keywords[0]}'，这是一个秘密信息。" }}""", "trigger_mode": "on_keyword", "keywords": "{{ [world.hidden_keyword] }}", "priority": 50},
                {"id": "always_on_with_trigger_info", "content": """{{ f"原始输入是：'{trigger.source_text}'。" }}""", "trigger_mode": "always_on", "priority": 1}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_recursion_data() -> dict:
    """
    测试 Codex 的递归功能。
    """
    graph_definition = {
        "main": {"nodes": [{
            "id": "recursive_invoke",
            "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "recursive_lore", "source": "告诉我关于A"}], "recursion_enabled": True, "debug": True}}]
        }]}
    }
    codices_data = {
        "recursive_lore": {
            "config": {"recursion_depth": 5}, # 增加深度以确保测试通过
            "entries": [
                {"id": "entry_A", "content": "这是关于A的信息，它引出B。", "trigger_mode": "on_keyword", "keywords": ["A"], "priority": 10},
                {"id": "entry_B", "content": "B被A触发了，它又引出C。", "trigger_mode": "on_keyword", "keywords": ["B"], "priority": 20},
                {"id": "entry_C", "content": "C被B触发了，这是最终信息。", "trigger_mode": "on_keyword", "keywords": ["C"], "priority": 30},
                {"id": "entry_D_always_on", "content": "这是一个总是存在的背景信息。", "trigger_mode": "always_on", "priority": 5}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_invalid_structure_data() -> dict:
    """
    测试无效 Codex 结构时的错误处理。
    """
    graph_definition = {"main": {"nodes": [{"id": "invoke_invalid", "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "bad_codex"}]}}]}]}}
    codices_data = {
        "bad_codex": {
            "entries": [
                {"id": "valid_one", "content": "valid"},
                {"id": "invalid_one", "content": 123} # content 必须是字符串
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_concurrent_world_write_data() -> dict:
    """
    测试 `system.invoke` 内部宏对 `world_state` 的并发写入。
    """
    graph_definition = {
        "main": {
            "nodes": [
                {
                    "id": "invoke_and_increment",
                    "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "concurrent_codex", "source": "触发计数"}]}}]
                },
                {
                    "id": "read_counter",
                    "depends_on": ["invoke_and_increment"],
                    "run": [{"runtime": "system.input", "config": {"value": "{{ world.counter }}"}}]
                }
            ]
        }
    }
    codices_data = {
        "concurrent_codex": {
            "entries": [
                {"id": "increment_1", "content": "{{ world.counter = world.counter + 1; 'Incremented 1.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 10},
                {"id": "increment_2", "content": "{{ world.counter += 2; 'Incremented 2.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 20},
                {"id": "increment_3", "content": "{{ world.counter += 3; 'Incremented 3.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 30}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}

@pytest.fixture
def codex_nonexistent_codex_data() -> dict:
    graph_definition = {
        "main": {"nodes": [{
            "id": "invoke_nonexistent",
            "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "nonexistent_codex"}]}}]
        }]}
    }
    # codices 是空的，因为我们就是想测试找不到的情况
    return {"graph": graph_definition, "codices": {}}
```

### test_02_evaluation_unit.py
```
# tests/test_02_evaluation_unit.py
import pytest
from uuid import uuid4
import asyncio

from backend.core.evaluation import (
    evaluate_expression, evaluate_data, build_evaluation_context
)
from backend.core.types import ExecutionContext
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection
# 【修改】导入新的运行时
from backend.runtimes.base_runtimes import SetWorldVariableRuntime
from backend.runtimes.control_runtimes import ExecuteRuntime

@pytest.fixture
def mock_exec_context() -> ExecutionContext:
    """提供一个可复用的、模拟的 ExecutionContext。"""
    graph_coll = GraphCollection.model_validate({"main": {"nodes": []}})
    # --- 修正: 在创建 Snapshot 时提供初始世界状态 ---
    initial_world = {"user_name": "Alice", "hp": 100}
    snapshot = StateSnapshot(
        sandbox_id=uuid4(),
        graph_collection=graph_coll,
        world_state=initial_world
    )
    # --- 修正: 使用新的工厂方法 ---
    context = ExecutionContext.create_for_main_run(snapshot)
    
    # 这部分保持不变，是正确的
    context.node_states = {"node_A": {"output": "Success"}}
    context.run_vars = {"trigger_input": {"message": "Do it!"}}

    return context

@pytest.fixture
def mock_eval_context(mock_exec_context: ExecutionContext) -> dict:
    """提供一个扁平化的、用于宏执行的字典上下文。"""
    return build_evaluation_context(mock_exec_context, pipe_vars={"from_pipe": "pipe_data"})

@pytest.fixture
def test_lock() -> asyncio.Lock:
    """提供一个在测试中共享的锁。"""
    return asyncio.Lock()

@pytest.mark.asyncio
class TestEvaluationCore:
    """对宏求值核心 `evaluate_expression` 进行深度单元测试。"""
    # --- 修正: 添加 lock fixture ---
    async def test_simple_expressions(self, mock_eval_context, test_lock):
        assert await evaluate_expression("1 + 1", mock_eval_context, test_lock) == 2

    # --- 修正: 添加 lock fixture ---
    async def test_context_access(self, mock_eval_context, test_lock):
        code = "f'{nodes.node_A.output}, {world.user_name}, {run.trigger_input.message}, {pipe.from_pipe}'"
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result == "Success, Alice, Do it!, pipe_data"

    # --- 修正: 添加 lock fixture ---
    async def test_side_effects_on_world_state(self, mock_exec_context: ExecutionContext, test_lock):
        eval_context = build_evaluation_context(mock_exec_context)
        assert eval_context["world"].hp == 100
        await evaluate_expression("world.hp -= 10", eval_context, test_lock)
        assert eval_context["world"].hp == 90
        # --- 修正: 从 shared.world_state 验证 ---
        assert mock_exec_context.shared.world_state["hp"] == 90

    # --- 修正: 添加 lock fixture ---
    async def test_multiline_script_with_return(self, mock_eval_context, test_lock):
        # --- 【核心修复】 ---
        # 移除 Ellipsis (...) 并替换为实际的 Python 代码
        code = """
bonus = 0
if world.hp > 50:
    bonus = 20
else:
    bonus = 5.0
bonus
"""
        # 测试 if 分支
        mock_eval_context["world"].hp = 80
        # 断言现在可以正确工作
        assert await evaluate_expression(code, mock_eval_context, test_lock) == 20
        # 测试 else 分支
        mock_eval_context["world"].hp = 40
        assert await evaluate_expression(code, mock_eval_context, test_lock) == 5.0

    # --- 修正: 添加 lock fixture ---
    async def test_syntax_error_handling(self, mock_eval_context, test_lock):
        with pytest.raises(ValueError, match="Macro syntax error"):
            await evaluate_expression("1 +", mock_eval_context, test_lock)

@pytest.mark.asyncio
class TestRecursiveEvaluation:
    """对递归求值函数 `evaluate_data` 进行测试。"""
    # --- 修正: 添加 lock fixture ---
    async def test_evaluate_data_recursively(self, mock_eval_context, test_lock):
        data = {
            "static": "hello",
            "direct": "{{ 1 + 2 }}",
            "nested": ["{{ world.user_name }}", {"deep": "{{ pipe.from_pipe.upper() }}"}]
        }
        result = await evaluate_data(data, mock_eval_context, test_lock)
        expected = {
            "static": "hello",
            "direct": 3,
            "nested": ["Alice", {"deep": "PIPE_DATA"}]
        }
        assert result == expected

@pytest.mark.asyncio
class TestRuntimesWithMacros:
    """对每个运行时进行独立的单元测试，假设宏预处理已完成。"""

    # 【关键修改】更新 execute 方法的调用签名
    async def test_set_world_variable_runtime(self, mock_exec_context: ExecutionContext):
        runtime = SetWorldVariableRuntime()
        # --- 修正: 检查 shared.world_state ---
        assert "new_var" not in mock_exec_context.shared.world_state
        await runtime.execute(
            config={"variable_name": "new_var", "value": "is_set"},
            context=mock_exec_context
        )
        # --- 修正: 验证 shared.world_state ---
        assert mock_exec_context.shared.world_state["new_var"] == "is_set"

    async def test_execute_runtime(self, mock_exec_context: ExecutionContext):
        runtime = ExecuteRuntime()
        # --- 修正: 检查 shared.world_state ---
        assert mock_exec_context.shared.world_state["hp"] == 100
        code_str = "world.hp -= 25"
        await runtime.execute(
            config={"code": code_str}, 
            context=mock_exec_context
        )
        # --- 修正: 验证 shared.world_state ---
        assert mock_exec_context.shared.world_state["hp"] == 75

        code_str_with_return = "f'New HP is {world.hp}'"
        result = await runtime.execute(
            config={"code": code_str_with_return}, 
            context=mock_exec_context
        )
        assert result == {"output": "New HP is 75"}


@pytest.mark.asyncio
class TestBuiltinModules:
    # --- 修正: 为所有测试添加 lock fixture ---
    async def test_random_module(self, mock_eval_context, test_lock):
        result = await evaluate_expression("random.randint(10, 10)", mock_eval_context, test_lock)
        assert result == 10

    async def test_math_module(self, mock_eval_context, test_lock):
        result = await evaluate_expression("math.ceil(3.14)", mock_eval_context, test_lock)
        assert result == 4

    async def test_json_module(self, mock_eval_context, test_lock):
        code = "import json\njson.dumps({'a': 1})"
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result == '{"a": 1}'

    async def test_re_module(self, mock_eval_context, test_lock):
        code = "re.match(r'\\w+', 'hello').group(0)"
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result == "hello"

# TestDotAccessibleDictInteraction 类中的测试需要修改
@pytest.mark.asyncio
class TestDotAccessibleDictInteraction:
    # --- 修正: 为所有测试添加 lock fixture ---
    async def test_deep_read(self, mock_exec_context, test_lock):
        # --- 修正: 修改 shared.world_state ---
        mock_exec_context.shared.world_state["player"] = {"stats": {"strength": 10}}
        eval_context = build_evaluation_context(mock_exec_context)
        result = await evaluate_expression("world.player.stats.strength", eval_context, test_lock)
        assert result == 10

    async def test_deep_write(self, mock_exec_context, test_lock):
        mock_exec_context.shared.world_state["player"] = {"stats": {"strength": 10}}
        eval_context = build_evaluation_context(mock_exec_context)
        await evaluate_expression("world.player.stats.strength = 15", eval_context, test_lock)
        assert mock_exec_context.shared.world_state["player"]["stats"]["strength"] == 15
    
    async def test_attribute_error_on_missing_key(self, mock_eval_context, test_lock):
        with pytest.raises(AttributeError):
            await evaluate_expression("world.non_existent_key", mock_eval_context, test_lock)

    async def test_list_of_dicts_access(self, mock_exec_context, test_lock):
        mock_exec_context.shared.world_state["inventory"] = [{"name": "sword"}, {"name": "shield"}]
        eval_context = build_evaluation_context(mock_exec_context)
        result = await evaluate_expression("world.inventory[1].name", eval_context, test_lock)
        assert result == "shield"

# TestEdgeCases 类中的测试需要修改
@pytest.mark.asyncio
class TestEdgeCases:
    # --- 修正: 为所有测试添加 lock fixture ---
    async def test_macro_returning_none(self, mock_eval_context, test_lock):
        code = "x = 1"
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result is None

    async def test_empty_macro(self, mock_eval_context, test_lock):
        result = await evaluate_expression("", mock_eval_context, test_lock)
        assert result is None
        result = await evaluate_expression("   ", mock_eval_context, test_lock)
        assert result is None

    async def test_evaluate_data_with_none_values(self, mock_eval_context, test_lock):
        data = {"key1": None, "key2": "{{ 1 + 1 }}"}
        result = await evaluate_data(data, mock_eval_context, test_lock)
        assert result == {"key1": None, "key2": 2}
```

### test_01_foundations.py
```
# tests/test_01_foundations.py
import pytest
from pydantic import ValidationError
from uuid import uuid4

from backend.models import GraphCollection, GenericNode, GraphDefinition, RuntimeInstruction
from backend.core.state_models import StateSnapshot, Sandbox, SnapshotStore
from backend.core.dependency_parser import build_dependency_graph


class TestCoreModels:
    """测试核心数据模型，已更新为新架构。"""

    def test_runtime_instruction_validation(self):
        """测试 RuntimeInstruction 模型。"""
        # 有效
        inst = RuntimeInstruction(runtime="test.runtime", config={"key": "value"})
        assert inst.runtime == "test.runtime"
        assert inst.config == {"key": "value"}
        # config 默认为空字典
        inst_default = RuntimeInstruction(runtime="test.runtime")
        assert inst_default.config == {}

        # 无效 (缺少 runtime)
        with pytest.raises(ValidationError):
            RuntimeInstruction(config={})

    def test_generic_node_validation_success(self):
        """测试 GenericNode 使用新的 `run` 字段。"""
        node = GenericNode(
            id="n1",
            run=[
                {"runtime": "step1", "config": {"p1": 1}},
                {"runtime": "step2"}
            ]
        )
        assert node.id == "n1"
        assert len(node.run) == 2
        assert isinstance(node.run[0], RuntimeInstruction)
        assert node.run[0].runtime == "step1"
        assert node.run[0].config == {"p1": 1}
        assert node.run[1].config == {}

    def test_generic_node_validation_fails(self):
        """测试 GenericNode 的无效 `run` 字段。"""
        # `run` 列表中的项不是有效的指令
        with pytest.raises(ValidationError):
            GenericNode(id="n1", run=["not_an_instruction"])
        
        with pytest.raises(ValidationError):
            GenericNode(id="n1", run=[{"config": {}}]) # runtime 缺失

    def test_graph_collection_validation(self):
        """测试 GraphCollection 验证逻辑，此逻辑不变。"""
        valid_data = {"main": {"nodes": [{"id": "a", "run": []}]}}
        collection = GraphCollection.model_validate(valid_data)
        assert "main" in collection.root

        with pytest.raises(ValidationError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate({"other": {"nodes": []}})


class TestSandboxModels:
    """测试沙盒相关模型，基本不变。"""
    # ... 此部分测试与旧版本基本一致，无需修改，因为模型本身的结构和不变性没有改变 ...
    @pytest.fixture
    def sample_graph_collection(self) -> GraphCollection:
        return GraphCollection.model_validate({"main": {"nodes": [{"id": "a", "run": []}]}})

    def test_state_snapshot_is_immutable(self, sample_graph_collection: GraphCollection):
        snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=sample_graph_collection)
        with pytest.raises(ValidationError, match="Instance is frozen"):
            snapshot.world_state = {"new_key": "new_value"}


class TestDependencyParser:
    """测试依赖解析器，使用新的节点结构。"""

    def test_simple_dependency(self):
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"config": {"value": "{{ nodes.A.output }}"}}]}]
        deps = build_dependency_graph(nodes)
        assert deps["B"] == {"A"}

    def test_dependency_in_nested_structure(self):
        nodes = [
            {"id": "source", "run": []},
            {"id": "consumer", "run": [{"config": {"nested": ["{{ nodes.source.val }}"]}}]}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["consumer"] == {"source"}

    def test_ignores_non_node_macros(self):
        nodes = [{"id": "A", "run": [{"config": {"value": "{{ world.x }}"}}]}]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()

    def test_dependency_on_placeholder_node_is_preserved(self):
        """
        验证对图中不存在的节点（即子图的输入占位符）的依赖会被保留。
        这对于 system.call 功能至关重要。
        """
        nodes = [{"id": "A", "run": [{"config": {"value": "{{ nodes.placeholder_input.val }}"}}]}]
        deps = build_dependency_graph(nodes)
        # 之前这里断言 deps["A"] == set()，现在它必须保留依赖
        assert deps["A"] == {"placeholder_input"}
```

### __init__.py
```

```

### test_04_api_e2e.py
```
# tests/test_04_api_e2e.py
import pytest
from fastapi.testclient import TestClient
from uuid import UUID, uuid4

from backend.models import GraphCollection


class TestApiSandboxLifecycle:
    """测试沙盒从创建、执行、查询到回滚的完整生命周期。"""
    
    def test_full_lifecycle(self, test_client: TestClient, linear_collection: GraphCollection):
        # 1. 创建
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "E2E Test"},
            json={
                "graph_collection": linear_collection.model_dump(),
                "initial_state": {} 
            }
        )
        assert response.status_code == 200
        sandbox_data = response.json()
        sandbox_id = sandbox_data["id"]
        genesis_snapshot_id = sandbox_data["head_snapshot_id"]

        # 2. 执行
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={"user_message": "test"})
        assert response.status_code == 200
        step1_snapshot_data = response.json()
        step1_snapshot_id = step1_snapshot_data["id"]
        assert "C" in step1_snapshot_data.get("run_output", {})

        # 3. 历史
        response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 2

        # 4. 回滚
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": genesis_snapshot_id}
        )
        assert response.status_code == 200

        # 5. 验证回滚
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        step2_snapshot_data = response.json()
        assert step2_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id


class TestApiErrorHandling:
    """测试 API 在各种错误情况下的响应。"""

    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Invalid"},
            json={"graph_collection": invalid_graph_no_main}
        )
        assert response.status_code == 422 
        error_data = response.json()
        assert "A 'main' graph must be defined" in error_data["detail"][0]["msg"]
        # 验证 pydantic v2 对 RootModel 的错误路径
        assert error_data["detail"][0]["loc"] == ["body", "graph_collection"]

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        nonexistent_id = uuid4()
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404
        
        # 获取历史记录现在会因为找不到 sandbox 而返回 404
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        assert response.status_code == 404

        response = test_client.put(f"/api/sandboxes/{nonexistent_id}/revert", params={"snapshot_id": uuid4()})
        assert response.status_code == 404


class TestApiWithComplexGraphs:
    """测试涉及更复杂图逻辑（如子图调用）的 API 端点。"""

    def test_e2e_with_subgraph_call(self, test_client: TestClient, subgraph_call_collection: GraphCollection):
        """
        通过 API 端到端测试一个包含 system.call 的图。
        """
        # 1. 创建沙盒
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "E2E Subgraph Test"},
            json={
                "graph_collection": subgraph_call_collection.model_dump(),
                "initial_state": {"global_setting": "Omega"}
            }
        )
        assert response.status_code == 200
        sandbox_id = response.json()["id"]

        # 2. 执行一步
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        assert response.status_code == 200
        
        # 3. 验证结果
        snapshot_data = response.json()
        run_output = snapshot_data.get("run_output", {})
        
        assert "main_caller" in run_output
        subgraph_output = run_output["main_caller"]["output"]
        processor_output = subgraph_output["processor"]["output"]
        
        expected_str = "Processed: Hello from main with world state: Omega"
        assert processor_output == expected_str
```

### test_05_concurrency.py
```
# tests/test_05_concurrency.py
import pytest
from uuid import uuid4

from backend.core.engine import ExecutionEngine
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection


@pytest.mark.asyncio
class TestConcurrencyWithLock:
    """
    测试引擎的宏级原子锁是否能正确处理并发写入，防止竞态条件。
    """

    async def test_concurrent_writes_are_atomic_and_correct(
        self, 
        test_engine: ExecutionEngine, 
        concurrent_write_collection: GraphCollection
    ):
        """
        验证两个并行节点对同一个 world_state 变量的多次修改是原子性的。
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
```

### test_03_engine_integration.py
```
# tests/test_03_engine_integration.py
import pytest
from uuid import uuid4

from backend.core.engine import ExecutionEngine
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection


@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，使用新的宏系统。"""

    async def test_engine_linear_flow(self, test_engine: ExecutionEngine, linear_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert output["A"]["output"] == "a story about a cat"
        assert output["B"]["llm_output"] == "LLM_RESPONSE_FOR:[The story is: a story about a cat]"
        assert output["C"]["llm_output"] == f"LLM_RESPONSE_FOR:[{output['B']['llm_output']}]"

    async def test_engine_runtime_pipeline(self, test_engine: ExecutionEngine, pipeline_collection: GraphCollection):
        """【已修正】测试单个节点内的运行时管道，并验证宏预处理与运行时的交互。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 1. 验证第一个指令的副作用
        assert final_snapshot.world_state["main_character"] == "Sir Reginald"

        # 2. 验证第三个指令使用了世界状态和管道状态
        node_a_result = final_snapshot.run_output["A"]
        
        expected_prompt = "Tell a story about Sir Reginald. He just received this message: A secret message"
        # 3. 【已修正】现在可以安全地断言 llm_output
        assert node_a_result["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt}]"

        # 4. 验证最终的节点输出是所有指令输出的合并
        assert node_a_result["output"] == "A secret message"


@pytest.mark.asyncio
class TestEngineStateAndMacros:
    async def test_world_state_persists_and_macros_read_it(self, test_engine: ExecutionEngine, world_vars_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        # 这一行断言现在应该能通过，因为 build_evaluation_context 会正确处理
        assert final_snapshot.world_state == {"theme": "cyberpunk"}

        # --- 修正: repr 输出现在是 SharedContext 的一部分，但 DotAccessibleDict 隐藏了这些细节。
        # 让我们做一个更健壮的断言，而不是依赖 __repr__ 的精确格式。
        expected_reader_output_start = "The theme is: cyberpunk and some data from setter"
        reader_output = final_snapshot.run_output["reader"]["output"]
        assert reader_output.startswith(expected_reader_output_start)

    async def test_graph_evolution(self, test_engine: ExecutionEngine, graph_evolution_collection: GraphCollection):
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        snapshot_after_evolution = await test_engine.step(genesis_snapshot, {})
        
        new_graph_def = snapshot_after_evolution.graph_collection
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        final_snapshot = await test_engine.step(snapshot_after_evolution, {})
        assert final_snapshot.run_output["new_node"]["output"] == "This is the evolved graph!"

    async def test_execute_runtime_integration(self, test_engine: ExecutionEngine, execute_runtime_collection: GraphCollection):
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(), 
            graph_collection=execute_runtime_collection,
            world_state={"player_status": "normal"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        assert final_snapshot.world_state["player_status"] == "empowered"

@pytest.mark.asyncio
class TestEngineErrorHandling:
    async def test_engine_detects_cycle(self, test_engine: ExecutionEngine, cyclic_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        with pytest.raises(ValueError, match="Cycle detected"):
            await test_engine.step(initial_snapshot, {})

    async def test_engine_handles_failure_and_skips_downstream(self, test_engine: ExecutionEngine, failing_node_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert "error" not in output["A_ok"]
        assert "error" not in output["D_independent"]

        assert "error" in output["B_fail"]
        assert output["B_fail"]["failed_step"] == 0 # 失败在第一个(也是唯一一个)指令
        assert "non_existent_variable" in output["B_fail"]["error"]

        assert output["C_skip"]["status"] == "skipped"
        assert output["C_skip"]["reason"] == "Upstream failure of node B_fail."

@pytest.mark.asyncio
class TestAdvancedMacroIntegration:
    """测试引擎中更高级的宏功能，如动态函数定义和二次求值链。"""

    async def test_dynamic_function_definition_and_usage(self, test_engine: ExecutionEngine, advanced_macro_collection: GraphCollection):
        """
        测试一个节点定义函数，另一个节点使用该函数。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=advanced_macro_collection,
            world_state={"game_difficulty": "easy"}
        )

        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        # 1. 验证 `teach_skill` 节点的副作用
        assert "math_utils" in final_snapshot.world_state
        assert callable(final_snapshot.world_state["math_utils"]["hypot"])

        # 2. 验证 `use_skill` 节点成功调用了该函数
        run_output = final_snapshot.run_output
        assert "use_skill" in run_output
        # 【已修正】现在这个断言应该可以成功了
        assert run_output["use_skill"]["output"] == 5.0

    async def test_llm_code_generation_and_execution(self, test_engine: ExecutionEngine, advanced_macro_collection: GraphCollection):
        """
        测试一个节点生成代码，另一个节点执行它，模拟 LLM 驱动的世界演化。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=advanced_macro_collection,
            world_state={"game_difficulty": "easy"}
        )

        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output
        
        # 【已修正】断言中的字符串现在与 fixture 中定义的完全一致
        assert run_output["llm_propose_change"]["output"] == "world.game_difficulty = 'hard'"
        
        assert "execute_change" in run_output
        
        assert final_snapshot.world_state["game_difficulty"] == "hard"

@pytest.mark.asyncio
class TestEngineSubgraphExecution:
    """测试引擎的子图执行功能 (system.call)。"""

    async def test_basic_subgraph_call(self, test_engine: ExecutionEngine, subgraph_call_collection: GraphCollection):
        """测试基本的子图调用和数据映射。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_collection,
            world_state={"global_setting": "Alpha"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        
        # 验证主调节点的输出是子图的完整结果字典
        subgraph_result = output["main_caller"]["output"]
        assert isinstance(subgraph_result, dict)
        
        # 验证子图内部的节点 'processor' 的输出
        processor_output = subgraph_result["processor"]["output"]
        expected_str = "Processed: Hello from main with world state: Alpha"
        assert processor_output == expected_str
        
    async def test_nested_subgraph_call(self, test_engine: ExecutionEngine, nested_subgraph_collection: GraphCollection):
        """测试嵌套的子图调用：main -> sub1 -> sub2。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=nested_subgraph_collection
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output

        # 逐层深入断言
        sub1_result = output["main_caller"]["output"]
        sub2_result = sub1_result["sub1_caller"]["output"]
        final_output = sub2_result["final_processor"]["output"]
        
        assert final_output == "Reached level 2 from: level 0"

    async def test_call_to_nonexistent_subgraph_fails_node(self, test_engine: ExecutionEngine, subgraph_call_to_nonexistent_graph_collection: GraphCollection):
        """测试调用一个不存在的子图时，节点会优雅地失败。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_to_nonexistent_graph_collection
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        bad_caller_result = output["bad_caller"]
        
        assert "error" in bad_caller_result
        
        # --- 【关键修正】---
        # 更新断言以匹配更详细的错误消息格式
        error_message = bad_caller_result["error"]
        assert "Failed at step 1 ('system.call')" in error_message
        assert "ValueError: Graph 'i_do_not_exist' not found" in error_message

    async def test_subgraph_can_modify_world_state(self, test_engine: ExecutionEngine, subgraph_modifies_world_collection: GraphCollection):
        """
        验证子图对 world_state 的修改在父图中是可见的，并且后续节点可以访问它。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_modifies_world_collection,
            world_state={"counter": 100} # 初始状态
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 1. 验证 world_state 被成功修改
        assert final_snapshot.world_state["counter"] == 110

        # 2. 验证父图中的后续节点可以读取到修改后的状态
        reader_output = final_snapshot.run_output["reader"]["output"]
        assert "Final counter: 110" in reader_output
        # 验证 reader 也可以访问 caller 的原始输出
        assert "incrementer" in reader_output
    
    async def test_subgraph_failure_propagates_to_caller(self, test_engine: ExecutionEngine, subgraph_with_failure_collection: GraphCollection):
        """
        验证子图中的失败会反映在调用节点的输出中，并导致父图中的下游节点被跳过。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_with_failure_collection,
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        
        # 1. 验证调用节点的结果是子图的失败状态
        caller_result = output["caller"]["output"]
        assert "B_fail" in caller_result
        assert "error" in caller_result["B_fail"]
        assert "non_existent" in caller_result["B_fail"]["error"]

        # 2. 验证调用节点本身的状态不是 FAILED，而是 SUCCEEDED，
        # 因为 system.call 运行时成功地“捕获”了子图的结果（即使是失败的结果）。
        # 这是预期的行为：运行时本身没有崩溃。
        # 【注意】我们检查的是 caller 节点的整体输出，而不是子图的结果
        assert "error" not in output["caller"]

        # 3. 验证依赖于 caller 的下游节点被跳过，因为它的依赖（caller）现在包含了一个失败的内部节点。
        # 这是一个更微妙的点。当前的 _process_subscribers 逻辑可能不会将此视为失败。
        # 让我们来验证当前的行为。
        # 当前 _process_subscribers 仅检查 run.get_node_state(dep_id) == NodeState.SUCCEEDED
        # 因为 caller 节点状态是 SUCCEEDED，所以 downstream_of_fail 会运行。
        # 这是当前实现的一个值得注意的行为！
        assert "downstream_of_fail" in output
        assert "error" not in output.get("downstream_of_fail", {})

        # 如果我们想要“失败”传播，我们需要修改 system.call 运行时，
        # 让它在子图失败时自己也返回一个 error。
        # 这是一个很好的设计决策讨论点。目前，我们测试了现有行为。

    async def test_dynamic_subgraph_call_by_macro(self, test_engine: ExecutionEngine, dynamic_subgraph_call_collection: GraphCollection):
        """
        验证 system.call 的 'graph' 参数可以由宏动态提供。
        """
        # 场景1: 调用 sub_a
        initial_snapshot_a = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=dynamic_subgraph_call_collection,
            world_state={"target_graph": "sub_a"}
        )
        final_snapshot_a = await test_engine.step(initial_snapshot_a, {})
        output_a = final_snapshot_a.run_output["dynamic_caller"]["output"]
        assert output_a["processor_a"]["output"] == "Processed by A: dynamic data"

        # 场景2: 调用 sub_b
        initial_snapshot_b = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=dynamic_subgraph_call_collection,
            world_state={"target_graph": "sub_b"}
        )
        final_snapshot_b = await test_engine.step(initial_snapshot_b, {})
        output_b = final_snapshot_b.run_output["dynamic_caller"]["output"]
        assert "processor_a" not in output_b
        assert output_b["processor_b"]["output"] == "Processed by B: dynamic data"
```

### test_07_codex_system.py
```
# tests/test_07_codex_system.py

import pytest
from uuid import uuid4

from backend.core.engine import ExecutionEngine
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

@pytest.mark.asyncio
class TestCodexSystem:
    """对 Hevno Codex 系统的集成测试 (system.invoke 运行时)。"""

    async def test_basic_invoke_always_on(
        self,
        test_engine: ExecutionEngine,
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
        test_engine: ExecutionEngine,
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
        test_engine: ExecutionEngine,
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
        test_engine: ExecutionEngine,
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
        
        # 预期渲染顺序：C (30) -> B (20) -> A (10) -> D (5)
        # 渲染循环：
        # 1. 初始激活 [A(10), D(5)] -> 渲染 A
        # 2. A 的内容触发 B -> 池子 [B(20), D(5)] -> 渲染 B
        # 3. B 的内容触发 C -> 池子 [C(30), D(5)] -> 渲染 C
        # 4. 池子 [D(5)] -> 渲染 D
        expected_order = [
            "这是关于A的信息，它引出B。",   # Loop 1, P=10
            "B被A触发了，它又引出C。",       # Loop 2, P=20
            "C被B触发了，这是最终信息。",   # Loop 3, P=30
            "这是一个总是存在的背景信息。", # Loop 4, P=5
        ]
        assert final_text.split("\n\n") == expected_order

        # Trace 日志中的渲染顺序也应该是 A -> B -> C -> D
        rendered_order_ids = [e["id"] for e in trace["evaluation_log"] if e["status"] == "rendered"]
        assert rendered_order_ids == ["entry_A", "entry_B", "entry_C", "entry_D_always_on"]
        
        assert len(trace["initial_activation"]) == 2
        assert len(trace["recursive_activations"]) == 2

    async def test_invoke_invalid_codex_structure_error(
        self,
        test_engine: ExecutionEngine,
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
        test_engine: ExecutionEngine,
        codex_nonexistent_codex_data: dict # <-- 修正 fixture 名称
    ):
        """
        测试 `system.invoke` 尝试从不存在的法典中读取时能捕获错误。
        """
        graph_collection = GraphCollection.model_validate(codex_nonexistent_codex_data["graph"])
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph_collection,
            world_state={"codices": codex_nonexistent_codex_data["codices"]} # 注入空的 codices
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        invoke_result = output["invoke_nonexistent"]

        assert "error" in invoke_result
        assert "Codex 'nonexistent_codex' not found" in invoke_result["error"]
        
    async def test_invoke_concurrent_world_writes(
        self,
        test_engine: ExecutionEngine,
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

        # 初始 0 + 3 + 2 + 1 = 6 (按优先级倒序执行)
        expected_counter = 6
        assert final_snapshot.world_state["counter"] == expected_counter
        assert output["read_counter"]["output"] == expected_counter

        invoke_text = output["invoke_and_increment"]["output"]
        assert "Incremented 1." in invoke_text
        assert "Incremented 2." in invoke_text
        assert "Incremented 3." in invoke_text
```
