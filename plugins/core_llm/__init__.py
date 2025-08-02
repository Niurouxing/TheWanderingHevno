# plugins/core_llm/__init__.py
import logging
from backend.core.contracts import Container, HookManager
from .service import LLMService, MockLLMService
from .manager import KeyPoolManager, CredentialManager
from .registry import provider_registry
from .runtime import LLMRuntime
# (如果需要报告器，也在这里导入)
# from .reporters import LLMProviderReporter

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_llm_service(container: Container) -> LLMService:
    """
    这个工厂函数封装了创建 LLMService 的复杂逻辑。
    它不依赖任何环境变量，所有配置都应来自容器或默认值。
    """
    # 注意：这里我们硬编码了非调试模式。未来可以从配置服务获取。
    # is_debug_mode = container.resolve("config_service").get("llm_debug_mode", False)
    
    # 实例化所有 provider
    provider_registry.instantiate_all()
    
    # 创建内部依赖
    cred_manager = CredentialManager()
    key_manager = KeyPoolManager(credential_manager=cred_manager)
    
    for name, info in provider_registry.get_all_provider_info().items():
        key_manager.register_provider(name, info.key_env_var)

    return LLMService(
        key_manager=key_manager,
        provider_registry=provider_registry,
        max_retries=3
    )

# --- 钩子实现 ---
async def register_llm_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的运行时。"""
    runtimes["llm.default"] = LLMRuntime
    logger.debug("Runtime 'llm.default' provided to runtime registry.")
    return runtimes

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-llm] 插件...")

    # 1. 注册服务到 DI 容器
    container.register("llm_service", _create_llm_service)
    container.register("mock_llm_service", lambda: MockLLMService()) # 同样注册 Mock 服务
    logger.debug("服务 'llm_service' 和 'mock_llm_service' 已注册。")

    # 2. 注册钩子实现
    # 我们将通过钩子来注册运行时，而不是直接依赖 runtime_registry
    hook_manager.add_implementation("collect_runtimes", register_llm_runtime, plugin_name="core-llm")
    logger.debug("钩子实现 'collect_runtimes' 已注册。")
    
    logger.info("插件 [core-llm] 注册成功。")