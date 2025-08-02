# Directory: backend

### __init__.py
```

```

### container.py
```
# backend/container.py

import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class Container:
    """一个简单的、通用的依赖注入容器。"""
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}
        self._instances: Dict[str, Any] = {}
        # 注意：此处日志可能还未完全配置，但可以安全调用
        # logger.info("DI Container initialized.")

    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        """
        注册一个服务工厂。

        :param name: 服务的唯一名称。
        :param factory: 一个创建服务实例的函数 (可以无参，或接收 container 实例)。
        :param singleton: 如果为 True，服务只会被创建一次（单例）。
        """
        if name in self._factories:
            logger.warning(f"Overwriting service registration for '{name}'")
        self._factories[name] = factory
        self._singletons[name] = singleton

    def resolve(self, name: str) -> Any:
        """
        解析（获取）一个服务实例。

        如果服务是单例且已被创建，则返回现有实例。
        否则，调用其工厂函数创建新实例。
        """
        if name in self._instances and self._singletons.get(name, True):
            return self._instances[name]

        if name not in self._factories:
            raise ValueError(f"Service '{name}' not found in container.")

        factory = self._factories[name]
        
        try:
            # 尝试将容器本身作为依赖注入到工厂中
            instance = factory(self)
        except TypeError:
            # 如果工厂不接受参数，则直接调用
            instance = factory()

        logger.debug(f"Resolved service '{name}'. Singleton: {self._singletons.get(name, True)}")

        if self._singletons.get(name, True):
            self._instances[name] = instance
        
        return instance
```

### app.py
```
# backend/app.py

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.loader import PluginLoader

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    container = Container()
    hook_manager = HookManager()

    # 1. 注册平台核心服务
    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)

    # 2. 加载插件（插件此时仅注册工厂和同步钩子）
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()
    
    logger = logging.getLogger(__name__)
    logger.info("--- FastAPI Application Assembly ---")

    # 3. 将核心服务附加到 app.state，以便依赖注入函数可以访问
    app.state.container = container
    # hook_manager 不再需要直接附加，因为可以通过容器获取

    # 4. 【关键】触发异步服务初始化钩子
    #    这会填充 Auditor, RuntimeRegistry 等
    logger.info("Triggering 'services_post_register' for async initializations...")
    await hook_manager.trigger('services_post_register', container=container)
    logger.info("Async service initialization complete.")

    # 5. 【关键】平台核心负责收集并装配 API 路由
    logger.info("Collecting API routers from all plugins...")
    # 通过钩子收集所有由插件提供的 APIRouter 实例
    routers_to_add: list[APIRouter] = await hook_manager.filter("collect_api_routers", [])
    
    if routers_to_add:
        logger.info(f"Collected {len(routers_to_add)} router(s). Adding to application...")
        for router in routers_to_add:
            app.include_router(router)
            logger.debug(f"Added router: prefix='{router.prefix}', tags={router.tags}")
    else:
        logger.warning("No API routers were collected from plugins.")
    
    # 6. 触发最终启动完成钩子
    await hook_manager.trigger('app_startup_complete', app=app, container=container)
    
    logger.info("--- Hevno Engine Ready ---")
    yield
    # --- 关闭阶段 ---
    logger.info("--- Hevno Engine Shutting Down ---")
    await hook_manager.trigger('app_shutdown', app=app)


def create_app() -> FastAPI:
    """应用工厂函数"""
    app = FastAPI(
        title="Hevno Engine (Plugin Architecture)",
        version="1.2.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
```

### main.py
```
# backend/main.py

import uvicorn
import os

from backend.app import create_app

# 调用工厂函数来获取完全配置好的应用实例
app = create_app()

@app.get("/")
def read_root():
    return {"message": "Hevno Engine (Plugin Architecture) is running!"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        reload_dirs=["backend", "plugins"]
    )
```

### core/hooks.py
```
# backend/core/hooks.py
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Awaitable, TypeVar

logger = logging.getLogger(__name__)

# 定义可被过滤的数据类型变量
T = TypeVar('T')

# 定义钩子函数的通用签名
HookCallable = Callable[..., Awaitable[Any]]

@dataclass(order=True)
class HookImplementation:
    """封装一个钩子实现及其元数据。"""
    priority: int
    func: HookCallable = field(compare=False)
    plugin_name: str = field(compare=False, default="<unknown>")

class HookManager:
    """
    一个中心化的服务，负责发现、注册和调度所有钩子实现。
    它的设计是完全通用的，不与任何特定的钩子绑定。
    """
    def __init__(self):
        self._hooks: Dict[str, List[HookImplementation]] = defaultdict(list)
        logger.info("HookManager initialized.")

    def add_implementation(
        self,
        hook_name: str,
        implementation: HookCallable,
        priority: int = 10,
        plugin_name: str = "<core>"
    ):
        """向管理器注册一个钩子实现。"""
        if not asyncio.iscoroutinefunction(implementation):
            raise TypeError(f"Hook implementation for '{hook_name}' must be an async function.")

        hook_impl = HookImplementation(priority=priority, func=implementation, plugin_name=plugin_name)
        self._hooks[hook_name].append(hook_impl)
        self._hooks[hook_name].sort() # 保持列表按优先级排序（从小到大）
        logger.debug(f"Registered hook '{hook_name}' from plugin '{plugin_name}' with priority {priority}.")

    async def trigger(self, hook_name: str, **kwargs: Any) -> None:
        """触发一个“通知型”钩子。并发执行，忽略返回值。"""
        if hook_name not in self._hooks:
            return

        implementations = self._hooks[hook_name]
        tasks = [impl.func(**kwargs) for impl in implementations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                impl = implementations[i]
                logger.error(
                    f"Error in NOTIFICATION hook '{hook_name}' from plugin '{impl.plugin_name}': {result}",
                    exc_info=result
                )

    async def filter(self, hook_name: str, data: T, **kwargs: Any) -> T:
        """
        触发一个“过滤型”钩子，形成处理链。
        非常适合用于收集数据。
        """
        if hook_name not in self._hooks:
            return data

        current_data = data
        # 按优先级顺序执行
        for impl in self._hooks[hook_name]:
            try:
                # 每个钩子实现都会接收上一个实现返回的数据
                current_data = await impl.func(current_data, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in FILTER hook '{hook_name}' from plugin '{impl.plugin_name}'. Skipping. Error: {e}",
                    exc_info=e
                )
        
        return current_data

    # decide 方法可以根据需要添加
```

### core/__init__.py
```

```

### core/loader.py
```
# backend/core/loader.py

import json
import logging
import importlib
import importlib.resources
import traceback
from typing import List, Dict

# 导入类型提示，而不是实现
from backend.core.contracts import Container, HookManager, PluginRegisterFunc

logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self, container: Container, hook_manager: HookManager):
        self._container = container
        self._hook_manager = hook_manager

    def load_plugins(self):
        """执行插件加载的全过程：发现、排序、注册。"""
        # 在日志系统配置前使用 print
        print("\n--- Hevno 插件系统：开始加载 ---")
        
        # 阶段一：发现
        all_plugins = self._discover_plugins()
        if not all_plugins:
            print("警告：在 'plugins' 目录中未发现任何插件。")
            print("--- Hevno 插件系统：加载完成 ---\n")
            return

        # 阶段二：排序 (根据 manifest 中的 priority)
        sorted_plugins = sorted(all_plugins, key=lambda p: (p['manifest'].get('priority', 100), p['name']))
        
        print("插件加载顺序已确定：")
        for i, p_info in enumerate(sorted_plugins):
            print(f"  {i+1}. {p_info['name']} (优先级: {p_info['manifest'].get('priority', 100)})")

        # 阶段三：注册
        self._register_plugins(sorted_plugins)
        
        logger.info("所有已发现的插件均已加载并注册完毕。")
        print("--- Hevno 插件系统：加载完成 ---\n")

    def _discover_plugins(self) -> List[Dict]:
        """扫描 'plugins' 包，读取所有子包中的 manifest.json 文件。"""
        discovered = []
        try:
            # 使用现代的 importlib.resources 来安全地访问包数据
            plugins_package_path = importlib.resources.files('plugins')
            
            for plugin_path in plugins_package_path.iterdir():
                if not plugin_path.is_dir() or plugin_path.name.startswith(('__', '.')):
                    continue

                manifest_path = plugin_path / "manifest.json"
                if not manifest_path.is_file():
                    continue
                
                try:
                    manifest_content = manifest_path.read_text(encoding='utf-8')
                    manifest = json.loads(manifest_content)
                    # 构造 Python 导入路径
                    import_path = f"plugins.{plugin_path.name}"
                    
                    plugin_info = {
                        "name": manifest.get('name', plugin_path.name),
                        "manifest": manifest,
                        "import_path": import_path
                    }
                    discovered.append(plugin_info)
                except Exception as e:
                    print(f"警告：无法解析插件 '{plugin_path.name}' 的 manifest.json: {e}")
                    pass
        
        except (ModuleNotFoundError, FileNotFoundError):
            print("信息：'plugins' 目录不存在或为空，跳过插件加载。")
            pass
            
        return discovered
    
    def _register_plugins(self, plugins: List[Dict]):
        """按顺序导入并调用每个插件的注册函数。"""
        for plugin_info in plugins:
            plugin_name = plugin_info['name']
            import_path = plugin_info['import_path']
            
            try:
                plugin_module = importlib.import_module(import_path)
                
                if not hasattr(plugin_module, "register_plugin"):
                    print(f"警告：插件 '{plugin_name}' 未定义 'register_plugin' 函数，已跳过。")
                    continue
                
                register_func: PluginRegisterFunc = getattr(plugin_module, "register_plugin")
                # 将核心服务注入到插件的注册函数中
                register_func(self._container, self._hook_manager)

            except Exception as e:
                print("\n" + "="*80)
                print(f"!!! 致命错误：加载插件 '{plugin_name}' ({import_path}) 失败 !!!")
                print("="*80)
                traceback.print_exc()
                print("="*80)
                raise RuntimeError(f"无法加载插件 {plugin_name}，应用启动中止。") from e
```

### core/contracts.py
```
# backend/core/contracts.py

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator

# --- 1. 核心服务接口与类型别名 (用于类型提示) ---

# 定义一个泛型，常用于 filter 钩子
T = TypeVar('T')

# 插件注册函数的标准签名
PluginRegisterFunc = Callable[['Container', 'HookManager'], None]

# 为核心服务定义接口，插件不应直接导入实现，而应依赖这些接口
class Container:
    def register(self, name: str, factory: Callable, singleton: bool = True) -> None: raise NotImplementedError
    def resolve(self, name: str) -> Any: raise NotImplementedError

class HookManager:
    def add_implementation(self, hook_name: str, implementation: Callable, priority: int = 10, plugin_name: str = "<unknown>"): raise NotImplementedError
    async def trigger(self, hook_name: str, **kwargs: Any) -> None: raise NotImplementedError
    async def filter(self, hook_name: str, data: T, **kwargs: Any) -> T: raise NotImplementedError
    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]: raise NotImplementedError


# --- 2. 核心持久化状态模型 (从旧 core/models.py 和 core/contracts.py 合并) ---

class RuntimeInstruction(BaseModel):
    runtime: str
    config: Dict[str, Any] = Field(default_factory=dict)

class GenericNode(BaseModel):
    id: str
    run: List[RuntimeInstruction]
    depends_on: Optional[List[str]] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphDefinition(BaseModel):
    nodes: List[GenericNode]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v

class StateSnapshot(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sandbox_id: UUID
    graph_collection: GraphCollection
    world_state: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_snapshot_id: Optional[UUID] = None
    triggering_input: Dict[str, Any] = Field(default_factory=dict)
    run_output: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(frozen=True)

class Sandbox(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    head_snapshot_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- 3. 核心运行时上下文模型 (从旧 core/contracts.py 迁移) ---

class SharedContext(BaseModel):
    world_state: Dict[str, Any]
    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    services: Any # 通常是一个 DotAccessibleDict 包装的容器
    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    shared: SharedContext
    initial_snapshot: StateSnapshot
    hook_manager: HookManager
    model_config = {"arbitrary_types_allowed": True}


# --- 4. 系统事件契约 (用于钩子, 从旧 core/contracts.py 迁移) ---

class NodeContext(BaseModel):
    node: GenericNode
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

class EngineStepStartContext(BaseModel):
    initial_snapshot: StateSnapshot
    triggering_input: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)

class EngineStepEndContext(BaseModel):
    final_snapshot: StateSnapshot
    model_config = ConfigDict(arbitrary_types_allowed=True)

class NodeExecutionStartContext(NodeContext): pass
class NodeExecutionSuccessContext(NodeContext):
    result: Dict[str, Any]
class NodeExecutionErrorContext(NodeContext):
    exception: Exception

class BeforeConfigEvaluationContext(NodeContext):
    instruction_config: Dict[str, Any]
class AfterMacroEvaluationContext(NodeContext):
    evaluated_config: Dict[str, Any]

class BeforeSnapshotCreateContext(BaseModel):
    snapshot_data: Dict[str, Any]
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ResolveNodeDependenciesContext(BaseModel):
    node: GenericNode
    auto_inferred_deps: Set[str]


# --- 5. 核心服务接口契约 ---
# 这些是插件应该依赖的抽象接口，而不是具体实现类。

class ExecutionEngineInterface:
    async def step(self, initial_snapshot: 'StateSnapshot', triggering_input: Dict[str, Any] = None) -> 'StateSnapshot':
        raise NotImplementedError

class SnapshotStoreInterface:
    def save(self, snapshot: 'StateSnapshot') -> None: raise NotImplementedError
    def get(self, snapshot_id: UUID) -> Optional['StateSnapshot']: raise NotImplementedError
    def find_by_sandbox(self, sandbox_id: UUID) -> List['StateSnapshot']: raise NotImplementedError

class AuditorInterface:
    async def generate_full_report(self) -> Dict[str, Any]: raise NotImplementedError
    def set_reporters(self, reporters: List['Reportable']) -> None: raise NotImplementedError

class Reportable(ABC): # 如果还没定义成抽象类，现在定义
    @property
    @abstractmethod
    def report_key(self) -> str: pass
    
    @property
    def is_static(self) -> bool: return True
    
    @abstractmethod
    async def generate_report(self) -> Any: pass
```

# Directory: plugins

### __init__.py
```

```

### core_llm/service.py
```
# plugins/core_llm/service.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, Optional, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# --- 从本插件内部导入组件 ---
from .manager import KeyPoolManager, KeyInfo
from .models import (
    LLMResponse,
    LLMError,
    LLMErrorType,
    LLMResponseStatus,
    LLMRequestFailedError,
)
from .registry import ProviderRegistry

logger = logging.getLogger(__name__)

def is_retryable_llm_error(exception: Exception) -> bool:
    """
    一个 tenacity 重试条件函数。
    仅当异常是 LLMRequestFailedError 并且其内部的 last_error 
    被明确标记为 is_retryable=True 时，才返回 True。
    """
    return (
        isinstance(exception, LLMRequestFailedError) and
        exception.last_error is not None and
        exception.last_error.is_retryable
    )

class LLMService:
    """
    LLM 网关的核心服务，负责协调所有组件并执行请求。
    实现了带有密钥轮换、状态管理和指数退避的健壮重试逻辑。
    """
    def __init__(
        self,
        key_manager: KeyPoolManager,
        provider_registry: ProviderRegistry,
        max_retries: int = 3
    ):
        self.key_manager = key_manager
        self.provider_registry = provider_registry
        self.max_retries = max_retries
        self.last_known_error: Optional[LLMError] = None

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        向指定的 LLM 发起请求，并处理重试逻辑。
        """
        self.last_known_error = None
        try:
            provider_name, actual_model_name = self._parse_model_name(model_name)
        except ValueError as e:
            return self._create_failure_response(
                model_name=model_name,
                error=LLMError(
                    error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                    message=str(e),
                    is_retryable=False,
                ),
            )

        def log_before_sleep(retry_state):
            """在 tenacity 每次重试前调用的日志记录函数。"""
            exc = retry_state.outcome.exception()
            if exc and isinstance(exc, LLMRequestFailedError) and exc.last_error:
                error_type = exc.last_error.error_type.value
            else:
                error_type = "unknown"
            
            logger.warning(
                f"LLM request for {model_name} failed with a retryable error ({error_type}). "
                f"Waiting {retry_state.next_action.sleep:.2f}s before attempt {retry_state.attempt_number + 1}."
            )
        
        retry_decorator = retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=is_retryable_llm_error,
            reraise=True,
            before_sleep=log_before_sleep
        )

        try:
            wrapped_attempt = retry_decorator(self._attempt_request)
            return await wrapped_attempt(provider_name, actual_model_name, prompt, **kwargs)
        
        except LLMRequestFailedError as e:
            final_message = (
                f"LLM request for model '{model_name}' failed permanently after {self.max_retries} attempt(s)."
            )
            logger.error(final_message, exc_info=True)
            # 重新抛出，以便上层（如运行时）可以捕获并格式化最终错误
            raise LLMRequestFailedError(final_message, last_error=self.last_known_error) from e
        
        except Exception as e:
            logger.critical(f"An unexpected non-LLM error occurred in LLMService: {e}", exc_info=True)
            raise

    async def _attempt_request(
        self,
        provider_name: str,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        执行单次 LLM 请求尝试。
        - 如果成功，返回 LLMResponse。
        - 如果遇到可重试的错误，抛出 LLMRequestFailedError 以便 tenacity 捕获。
        - 如果遇到不可重试的错误，返回带有 error_details 的 LLMResponse。
        """
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found.")

        try:
            async with self.key_manager.acquire_key(provider_name) as key_info:
                try:
                    response = await provider.generate(
                        prompt=prompt, model_name=model_name, api_key=key_info.key_string, **kwargs
                    )
                    
                    # Case 1: Provider 返回了一个带有逻辑错误的响应 (e.g., 内容过滤)
                    if response.status in [LLMResponseStatus.ERROR, LLMResponseStatus.FILTERED] and response.error_details:
                        self.last_known_error = response.error_details
                        await self._handle_error(provider_name, key_info, response.error_details)
                        
                        # 如果此逻辑错误是可重试的，则抛出异常以触发 tenacity
                        if response.error_details.is_retryable:
                            raise LLMRequestFailedError("Provider returned a retryable error response.", last_error=response.error_details)

                    # Case 2: 成功，或遇到不可重试的逻辑错误。无论哪种，本次尝试都结束了。
                    return response
                
                except Exception as e:
                    # Case 3: Provider 抛出了一个 SDK 或网络层面的异常
                    llm_error = provider.translate_error(e)
                    self.last_known_error = llm_error
                    await self._handle_error(provider_name, key_info, llm_error)
                    
                    error_message = f"Request attempt failed due to an exception: {llm_error.message}"
                    # 抛出我们的自定义异常，tenacity 将根据 is_retryable 决定是否重试
                    raise LLMRequestFailedError(error_message, last_error=llm_error) from e
        
        except (RuntimeError, ValueError) as e:
            # 捕获我们自己的内部错误 (e.g., 'No key pool registered for provider')
            # 这些错误通常是配置问题，不可重试。
            raise LLMRequestFailedError(str(e), last_error=LLMError(
                error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                message=str(e),
                is_retryable=False
            ))

    async def _handle_error(self, provider_name: str, key_info: KeyInfo, error: LLMError):
        """根据错误类型更新密钥池中密钥的状态。"""
        if error.error_type == LLMErrorType.AUTHENTICATION_ERROR:
            logger.warning(f"Authentication error with key for '{provider_name}'. Banning key.")
            await self.key_manager.mark_as_banned(provider_name, key_info.key_string)
        elif error.error_type == LLMErrorType.RATE_LIMIT_ERROR:
            cooldown = error.retry_after_seconds or 60
            logger.info(f"Rate limit hit for key on '{provider_name}'. Cooling down for {cooldown}s.")
            self.key_manager.mark_as_rate_limited(provider_name, key_info.key_string, cooldown)

    def _parse_model_name(self, model_name: str) -> tuple[str, str]:
        """将 'provider/model_id' 格式的字符串解析为元组。"""
        parts = model_name.split('/', 1)
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"Invalid model name format: '{model_name}'. Expected 'provider/model_id'.")
        return parts[0], parts[1]
    
    def _create_failure_response(self, model_name: str, error: LLMError) -> LLMResponse:
        """创建一个标准的错误响应对象。"""
        return LLMResponse(status=LLMResponseStatus.ERROR, model_name=model_name, error_details=error)


class MockLLMService:
    """
    一个 LLMService 的模拟实现，用于调试和测试。
    它不进行任何网络调用，而是立即返回一个可预测的假响应。
    """
    def __init__(self, *args, **kwargs):
        logger.info("--- MockLLMService Initialized: Real LLM calls are disabled. ---")

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        await asyncio.sleep(0.05)
        mock_content = f"[MOCK RESPONSE for {model_name}] - Prompt received: '{prompt[:50]}...'"
        
        return LLMResponse(
            status=LLMResponseStatus.SUCCESS,
            content=mock_content,
            model_name=model_name,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 15, "total_tokens": len(prompt.split()) + 15}
        )
```

### core_llm/models.py
```
# plugins/core_llm/models.py

from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


# --- Enums for Status and Error Types ---

class LLMResponseStatus(str, Enum):
    """定义 LLM 响应的标准化状态。"""
    SUCCESS = "success"
    FILTERED = "filtered"
    ERROR = "error"


class LLMErrorType(str, Enum):
    """定义标准化的 LLM 错误类型，用于驱动重试和故障转移逻辑。"""
    AUTHENTICATION_ERROR = "authentication_error"  # 密钥无效或权限不足
    RATE_LIMIT_ERROR = "rate_limit_error"          # 达到速率限制
    PROVIDER_ERROR = "provider_error"              # 服务商侧 5xx 或其他服务器错误
    NETWORK_ERROR = "network_error"                # 网络连接问题
    INVALID_REQUEST_ERROR = "invalid_request_error"  # 请求格式错误 (4xx)
    UNKNOWN_ERROR = "unknown_error"                # 未知或未分类的错误


# --- Core Data Models ---

class LLMError(BaseModel):
    """
    一个标准化的错误对象，用于封装来自任何提供商的错误信息。
    """
    error_type: LLMErrorType = Field(
        ...,
        description="错误的标准化类别。"
    )
    message: str = Field(
        ...,
        description="可读的错误信息。"
    )
    is_retryable: bool = Field(
        ...,
        description="此错误是否适合重试（例如，网络错误或某些服务端错误）。"
    )
    retry_after_seconds: Optional[int] = Field(
        default=None,
        description="如果提供商明确告知，需要等待多少秒后才能重试。"
    )
    provider_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="原始的、特定于提供商的错误细节，用于调试。"
    )


class LLMResponse(BaseModel):
    """
    一个标准化的响应对象，用于封装来自任何提供商的成功、过滤或错误结果。
    """
    status: LLMResponseStatus = Field(
        ...,
        description="响应的总体状态。"
    )
    content: Optional[str] = Field(
        default=None,
        description="LLM 生成的文本内容。仅在 status 为 'success' 时保证存在。"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="实际用于生成此响应的模型名称。"
    )
    usage: Optional[Dict[str, int]] = Field(
        default=None,
        description="Token 使用情况统计，例如 {'prompt_tokens': 10, 'completion_tokens': 200}。"
    )
    error_details: Optional[LLMError] = Field(
        default=None,
        description="如果 status 为 'error'，则包含此字段以提供详细的错误信息。"
    )
    
    # 可以在这里添加一个验证器，确保在status为error时，error_details不为空
    # 但为了保持模型的简单性，我们暂时将此逻辑留给上层服务处理。


# --- Custom Exception ---

class LLMRequestFailedError(Exception):
    """
    在所有重试和故障转移策略都用尽后，由 LLMService 抛出的最终异常。
    """
    def __init__(self, message: str, last_error: Optional[LLMError] = None):
        """
        :param message: 对失败的总体描述。
        :param last_error: 导致最终失败的最后一个标准化错误对象。
        """
        super().__init__(message)
        self.last_error = last_error

    def __str__(self):
        if self.last_error:
            return (
                f"{super().__str__()}\n"  # <--- super().__str__() 会返回我们传入的 message
                f"Last known error ({self.last_error.error_type.value}): {self.last_error.message}"
            )
        return super().__str__()
```

### core_llm/registry.py
```
# plugins/core_llm/registry.py

from typing import Dict, Type, Optional, Callable
from pydantic import BaseModel
from .providers.base import LLMProvider
import logging

logger = logging.getLogger(__name__)

class ProviderInfo(BaseModel):
    provider_class: Type[LLMProvider]
    key_env_var: str

class ProviderRegistry:
    """
    负责注册和查找 LLMProvider 实例及其元数据。
    """
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._provider_info: Dict[str, ProviderInfo] = {}

    def register(self, name: str, key_env_var: str) -> Callable[[Type[LLMProvider]], Type[LLMProvider]]:
        def decorator(provider_class: Type[LLMProvider]) -> Type[LLMProvider]:
            if name in self._provider_info:
                logger.warning(f"Overwriting LLM provider registration for '{name}'.")
            self._provider_info[name] = ProviderInfo(provider_class=provider_class, key_env_var=key_env_var)
            logger.info(f"LLM Provider '{name}' discovered (keys from '{key_env_var}').")
            return provider_class
        return decorator
    
    def get_provider_info(self, name: str) -> Optional[ProviderInfo]:
        return self._provider_info.get(name)

    def instantiate_all(self):
        """实例化所有已注册的 Provider。"""
        for name, info in self._provider_info.items():
            if name not in self._providers:
                self._providers[name] = info.provider_class()
    
    def get(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name)
    
    def get_all_provider_info(self) -> Dict[str, ProviderInfo]:
        return self._provider_info

provider_registry = ProviderRegistry()
```

### core_llm/__init__.py
```
# plugins/core_llm/__init__.py 

import logging
import os

# 从平台核心导入接口和类型
from backend.core.contracts import Container, HookManager

# 导入本插件内部的组件
from .service import LLMService, MockLLMService
from .manager import KeyPoolManager, CredentialManager
from .registry import provider_registry
from .runtime import LLMRuntime
from .reporters import LLMProviderReporter

# 动态加载所有 provider
from backend.core.loader import load_modules
load_modules(["plugins.core_llm.providers"])

logger = logging.getLogger(__name__)

# --- 服务工厂 (Service Factories) ---
def _create_llm_service(container: Container) -> LLMService:
    """这个工厂函数封装了创建 LLMService 的复杂逻辑。"""
    is_debug_mode = os.getenv("HEVNO_LLM_DEBUG_MODE", "false").lower() == "true"
    if is_debug_mode:
        logger.warning("LLM Gateway is in MOCK/DEBUG mode.")
        return MockLLMService()

    provider_registry.instantiate_all()
    cred_manager = CredentialManager()
    key_manager = KeyPoolManager(credential_manager=cred_manager)
    
    for name, info in provider_registry.get_all_provider_info().items():
        key_manager.register_provider(name, info.key_env_var)

    return LLMService(
        key_manager=key_manager,
        provider_registry=provider_registry,
        max_retries=3
    )

# --- 钩子实现 (Hook Implementations) ---
async def provide_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的 'llm.default' 运行时。"""
    if "llm.default" not in runtimes:
        runtimes["llm.default"] = LLMRuntime
        logger.debug("Provided 'llm.default' runtime to the engine.")
    return runtimes

async def provide_reporter(reporters: list) -> list:
    """钩子实现：向审计员提供本插件的报告器。"""
    reporters.append(LLMProviderReporter())
    logger.debug("Provided 'LLMProviderReporter' to the auditor.")
    return reporters

# --- 主注册函数 (Main Registration Function) ---
def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-llm 插件的注册入口，由平台加载器调用。"""
    logger.info("--> 正在注册 [core-llm] 插件...")

    # 1. 注册服务到 DI 容器
    #    'llm_service' 是单例，它的创建逻辑被封装在工厂函数中。
    container.register("llm_service", _create_llm_service)
    logger.debug("服务 'llm_service' 已注册。")

    # 2. 注册钩子实现
    #    通过 'collect_runtimes' 钩子，将我们的运行时提供给 core_engine。
    hook_manager.add_implementation(
        "collect_runtimes", 
        provide_runtime, 
        plugin_name="core-llm"
    )
    #    通过 'collect_reporters' 钩子，将我们的报告器提供给 core_api。
    hook_manager.add_implementation(
        "collect_reporters",
        provide_reporter,
        plugin_name="core-llm"
    )
    logger.debug("钩子实现 'collect_runtimes' 和 'collect_reporters' 已注册。")
    
    logger.info("插件 [core-llm] 注册成功。")
```

### core_llm/runtime.py
```
# plugins/core_llm/runtime.py

from typing import Dict, Any

from backend.core.contracts import ExecutionContext
from plugins.core_engine.interfaces import RuntimeInterface
from .models import LLMResponse, LLMRequestFailedError

# --- 核心修改: 移除 @runtime_registry 装饰器 ---
class LLMRuntime(RuntimeInterface):
    """
    一个轻量级的运行时，它通过 Hevno LLM Gateway 发起 LLM 调用。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        model_name = config.get("model")
        prompt = config.get("prompt")
        
        if not model_name:
            raise ValueError("LLMRuntime requires a 'model' field in its config (e.g., 'gemini/gemini-1.5-flash').")
        if not prompt:
            raise ValueError("LLMRuntime requires a 'prompt' field in its config.")

        llm_params = {k: v for k, v in config.items() if k not in ["model", "prompt"]}

        llm_service = context.shared.services.llm_service

        try:
            response: LLMResponse = await llm_service.request(
                model_name=model_name,
                prompt=prompt,
                **llm_params
            )
            
            if response.error_details:
                return {
                    "error": response.error_details.message,
                    "error_type": response.error_details.error_type.value,
                    "details": response.error_details.model_dump()
                }

            return {
                "llm_output": response.content,
                "usage": response.usage,
                "model_name": response.model_name
            }

        except LLMRequestFailedError as e:
            return {
                "error": str(e),
                "details": e.last_error.model_dump() if e.last_error else None
            }
```

### core_llm/manifest.json
```
{
    "name": "core-llm",
    "version": "1.0.0",
    "description": "Provides the LLM Gateway, including multi-provider support, key management, and retry logic.",
    "author": "Hevno Team",
    "priority": 20,
    "dependencies": ["core-engine"] 
}
```

### core_llm/reporters.py
```
# plugins/core_llm/reporters.py
from typing import Any
from plugins.core_api.auditor import Reportable 
from .registry import provider_registry


class LLMProviderReporter(Reportable):
    
    @property
    def report_key(self) -> str:
        return "llm_providers"
    
    async def generate_report(self) -> Any:
        manifest = []
        all_info = provider_registry.get_all_provider_info()
        for name, info in all_info.items():
            provider_class = info.provider_class
            manifest.append({
                "name": name,
                # 同样，假设 LLMProvider 基类增加了 supported_models 属性
                "supported_models": getattr(provider_class, 'supported_models', [])
            })
        return sorted(manifest, key=lambda x: x['name'])
```

### core_llm/manager.py
```
# plugins/core_llm/manager.py

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, AsyncIterator


# --- Enums and Data Classes for Key State Management ---

class KeyStatus(str, Enum):
    """定义 API 密钥的健康状态。"""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    BANNED = "banned"


@dataclass
class KeyInfo:
    """存储单个 API 密钥及其状态信息。"""
    key_string: str
    status: KeyStatus = KeyStatus.AVAILABLE
    rate_limit_until: float = 0.0  # Unix timestamp until which the key is rate-limited

    def is_available(self) -> bool:
        """检查密钥当前是否可用。"""
        if self.status == KeyStatus.BANNED:
            return False
        if self.status == KeyStatus.RATE_LIMITED:
            if time.time() < self.rate_limit_until:
                return False
            # 如果限速时间已过，自动恢复为可用
            self.status = KeyStatus.AVAILABLE
            self.rate_limit_until = 0.0
        return self.status == KeyStatus.AVAILABLE


# --- Core Manager Components ---

class CredentialManager:
    """负责从环境变量中安全地加载和解析密钥。"""

    def load_keys_from_env(self, env_variable: str) -> List[str]:
        """
        从指定的环境变量中加载 API 密钥。
        密钥应以逗号分隔。

        :param env_variable: 环境变量的名称 (e.g., 'GEMINI_API_KEYS').
        :return: 一个包含 API 密钥字符串的列表。
        """
        keys_str = os.getenv(env_variable)
        if not keys_str:
            print(f"Warning: Environment variable '{env_variable}' not set. No keys loaded.")
            return []
        
        # 按逗号分割，并去除每个密钥前后的空白字符
        keys = [key.strip() for key in keys_str.split(',') if key.strip()]
        if not keys:
            print(f"Warning: Environment variable '{env_variable}' is set but contains no valid keys.")
        return keys


class ProviderKeyPool:
    """
    管理特定提供商（如 'gemini'）的一组 API 密钥。
    内置并发控制和密钥选择逻辑。
    """
    def __init__(self, provider_name: str, keys: List[str]):
        if not keys:
            raise ValueError(f"Cannot initialize ProviderKeyPool for '{provider_name}' with an empty key list.")
        
        self.provider_name = provider_name
        self._keys: List[KeyInfo] = [KeyInfo(key_string=k) for k in keys]
        
        # 使用 Semaphore 控制对该提供商的并发请求数量，初始值等于可用密钥数
        self._semaphore = asyncio.Semaphore(len(self._keys))

    def _get_next_available_key(self) -> Optional[KeyInfo]:
        """循环查找下一个可用的密钥。"""
        # 简单的轮询策略
        for key_info in self._keys:
            if key_info.is_available():
                return key_info
        return None

    @asynccontextmanager
    async def acquire_key(self) -> AsyncIterator[KeyInfo]:
        """
        一个安全的异步上下文管理器，用于获取和释放密钥。
        这是与该池交互的主要方式。

        :yields: 一个可用的 KeyInfo 对象。
        :raises asyncio.TimeoutError: 如果在指定时间内无法获取密钥。
        :raises RuntimeError: 如果池中已无任何可用密钥。
        """
        # 1. 获取信号量，这会阻塞直到有空闲的“插槽”
        await self._semaphore.acquire()

        try:
            # 2. 从池中选择一个当前可用的密钥
            key_info = self._get_next_available_key()
            if not key_info:
                # 这种情况理论上不应该发生，因为信号量应该反映可用密钥数
                # 但作为防御性编程，我们处理它
                raise RuntimeError(f"No available keys in pool '{self.provider_name}' despite acquiring semaphore.")
            
            # 3. 将密钥提供给调用者
            yield key_info
        finally:
            # 4. 无论发生什么，都释放信号量
            self._semaphore.release()

    def mark_as_rate_limited(self, key_string: str, duration_seconds: int = 60):
        """标记一个密钥为被限速状态。"""
        for key in self._keys:
            if key.key_string == key_string:
                key.status = KeyStatus.RATE_LIMITED
                key.rate_limit_until = time.time() + duration_seconds
                print(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' marked as rate-limited for {duration_seconds}s.")
                break

    async def mark_as_banned(self, key_string: str):
        """永久性地标记一个密钥为被禁用，并减少并发信号量。"""
        for key in self._keys:
            if key.key_string == key_string and key.status != KeyStatus.BANNED:
                key.status = KeyStatus.BANNED
                # 关键一步：永久性地减少一个并发“插槽”
                # 我们通过尝试获取然后不释放来实现
                # 注意：这假设信号量初始值与密钥数相同
                await self._semaphore.acquire()
                print(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' permanently banned. Concurrency reduced.")
                break


class KeyPoolManager:
    """
    顶层管理器，聚合了所有提供商的密钥池。
    这是上层服务（LLMService）与之交互的唯一入口。
    """
    def __init__(self, credential_manager: CredentialManager):
        self._pools: Dict[str, ProviderKeyPool] = {}
        self._cred_manager = credential_manager

    def register_provider(self, provider_name: str, env_variable: str):
        """

        从环境变量加载密钥，并为提供商创建一个密钥池。
        :param provider_name: 提供商的名称 (e.g., 'gemini').
        :param env_variable: 包含该提供商密钥的环境变量。
        """
        keys = self._cred_manager.load_keys_from_env(env_variable)
        if keys:
            self._pools[provider_name] = ProviderKeyPool(provider_name, keys)
            print(f"Registered provider '{provider_name}' with {len(keys)} keys from '{env_variable}'.")

    def get_pool(self, provider_name: str) -> Optional[ProviderKeyPool]:
        """获取指定提供商的密钥池。"""
        return self._pools.get(provider_name)

    # 为了方便上层服务调用，我们将核心方法直接暴露在这里
    
    @asynccontextmanager
    async def acquire_key(self, provider_name: str) -> AsyncIterator[KeyInfo]:
        """
        从指定提供商的池中获取一个密钥。
        """
        pool = self.get_pool(provider_name)
        if not pool:
            raise ValueError(f"No key pool registered for provider '{provider_name}'.")
        
        async with pool.acquire_key() as key_info:
            yield key_info

    def mark_as_rate_limited(self, provider_name: str, key_string: str, duration_seconds: int = 60):
        pool = self.get_pool(provider_name)
        if pool:
            pool.mark_as_rate_limited(key_string, duration_seconds)

    async def mark_as_banned(self, provider_name: str, key_string: str):
        pool = self.get_pool(provider_name)
        if pool:
            await pool.mark_as_banned(key_string)
```

### core_api/__init__.py
```
# plugins/core_api/__init__.py

import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager, Reportable
from .auditor import Auditor
from .base_router import router as base_router
from .sandbox_router import router as sandbox_router

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_auditor() -> Auditor:
    """工厂：只创建 Auditor 的空实例。它的内容将在之后被异步填充。"""
    return Auditor([])

# --- 钩子实现 ---
async def populate_auditor(container: Container):
    """钩子实现：监听启动事件，异步地收集报告器并填充 Auditor。"""
    logger.debug("Async task: Populating auditor with reporters...")
    hook_manager = container.resolve("hook_manager")
    auditor: Auditor = container.resolve("auditor")
    
    reporters_list: List[Reportable] = await hook_manager.filter("collect_reporters", [])
    
    auditor.set_reporters(reporters_list)
    logger.info(f"Auditor populated with {len(reporters_list)} reporter(s).")

async def provide_own_routers(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的路由添加到收集中。"""
    routers.append(base_router)
    routers.append(sandbox_router)
    logger.debug("Provided own routers (base, sandbox) to the application.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-api] 插件...")

    # 1. 注册服务（仅创建空实例）
    container.register("auditor", _create_auditor, singleton=True)
    logger.debug("服务 'auditor' 已注册 (initially empty)。")

    # 2. 注册异步填充钩子
    hook_manager.add_implementation(
        "services_post_register",
        populate_auditor,
        plugin_name="core-api"
    )

    # 3. 【关键】注册路由【提供者】钩子
    #    它现在和其他插件一样，只是一个提供者。
    hook_manager.add_implementation(
        "collect_api_routers", 
        provide_own_routers, 
        priority=100, # 较高的 priority 意味着后执行
        plugin_name="core-api"
    )
    logger.debug("钩子实现 'collect_api_routers' 和 'services_post_register' 已注册。")

    logger.info("插件 [core-api] 注册成功。")
```

### core_api/sandbox_router.py
```
# plugins/core_api/sandbox_router.py

from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from fastapi import APIRouter, Body, Depends, HTTPException

# 从平台核心契约导入数据模型
from backend.core.contracts import Sandbox, StateSnapshot, GraphCollection

# 从本插件的依赖注入文件中导入 "getters"
from .dependencies import get_sandbox_store, get_snapshot_store, get_engine

# 只从 contracts 导入接口
from backend.core.contracts import ExecutionEngineInterface, SnapshotStoreInterface


router = APIRouter(prefix="/api/sandboxes", tags=["Sandboxes"])

# --- Request/Response Models ---
class CreateSandboxRequest(BaseModel):
    name: str = Field(..., description="The human-readable name for the sandbox.")
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = Field(default_factory=dict)

# --- API Endpoints ---
@router.post("", response_model=Sandbox, status_code=201)
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
):
    """创建一个新的沙盒并生成其初始（创世）快照。"""
    sandbox = Sandbox(name=request_body.name)
    
    if sandbox.id in sandbox_store:
        raise HTTPException(status_code=409, detail=f"Sandbox with ID {sandbox.id} already exists.")

    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request_body.graph_collection,
        world_state=request_body.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    
    return sandbox

@router.post("/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store),
    engine: ExecutionEngineInterface = Depends(get_engine)
):
    """在沙盒的最新状态上执行一步计算。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    if not sandbox.head_snapshot_id:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
        
    latest_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
    if not latest_snapshot:
        raise HTTPException(status_code=500, detail=f"Data inconsistency: head snapshot '{sandbox.head_snapshot_id}' not found.")
    
    new_snapshot = await engine.step(latest_snapshot, user_input)
    
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    
    return new_snapshot

@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot])
async def get_sandbox_history(
    sandbox_id: UUID,
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
):
    """获取一个沙盒的所有历史快照，按时间顺序排列。"""
    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    return snapshots

@router.put("/{sandbox_id}/revert", status_code=200)
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
):
    """将沙盒的状态回滚到指定的历史快照。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    target_snapshot = snapshot_store.get(snapshot_id)
    if not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Target snapshot not found or does not belong to this sandbox.")
    
    sandbox.head_snapshot_id = snapshot_id
    return {"message": f"Sandbox '{sandbox.name}' successfully reverted to snapshot {snapshot_id}"}
```

### core_api/manifest.json
```
{
    "name": "core-api",
    "version": "1.0.0",
    "description": "Provides the core RESTful API endpoints and the system reporting auditor.",
    "author": "Hevno Team",
    "priority": 100
}
```

### core_api/auditor.py
```
# plugins/core_api/auditor.py

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class Reportable(ABC):
    """
    一个统一的汇报协议 (契约)。
    任何希望向系统提供状态或元数据的组件都应实现此接口。
    """
    @property
    @abstractmethod
    def report_key(self) -> str:
        """返回此报告在最终JSON对象中的唯一键名。"""
        pass

    @property
    def is_static(self) -> bool:
        """指明此报告是否为静态（可缓存）。默认为 True。"""
        return True

    @abstractmethod
    async def generate_report(self) -> Any:
        """生成并返回报告内容。"""
        pass

class Auditor:
    """
    审阅官服务。负责从注册的 Reportable 实例中收集报告并聚合。
    """
    def __init__(self, reporters: List[Reportable]):
        self._reporters = reporters
        self._static_report_cache: Dict[str, Any] | None = None

    def set_reporters(self, reporters: List[Reportable]):
        """允许在创建后设置/替换报告器列表。"""
        self._reporters = reporters
        self._static_report_cache = None

    async def generate_full_report(self) -> Dict[str, Any]:
        """生成完整的系统报告。"""
        full_report = {}

        # 1. 处理静态报告 (带缓存)
        if self._static_report_cache is None:
            self._static_report_cache = await self._generate_static_reports()
        full_report.update(self._static_report_cache)

        # 2. 处理动态报告 (实时生成)
        dynamic_reports = await self._generate_dynamic_reports()
        full_report.update(dynamic_reports)

        return full_report

    async def _generate_reports_by_type(self, static: bool) -> Dict[str, Any]:
        """根据报告类型（静态/动态）生成报告。"""
        reports = {}
        reportables_to_run = [r for r in self._reporters if r.is_static is static]
        if not reportables_to_run:
            return {}

        tasks = [r.generate_report() for r in reportables_to_run]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r, result in zip(reportables_to_run, results):
            if isinstance(result, Exception):
                reports[r.report_key] = {"error": f"Failed to generate report: {result}"}
            else:
                reports[r.report_key] = result
        return reports

    async def _generate_static_reports(self) -> Dict[str, Any]:
        return await self._generate_reports_by_type(static=True)

    async def _generate_dynamic_reports(self) -> Dict[str, Any]:
        return await self._generate_reports_by_type(static=False)
```

### core_api/base_router.py
```
# plugins/core_api/base_router.py

from fastapi import APIRouter, Depends
from .dependencies import get_auditor
from .auditor import Auditor

router = APIRouter(prefix="/api", tags=["System"])

@router.get("/system/report")
async def get_system_report(auditor: Auditor = Depends(get_auditor)):
    """获取完整的系统状态和元数据报告。"""
    return await auditor.generate_full_report()
```

### core_api/dependencies.py
```
# plugins/core_api/dependencies.py

from typing import Dict, Any, List
from uuid import UUID
from fastapi import Request

# 只从 backend.core.contracts 导入数据模型和接口
from backend.core.contracts import (
    Sandbox, 
    StateSnapshot,
    ExecutionEngineInterface, 
    SnapshotStoreInterface,
    AuditorInterface
)

# 每个依赖注入函数现在只做一件事：从容器中解析服务。
# 类型提示使用我们新定义的接口。

def get_engine(request: Request) -> ExecutionEngineInterface:
    return request.app.state.container.resolve("execution_engine")

def get_snapshot_store(request: Request) -> SnapshotStoreInterface:
    return request.app.state.container.resolve("snapshot_store")

def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    # 对于简单的字典存储，可以直接用 Dict
    return request.app.state.container.resolve("sandbox_store")

def get_auditor(request: Request) -> AuditorInterface:
    return request.app.state.container.resolve("auditor")
```

### core_logging/logging_config.yaml
```
version: 1

disable_existing_loggers: false

# 定义格式化器
formatters:
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  detailed:
    format: '[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s'

# 定义处理器 (输出到哪里)
handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: simple
    stream: ext://sys.stdout

#   file:
#     class: logging.handlers.RotatingFileHandler
#     level: DEBUG
#     formatter: detailed
#     filename: app.log
#     maxBytes: 10485760 # 10MB
#     backupCount: 5
#     encoding: utf8

# 根日志记录器配置
root:
  level: INFO # 默认级别
  handlers: [console] #, file] # 默认使用控制台处理器

# 可以为特定模块设置不同级别
loggers:
  uvicorn:
    level: INFO
  fastapi:
    level: INFO
```

### core_logging/__init__.py
```
# plugins/core_logging/__init__.py
import os
import yaml
import logging
import logging.config
from pathlib import Path

from backend.core.contracts import Container, HookManager

PLUGIN_DIR = Path(__file__).parent

def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-logging 插件的注册入口。"""
    # 统一的入口消息
    print("--> 正在注册 [core-logging] 插件...")
    
    config_path = PLUGIN_DIR / "logging_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        logging_config = yaml.safe_load(f)
    
    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level and env_log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level_override = env_log_level.upper()
        logging_config['root']['level'] = log_level_override

    logging.config.dictConfig(logging_config)
    
    logger = logging.getLogger(__name__)
    
    # 统一的成功消息
    logger.info("插件 [core-logging] 注册成功。")
```

### core_logging/manifest.json
```
{
    "name": "core-logging",
    "version": "1.0.0",
    "description": "Provides centralized, configurable logging for the Hevno platform.",
    "author": "Hevno Team",
    "priority": -100
}
```

### core_persistence/service.py
```
# plugins/core_persistence/service.py

import io
import json
import zipfile
import logging
from pathlib import Path
from typing import Type, TypeVar, Tuple, Dict, Any, List
from pydantic import BaseModel, ValidationError

# --- 核心修复：从本插件的 models.py 中导入所需的模型 ---
from .models import PackageManifest, AssetType, FILE_EXTENSIONS

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class PersistenceService:
    """
    处理所有文件系统和包导入/导出操作的核心服务。
    """
    def __init__(self, assets_base_dir: str):
        self.assets_base_dir = Path(assets_base_dir)
        self.assets_base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PersistenceService initialized. Assets directory: {self.assets_base_dir.resolve()}")

    def _get_asset_path(self, asset_type: AssetType, asset_name: str) -> Path:
        """根据资产类型和名称构造标准化的文件路径。"""
        extension = FILE_EXTENSIONS[asset_type]
        # 简单的安全措施，防止路径遍历
        safe_name = Path(asset_name).name 
        return self.assets_base_dir / asset_type.value / f"{safe_name}{extension}"

    def save_asset(self, asset_model: T, asset_type: AssetType, asset_name: str) -> Path:
        """将 Pydantic 模型保存为格式化的 JSON 文件。"""
        file_path = self._get_asset_path(asset_type, asset_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        json_content = asset_model.model_dump_json(indent=2)
        file_path.write_text(json_content, encoding='utf-8')
        return file_path

    def load_asset(self, asset_type: AssetType, asset_name: str, model_class: Type[T]) -> T:
        """从文件加载并验证 Pydantic 模型。"""
        file_path = self._get_asset_path(asset_type, asset_name)
        if not file_path.exists():
            raise FileNotFoundError(f"Asset '{asset_name}' of type '{asset_type.value}' not found.")
        
        json_content = file_path.read_text(encoding='utf-8')
        try:
            return model_class.model_validate_json(json_content)
        except ValidationError as e:
            raise ValueError(f"Failed to validate asset '{asset_name}': {e}") from e

    def list_assets(self, asset_type: AssetType) -> List[str]:
        """列出指定类型的所有资产名称。"""
        asset_dir = self.assets_base_dir / asset_type.value
        if not asset_dir.exists():
            return []
        
        extension = FILE_EXTENSIONS[asset_type]
        # 使用 .stem 获取不带扩展名的文件名
        return sorted([p.stem.replace(extension.rsplit('.', 1)[0], '') for p in asset_dir.glob(f"*{extension}")])


    def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel]) -> bytes:
        """在内存中创建一个 .hevno.zip 包并返回其字节流。"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', manifest.model_dump_json(indent=2))
            for filename, model_instance in data_files.items():
                file_content = model_instance.model_dump_json(indent=2)
                zf.writestr(f'data/{filename}', file_content)
        
        return zip_buffer.getvalue()

    def import_package(self, zip_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str]]:
        """解压包，读取清单和所有数据文件（作为原始字符串）。"""
        zip_buffer = io.BytesIO(zip_bytes)
        data_files: Dict[str, str] = {}
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            try:
                manifest_content = zf.read('manifest.json').decode('utf-8')
                manifest = PackageManifest.model_validate_json(manifest_content)
            except KeyError:
                raise ValueError("Package is missing 'manifest.json'.")
            except (ValidationError, json.JSONDecodeError) as e:
                raise ValueError(f"Invalid 'manifest.json': {e}") from e

            for item in zf.infolist():
                if item.filename.startswith('data/') and not item.is_dir():
                    relative_path = item.filename.split('data/', 1)[1]
                    data_files[relative_path] = zf.read(item).decode('utf-8')
        
        return manifest, data_files
```

### core_persistence/models.py
```
# plugins/core_persistence/models.py

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# --- 文件约定 ---
class AssetType(str, Enum):
    GRAPH = "graph"
    CODEX = "codex"
    SANDBOX = "sandbox"

FILE_EXTENSIONS = {
    AssetType.GRAPH: ".graph.hevno.json",
    AssetType.CODEX: ".codex.hevno.json",
}

# --- 插件占位符模型 ---
class PluginRequirement(BaseModel):
    name: str = Field(..., description="Plugin identifier, e.g., 'hevno-dice-roller'")
    source_url: str = Field(..., description="Plugin source, e.g., 'https://github.com/user/repo'")
    version: str = Field(..., description="Compatible version or Git ref")

# --- 包清单模型 ---
class PackageType(str, Enum):
    SANDBOX_ARCHIVE = "sandbox_archive"
    GRAPH_COLLECTION = "graph_collection"
    CODEX_COLLECTION = "codex_collection"

class PackageManifest(BaseModel):
    format_version: str = Field(default="1.0")
    package_type: PackageType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_point: str
    required_plugins: List[PluginRequirement] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### core_persistence/__init__.py
```
# plugins/core_persistence/__init__.py
import os
import logging

from backend.core.contracts import Container, HookManager
from .service import PersistenceService
from .api import router as persistence_router

logger = logging.getLogger(__name__)

def _create_persistence_service() -> PersistenceService:
    """服务工厂：创建 PersistenceService 实例。"""
    assets_dir = os.getenv("HEVNO_ASSETS_DIR", "hevno_project/assets")
    return PersistenceService(assets_base_dir=assets_dir)

async def provide_router(routers: list) -> list:
    """钩子实现：提供本插件的 API 路由。"""
    routers.append(persistence_router)
    return routers

def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core_persistence 插件的注册入口。"""
    # 统一的入口消息
    logger.info("--> 正在注册 [core-persistence] 插件...")
    
    # 注册服务
    container.register("persistence_service", _create_persistence_service)
    logger.debug("服务 'persistence_service' 已注册。")
    
    # 注册钩子
    hook_manager.add_implementation("collect_api_routers", provide_router, plugin_name="core_persistence")
    logger.debug("钩子实现 'collect_api_routers' 已注册。")
    
    # 统一的成功消息
    logger.info("插件 [core-persistence] 注册成功。")
```

### core_persistence/api.py
```
# plugins/core_persistence/api.py

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
import io

from .service import PersistenceService
from .models import PackageManifest, PackageType

# 注意：为了解耦，我们不从其他插件导入模型，如 Sandbox 或 StateSnapshot
# 在实际的 API 实现中，我们将处理原始的字典或 Pydantic BaseModel

logger = logging.getLogger(__name__)

# --- 依赖注入函数 ---
# 这个函数定义了如何为请求获取 PersistenceService 实例
def get_persistence_service(request: Request) -> PersistenceService:
    # 从 app.state 获取容器，然后解析服务
    return request.app.state.container.resolve("persistence_service")

# --- API 路由 ---
router = APIRouter(prefix="/api/persistence", tags=["Core-Persistence"])

@router.get("/assets")
async def list_all_assets(
    # service: PersistenceService = Depends(get_persistence_service) # 示例
):
    # 这里的逻辑需要根据您希望如何列出资产来具体实现
    # 例如：service.list_assets(...)
    return {"message": "Asset listing endpoint for core_persistence."}


# 导入/导出功能可以像旧的 api/persistence.py 一样实现
# 这里只给出一个示例以展示路由的创建
@router.post("/package/import")
async def import_package(
    file: UploadFile = File(...),
    service: PersistenceService = Depends(get_persistence_service)
):
    logger.info(f"Received package for import: {file.filename}")
    if not file.filename.endswith(".hevno.zip"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .hevno.zip file.")
    
    zip_bytes = await file.read()
    try:
        manifest, _ = service.import_package(zip_bytes)
        # 在这里，我们可以根据 manifest 的内容，触发其他钩子来处理导入的数据
        # 例如: await hook_manager.trigger("sandbox_imported", manifest=manifest, data=data_files)
        logger.info(f"Successfully parsed package '{manifest.package_type}' created at {manifest.created_at}")
        return manifest
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### core_persistence/manifest.json
```
{
    "name": "core-persistence",
    "version": "1.0.0",
    "description": "Provides file system persistence, asset management, and package import/export.",
    "author": "Hevno Team",
    "priority": 10
}
```

### core_codex/invoke_runtime.py
```
# plugins/core_codex/invoke_runtime.py

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Set

from pydantic import ValidationError

# 从 core_engine 插件导入接口和组件
from plugins.core_engine.interfaces import RuntimeInterface
from plugins.core_engine.evaluation import evaluate_data, build_evaluation_context
from plugins.core_engine.utils import DotAccessibleDict

# 从平台核心导入数据契约
from backend.core.contracts import ExecutionContext

# 从本插件内部导入模型
from .models import CodexCollection, ActivatedEntry, TriggerMode

logger = logging.getLogger(__name__)


class InvokeRuntime(RuntimeInterface):
    """
    system.invoke 运行时的实现。
    """
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs
    ) -> Dict[str, Any]:
        # --- 0. 准备工作 ---
        from_sources = config.get("from", [])
        if not from_sources:
            return {"output": ""}

        recursion_enabled = config.get("recursion_enabled", False)
        debug_mode = config.get("debug", False)
        lock = context.shared.global_write_lock

        codices_data = context.shared.world_state.get("codices", {})
        try:
            codex_collection = CodexCollection.model_validate(codices_data).root
        except ValidationError as e:
            raise ValueError(f"Invalid codex structure in world.codices: {e}")

        # --- 1. 阶段一：选择与过滤 (Structural Evaluation) ---
        initial_pool: List[ActivatedEntry] = []
        rejected_entries_trace = []
        initial_activation_trace = []
        
        # 宏求值的上下文只需要创建一次
        structural_eval_context = build_evaluation_context(context)

        for source_config in from_sources:
            codex_name = source_config.get("codex")
            if not codex_name: 
                continue
            
            codex_model = codex_collection.get(codex_name)
            if not codex_model:
                logger.warning(f"Codex '{codex_name}' referenced in invoke config not found in world.codices.")
                continue

            source_text_macro = source_config.get("source", "")
            source_text = await evaluate_data(source_text_macro, structural_eval_context, lock) if source_text_macro else ""

            for entry in codex_model.entries:
                is_enabled = await evaluate_data(entry.is_enabled, structural_eval_context, lock)
                if not is_enabled:
                    if debug_mode:
                        rejected_entries_trace.append({"id": entry.id, "reason": "is_enabled macro returned false"})
                    continue

                keywords = await evaluate_data(entry.keywords, structural_eval_context, lock)
                priority = await evaluate_data(entry.priority, structural_eval_context, lock)

                matched_keywords = []
                is_activated = False
                if entry.trigger_mode == TriggerMode.ALWAYS_ON:
                    is_activated = True
                elif entry.trigger_mode == TriggerMode.ON_KEYWORD and source_text and keywords:
                    for keyword in keywords:
                        # 确保 keyword 是字符串以进行正则匹配
                        if re.search(re.escape(str(keyword)), str(source_text), re.IGNORECASE):
                            matched_keywords.append(keyword)
                    if matched_keywords:
                        is_activated = True
                
                if is_activated:
                    activated = ActivatedEntry(
                        entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                        priority_val=int(priority), keywords_val=keywords, is_enabled_val=bool(is_enabled),
                        source_text=str(source_text), matched_keywords=matched_keywords
                    )
                    initial_pool.append(activated)
                    if debug_mode:
                        initial_activation_trace.append({
                            "id": entry.id, "priority": int(priority),
                            "reason": entry.trigger_mode.value,
                            "matched_keywords": matched_keywords
                        })
        
        # --- 2. 阶段二：渲染与注入 (Content Evaluation) ---
        final_text_parts = []
        rendered_entry_ids: Set[str] = set()
        rendering_pool = sorted(initial_pool, key=lambda x: x.priority_val, reverse=True)
        
        # Debugging trace lists
        evaluation_log = []
        recursive_activations = []

        # 确定最大递归深度
        max_depth = max((act.codex_config.recursion_depth for act in rendering_pool), default=3) if rendering_pool else 3

        recursion_level = 0
        while rendering_pool and (not recursion_enabled or recursion_level < max_depth):
            
            rendering_pool.sort(key=lambda x: x.priority_val, reverse=True)
            entry_to_render = rendering_pool.pop(0)

            if entry_to_render.entry_model.id in rendered_entry_ids:
                continue
            
            # 为内容求值创建上下文，包含特殊的 'trigger' 对象
            content_eval_context = build_evaluation_context(context)
            content_eval_context['trigger'] = DotAccessibleDict({
                "source_text": entry_to_render.source_text,
                "matched_keywords": entry_to_render.matched_keywords
            })

            rendered_content = str(await evaluate_data(entry_to_render.entry_model.content, content_eval_context, lock))
            
            final_text_parts.append(rendered_content)
            rendered_entry_ids.add(entry_to_render.entry_model.id)
            if debug_mode:
                evaluation_log.append({"id": entry_to_render.entry_model.id, "status": "rendered", "level": recursion_level})
            
            if recursion_enabled:
                recursion_level += 1
                new_source_text = rendered_content
                
                # 遍历所有法典，寻找可被新内容递归触发的条目
                for codex_name, codex_model in codex_collection.items():
                    for entry in codex_model.entries:
                        # 跳过已处理或已在队列中的条目
                        if entry.id in rendered_entry_ids or any(p.entry_model.id == entry.id for p in rendering_pool):
                            continue
                        
                        # 递归只对关键词模式有效
                        if entry.trigger_mode == TriggerMode.ON_KEYWORD:
                            is_enabled = await evaluate_data(entry.is_enabled, structural_eval_context, lock)
                            if not is_enabled: 
                                continue

                            keywords = await evaluate_data(entry.keywords, structural_eval_context, lock)
                            new_matched_keywords = [kw for kw in keywords if re.search(re.escape(str(kw)), new_source_text, re.IGNORECASE)]
                            
                            if new_matched_keywords:
                                priority = await evaluate_data(entry.priority, structural_eval_context, lock)
                                activated = ActivatedEntry(
                                    entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                                    priority_val=int(priority), keywords_val=keywords, is_enabled_val=is_enabled,
                                    source_text=new_source_text, matched_keywords=new_matched_keywords
                                )
                                rendering_pool.append(activated)
                                if debug_mode:
                                    recursive_activations.append({
                                        "id": entry.id, "priority": int(priority), "level": recursion_level,
                                        "reason": "recursive_keyword_match", "triggered_by": entry_to_render.entry_model.id
                                    })
        
        # --- 3. 构造输出 ---
        final_text = "\n\n".join(final_text_parts)
        
        if debug_mode:
            trace_data = {
                "initial_activation": initial_activation_trace,
                "recursive_activations": recursive_activations,
                "evaluation_log": evaluation_log,
                "rejected_entries": rejected_entries_trace,
            }
            return { "output": { "final_text": final_text, "trace": trace_data } }
        
        return {"output": final_text}
```

### core_codex/models.py
```
# plugins/core_codex/models.py
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator

class TriggerMode(str, Enum):
    ALWAYS_ON = "always_on"
    ON_KEYWORD = "on_keyword"

class CodexEntry(BaseModel):
    """定义单个知识条目的结构。"""
    id: str
    content: str  # [Macro]
    is_enabled: Any = Field(default=True)  # [Macro] bool or str
    trigger_mode: TriggerMode = Field(default=TriggerMode.ALWAYS_ON)
    keywords: Any = Field(default_factory=list)  # [Macro] List[str] or str
    priority: Any = Field(default=0)  # [Macro] int or str
    
    model_config = ConfigDict(extra='forbid') # 确保没有多余字段

class CodexConfig(BaseModel):
    """定义单个法典级别的配置。"""
    recursion_depth: int = Field(default=3, ge=0, description="此法典参与递归时的最大深度。")
    
    model_config = ConfigDict(extra='forbid')

class Codex(BaseModel):
    """定义一个完整的法典。"""
    description: Optional[str] = None
    config: CodexConfig = Field(default_factory=CodexConfig)
    entries: List[CodexEntry]
    metadata: Dict[str, Any] = Field(default_factory=dict) 

    model_config = ConfigDict(extra='forbid')

class CodexCollection(RootModel[Dict[str, Codex]]):
    """
    代表 world.codices 的顶层结构。
    模型本身是一个 `Dict[str, Codex]`。
    """
    pass

# 用于运行时内部处理的数据结构
class ActivatedEntry(BaseModel):
    entry_model: CodexEntry
    codex_name: str
    codex_config: CodexConfig
    
    # 结构性宏求值后的结果
    priority_val: int
    keywords_val: List[str]
    is_enabled_val: bool
    
    # 触发信息
    source_text: str
    matched_keywords: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
```

### core_codex/__init__.py
```
# plugins/core_codex/__init__.py
import logging
from backend.core.contracts import Container, HookManager

from .invoke_runtime import InvokeRuntime

logger = logging.getLogger(__name__)

# --- 钩子实现 ---
async def register_codex_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的 'system.invoke' 运行时。"""
    runtimes["system.invoke"] = InvokeRuntime
    logger.debug("Runtime 'system.invoke' provided to runtime registry.")
    return runtimes

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-codex] 插件...")

    # 本插件只提供运行时，不注册服务。
    # 它通过钩子与 core-engine 通信。
    hook_manager.add_implementation(
        "collect_runtimes", 
        register_codex_runtime, 
        plugin_name="core-codex"
    )
    logger.debug("钩子实现 'collect_runtimes' 已注册。")

    logger.info("插件 [core-codex] 注册成功。")
```

### core_codex/manifest.json
```
{
    "name": "core-codex",
    "version": "1.0.0",
    "description": "Provides the Codex knowledge base system and the 'system.invoke' runtime.",
    "author": "Hevno Team",
    "priority": 30,
    "dependencies": ["core-engine"]
}
```

### core_engine/interfaces.py
```
# plugins/core_engine/interfaces.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# 从平台核心导入共享的数据契约
from backend.core.contracts import ExecutionContext

class SubGraphRunner(ABC):
    """定义执行子图能力的抽象接口。"""
    @abstractmethod
    async def execute_graph(
        self,
        graph_name: str,
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

class RuntimeInterface(ABC):
    """定义所有运行时必须实现的接口。"""
    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        subgraph_runner: Optional[SubGraphRunner] = None,
        pipeline_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass
```

### core_engine/models.py
```
# plugins/core_engine/models.py
from pydantic import BaseModel, Field, RootModel, field_validator
from typing import List, Dict, Any, Optional # <-- 导入 Optional

class RuntimeInstruction(BaseModel):
    """
    一个运行时指令，封装了运行时名称及其隔离的配置。
    这是节点执行逻辑的基本单元。
    """
    runtime: str
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="该运行时专属的、隔离的配置字典。"
    )

class GenericNode(BaseModel):
    """
    节点模型，现在以一个有序的运行时指令列表为核心。
    """
    id: str
    run: List[RuntimeInstruction] = Field(
        ...,
        description="定义节点执行逻辑的有序指令列表。"
    )
    depends_on: Optional[List[str]] = Field(
        default=None,
        description="一个可选的列表，用于明确声明此节点在执行前必须等待的其他节点的ID。用于处理无法通过宏自动推断的隐式依赖。"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphDefinition(BaseModel):
    """图定义，包含一个节点列表。"""
    nodes: List[GenericNode]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    """
    整个配置文件的顶层模型。
    使用 RootModel，模型本身就是一个 `Dict[str, GraphDefinition]`。
    """
    
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        """验证器，确保存在一个 'main' 图作为入口点。"""
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v
```

### core_engine/registry.py
```
# plugins/core_engine/registry.py

from typing import Dict, Type, Callable
import logging

# --- 核心修改: 导入路径本地化 ---
from .interfaces import RuntimeInterface

logger = logging.getLogger(__name__)

class RuntimeRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    # --- 核心修改: 这是一个常规方法，不再是装饰器工厂 ---
    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        """
        向注册表注册一个运行时类。
        """
        if name in self._registry:
            logger.warning(f"Overwriting runtime registration for '{name}'.")
        self._registry[name] = runtime_class
        logger.debug(f"Runtime '{name}' registered to the registry.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        """
        获取一个运行时的【新实例】。
        """
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime '{name}' not found in registry.")
        return runtime_class()


```

### core_engine/evaluation.py
```
# plugins/core_engine/evaluation.py

import ast
import asyncio
import re
from typing import Any, Dict, List, Optional   
from functools import partial
import random
import math
import datetime
import json
import re as re_module

from .utils import DotAccessibleDict
from backend.core.contracts import ExecutionContext

INLINE_MACRO_REGEX = re.compile(r"{{\s*(.+?)\s*}}", re.DOTALL)
MACRO_REGEX = re.compile(r"^{{\s*(.+)\s*}}$", re.DOTALL)
import random
import math
import datetime
import json
import re as re_module

PRE_IMPORTED_MODULES = {
    "random": random,
    "math": math,
    "datetime": datetime,
    "json": json,
    "re": re_module,
}

def build_evaluation_context(
    exec_context: ExecutionContext,
    pipe_vars: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    从 ExecutionContext 构建宏的执行环境。
    这个函数现在变得非常简单，因为它信任传入的上下文。
    """
    context = {
        **PRE_IMPORTED_MODULES,
        # 直接从共享上下文中获取 world 和 session
        "world": DotAccessibleDict(exec_context.shared.world_state),
        "session": DotAccessibleDict(exec_context.shared.session_info),
        # run 和 nodes 是当前图执行所私有的
        "run": DotAccessibleDict(exec_context.run_vars),
        "nodes": DotAccessibleDict(exec_context.node_states),
    }
    if pipe_vars is not None:
        context['pipe'] = DotAccessibleDict(pipe_vars)
        
    return context

async def evaluate_expression(code_str: str, context: Dict[str, Any], lock: asyncio.Lock) -> Any:
    """..."""
    # ast.parse 可能会失败，需要 try...except
    try:
        tree = ast.parse(code_str, mode='exec')
    except SyntaxError as e:
        raise ValueError(f"Macro syntax error: {e}\nCode: {code_str}")

    # 如果代码块为空，直接返回 None
    if not tree.body:
        return None

    # 如果最后一行是表达式，我们将其转换为一个赋值语句，以便捕获结果
    result_var = "_macro_result"
    if isinstance(tree.body[-1], ast.Expr):
        # 包装最后一条表达式
        assign_node = ast.Assign(
            targets=[ast.Name(id=result_var, ctx=ast.Store())],
            value=tree.body[-1].value
        )
        tree.body[-1] = ast.fix_missing_locations(assign_node)
    
    # 将 AST 编译为代码对象
    code_obj = compile(tree, filename="<macro>", mode="exec")
    
    # 在锁的保护下运行
    async with lock:
        # 在另一个线程中运行，以避免阻塞事件循环
        # 注意：这里我们直接修改传入的 context 字典来捕获结果
        await asyncio.get_running_loop().run_in_executor(
            None, exec, code_obj, context
        )
    
    # 从被修改的上下文字典中获取结果
    return context.get(result_var)

async def evaluate_data(data: Any, eval_context: Dict[str, Any], lock: asyncio.Lock) -> Any:
    if isinstance(data, str):
        # 模式1: 检查是否为“全宏替换”
        # 这种模式很重要，因为它允许宏返回非字符串类型（如列表、布尔值）
        full_match = MACRO_REGEX.match(data)
        if full_match:
            code_to_run = full_match.group(1)
            # 这里返回的结果可以是任何类型
            return await evaluate_expression(code_to_run, eval_context, lock)

        # 模式2: 如果不是全宏，检查是否包含“内联模板”
        # 这种模式的结果总是字符串
        if '{{' in data and '}}' in data:
            matches = list(INLINE_MACRO_REGEX.finditer(data))
            if not matches:
                # 包含 {{ 和 }} 但格式不正确，按原样返回
                return data

            # 并发执行所有宏的求值
            codes_to_run = [m.group(1) for m in matches]
            tasks = [evaluate_expression(code, eval_context, lock) for code in codes_to_run]
            evaluated_results = await asyncio.gather(*tasks)

            # 将求值结果替换回原字符串
            # 使用一个迭代器来确保替换顺序正确
            results_iter = iter(evaluated_results)
            # re.sub 的 lambda 每次调用时，都会从迭代器中取下一个结果
            # 这比多次调用 str.replace() 更安全、更高效
            final_string = INLINE_MACRO_REGEX.sub(lambda m: str(next(results_iter)), data)
            
            return final_string

        # 如果两种模式都不匹配，说明是普通字符串
        return data

    if isinstance(data, dict):
        keys = list(data.keys())
        # 创建异步任务列表
        value_tasks = [evaluate_data(data[k], eval_context, lock) for k in keys]
        # 并发执行所有值的求值
        evaluated_values = await asyncio.gather(*value_tasks)
        # 重新组装字典
        return dict(zip(keys, evaluated_values))

    if isinstance(data, list):
        # 并发执行列表中所有项的求值
        item_tasks = [evaluate_data(item, eval_context, lock) for item in data]
        return await asyncio.gather(*item_tasks)

    return data
```

### core_engine/__init__.py
```
# plugins/core_engine/__init__.py

import logging
from typing import Dict, Type

from backend.core.contracts import Container, HookManager
from .engine import ExecutionEngine
from .registry import RuntimeRegistry
from .state import SnapshotStore
from .interfaces import RuntimeInterface
from .runtimes.base_runtimes import InputRuntime, SetWorldVariableRuntime
from .runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime

logger = logging.getLogger(__name__)

# --- 服务工厂 ---

def _create_runtime_registry() -> RuntimeRegistry:
    """工厂：仅创建 RuntimeRegistry 的【空】实例，并注册内置运行时。"""
    registry = RuntimeRegistry()
    logger.debug("RuntimeRegistry instance created.")

    base_runtimes: Dict[str, Type[RuntimeInterface]] = {
        "system.input": InputRuntime,
        "system.set_world_var": SetWorldVariableRuntime,
        "system.execute": ExecuteRuntime,
        "system.call": CallRuntime,
        "system.map": MapRuntime,
    }
    for name, runtime_class in base_runtimes.items():
        registry.register(name, runtime_class)
    logger.info(f"Registered {len(base_runtimes)} built-in system runtimes.")
    return registry

def _create_execution_engine(container: Container) -> ExecutionEngine:
    """工厂：创建执行引擎，并注入其所有依赖。"""
    logger.debug("Creating ExecutionEngine instance...")
    return ExecutionEngine(
        registry=container.resolve("runtime_registry"),
        container=container,
        hook_manager=container.resolve("hook_manager")
    )

# --- 钩子实现 ---
async def populate_runtime_registry(container: Container):
    """
    【新】钩子实现：监听应用启动事件，【异步地】收集并填充运行时注册表。
    """
    logger.debug("Async task: Populating runtime registry from other plugins...")
    hook_manager = container.resolve("hook_manager")
    registry = container.resolve("runtime_registry")

    external_runtimes: Dict[str, Type[RuntimeInterface]] = await hook_manager.filter("collect_runtimes", {})
    
    if not external_runtimes:
        logger.info("No external runtimes discovered from other plugins.")
        return

    logger.info(f"Discovered {len(external_runtimes)} external runtime(s): {list(external_runtimes.keys())}")
    for name, runtime_class in external_runtimes.items():
        registry.register(name, runtime_class)

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-engine] 插件...")

    container.register("snapshot_store", lambda: SnapshotStore(), singleton=True)
    container.register("sandbox_store", lambda: {}, singleton=True)
    
    # 注册工厂，它只做同步部分
    container.register("runtime_registry", _create_runtime_registry, singleton=True)
    container.register("execution_engine", _create_execution_engine, singleton=True)
    
    # 【新】注册一个监听器，它将在应用启动的异步阶段被调用
    hook_manager.add_implementation(
        "services_post_register", 
        populate_runtime_registry, 
        plugin_name="core-engine"
    )

    logger.info("插件 [core-engine] 注册成功。")
```

### core_engine/base_runtimes.py
```
# plugins/core_engine/runtimes/base_runtimes.py

import logging
from typing import Dict, Any


from ..interfaces import RuntimeInterface
from backend.core.contracts import ExecutionContext

logger = logging.getLogger(__name__)


class InputRuntime(RuntimeInterface):
    """从 config 中获取 'value'。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value", "")}


class SetWorldVariableRuntime(RuntimeInterface):
    """从 config 中获取变量名和值，并设置一个持久化的世界变量。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        variable_name = config.get("variable_name")
        value_to_set = config.get("value")

        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name' in its config.")
        
        logger.debug(f"Setting world_state['{variable_name}'] to: {value_to_set}")
        context.shared.world_state[variable_name] = value_to_set
        
        return {}
```

### core_engine/control_runtimes.py
```
# plugins/core_engine/runtimes/control_runtimes.py

from typing import Dict, Any, List, Optional
import asyncio


from ..interfaces import RuntimeInterface, SubGraphRunner
from ..evaluation import evaluate_data, evaluate_expression, build_evaluation_context
from ..utils import DotAccessibleDict
from backend.core.contracts import ExecutionContext


class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        code_to_execute = config.get("code")

        if not isinstance(code_to_execute, str):
            return {"output": code_to_execute}

        eval_context = build_evaluation_context(context)
        # --- 修正: 从共享上下文中获取并传递锁 ---
        lock = context.shared.global_write_lock
        result = await evaluate_expression(code_to_execute, eval_context, lock)
        return {"output": result}


class CallRuntime(RuntimeInterface):
    """执行一个子图。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("CallRuntime requires a SubGraphRunner.")
            
        graph_name = config.get("graph")
        using_inputs = config.get("using", {})
        
        inherited_inputs = {
            placeholder_name: {"output": value}
            for placeholder_name, value in using_inputs.items()
        }

        # 调用 subgraph_runner，它会负责创建正确的子上下文
        subgraph_results = await subgraph_runner.execute_graph(
            graph_name=graph_name,
            parent_context=context, # 传递当前的上下文
            inherited_inputs=inherited_inputs
        )
        
        return {"output": subgraph_results}


class MapRuntime(RuntimeInterface):
    """并行迭代。"""
    template_fields = ["using", "collect"]

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("MapRuntime requires a SubGraphRunner.")

        list_to_iterate = config.get("list")
        graph_name = config.get("graph")
        using_template = config.get("using", {})
        collect_template = config.get("collect")

        if not isinstance(list_to_iterate, list):
            raise TypeError(f"system.map 'list' field must be a list...")

        tasks = []
        base_eval_context = build_evaluation_context(context)
        lock = context.shared.global_write_lock

        for index, item in enumerate(list_to_iterate):
            # a. 创建包含 `source` 的临时上下文，用于求值 `using`
            using_eval_context = {
                **base_eval_context,
                "source": DotAccessibleDict({"item": item, "index": index})
            }
            
            # b. 求值 `using` 字典 (需要传递锁)
            evaluated_using = await evaluate_data(using_template, using_eval_context, lock)
            inherited_inputs = {
                placeholder: {"output": value}
                for placeholder, value in evaluated_using.items()
            }
            
            # c. 创建子图执行任务
            #    subgraph_runner.execute_graph 会处理子上下文的创建
            task = asyncio.create_task(
                subgraph_runner.execute_graph(
                    graph_name=graph_name,
                    parent_context=context,
                    inherited_inputs=inherited_inputs
                )
            )
            tasks.append(task)
        
        subgraph_results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        
        # d. 聚合阶段
        if collect_template:
            collected_outputs = []
            for result in subgraph_results:
                # `nodes` 指向当前子图的结果
                collect_eval_context = build_evaluation_context(context)
                collect_eval_context["nodes"] = DotAccessibleDict(result)
                
                collected_value = await evaluate_data(collect_template, collect_eval_context, lock)
                collected_outputs.append(collected_value)
            
            return {"output": collected_outputs}
        else:
            return {"output": subgraph_results}
```

### core_engine/engine.py
```
# plugins/core_engine/engine.py 

import asyncio
import logging
from enum import Enum, auto
from typing import Dict, Any, Set, List, Optional
from collections import defaultdict
import traceback

from backend.core.contracts import (
    GraphCollection, GraphDefinition, GenericNode, Container,
    ExecutionContext,
    EngineStepStartContext, EngineStepEndContext,
    BeforeConfigEvaluationContext, AfterMacroEvaluationContext,
    NodeExecutionStartContext, NodeExecutionSuccessContext, NodeExecutionErrorContext,
    HookManager
)
from .dependency_parser import build_dependency_graph_async
from .registry import RuntimeRegistry
from .evaluation import build_evaluation_context, evaluate_data
from .state import (
    create_main_execution_context, 
    create_sub_execution_context, 
    create_next_snapshot
)
from .interfaces import RuntimeInterface, SubGraphRunner

logger = logging.getLogger(__name__)

class NodeState(Enum):
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    SKIPPED = auto()

class GraphRun:
    def __init__(self, context: ExecutionContext, graph_def: GraphDefinition):
        self.context = context
        self.graph_def = graph_def
        if not self.graph_def:
            raise ValueError("GraphRun must be initialized with a valid GraphDefinition.")
        self.node_map: Dict[str, GenericNode] = {n.id: n for n in self.graph_def.nodes}
        self.node_states: Dict[str, NodeState] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.subscribers: Dict[str, Set[str]] = {}

    @classmethod
    async def create(cls, context: ExecutionContext, graph_def: GraphDefinition) -> "GraphRun":
        run = cls(context, graph_def)
        run.dependencies = await build_dependency_graph_async(
            [node.model_dump() for node in run.graph_def.nodes],
            context.hook_manager
        )
        run.subscribers = run._build_subscribers()
        run._detect_cycles()
        run._initialize_node_states()
        return run

    def _build_subscribers(self) -> Dict[str, Set[str]]:
        subscribers = defaultdict(set)
        for node_id, deps in self.dependencies.items():
            for dep_id in deps:
                subscribers[dep_id].add(node_id)
        return subscribers

    def _detect_cycles(self):
        path = set()
        visited = set()
        def visit(node_id):
            path.add(node_id)
            visited.add(node_id)
            for neighbour in self.dependencies.get(node_id, set()):
                if neighbour in path:
                    raise ValueError(f"Cycle detected involving node {neighbour}")
                if neighbour not in visited:
                    visit(neighbour)
            path.remove(node_id)
        for node_id in self.node_map:
            if node_id not in visited:
                visit(node_id)

    def _initialize_node_states(self):
        for node_id in self.node_map:
            if not self.dependencies.get(node_id):
                self.node_states[node_id] = NodeState.READY
            else:
                self.node_states[node_id] = NodeState.PENDING

    def get_node(self, node_id: str) -> GenericNode:
        return self.node_map[node_id]
    def get_node_state(self, node_id: str) -> NodeState:
        return self.node_states.get(node_id)
    def set_node_state(self, node_id: str, state: NodeState):
        self.node_states[node_id] = state
    def get_node_result(self, node_id: str) -> Dict[str, Any]:
        return self.context.node_states.get(node_id)
    def set_node_result(self, node_id: str, result: Dict[str, Any]):
        self.context.node_states[node_id] = result
    def get_nodes_in_state(self, state: NodeState) -> List[str]:
        return [nid for nid, s in self.node_states.items() if s == state]
    def get_dependencies(self, node_id: str) -> Set[str]:
        return self.dependencies.get(node_id, set())
    def get_subscribers(self, node_id: str) -> Set[str]:
        return self.subscribers.get(node_id, set())
    def get_execution_context(self) -> ExecutionContext:
        return self.context
    def get_final_node_states(self) -> Dict[str, Any]:
        return self.context.node_states

class ExecutionEngine(SubGraphRunner):
    def __init__(
        self,
        registry: RuntimeRegistry,
        container: Container,
        hook_manager: HookManager,
        num_workers: int = 5
    ):
        self.registry = registry
        self.container = container
        self.hook_manager = hook_manager
        self.num_workers = num_workers
        
    async def step(self, initial_snapshot, triggering_input: Dict[str, Any] = None):
        if triggering_input is None: triggering_input = {}
        
        await self.hook_manager.trigger(
            "engine_step_start",
            context=EngineStepStartContext(
                initial_snapshot=initial_snapshot,
                triggering_input=triggering_input
            )
        )
        
        context = create_main_execution_context(
            snapshot=initial_snapshot,
            container=self.container,
            run_vars={"triggering_input": triggering_input},
            hook_manager=self.hook_manager
        )

        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def: raise ValueError("'main' graph not found.")
        
        final_node_states = await self._internal_execute_graph(main_graph_def, context)
        
        next_snapshot = await create_next_snapshot(
            context=context, 
            final_node_states=final_node_states, 
            triggering_input=triggering_input
        )

        await self.hook_manager.trigger(
            "engine_step_end",
            context=EngineStepEndContext(final_snapshot=next_snapshot)
        )

        return next_snapshot

    async def execute_graph(
        self,
        graph_name: str,
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        graph_collection = parent_context.initial_snapshot.graph_collection.root
        graph_def = graph_collection.get(graph_name)
        if not graph_def:
            raise ValueError(f"Graph '{graph_name}' not found.")
        
        sub_run_context = create_sub_execution_context(parent_context)

        return await self._internal_execute_graph(
            graph_def=graph_def,
            context=sub_run_context,
            inherited_inputs=inherited_inputs
        )

    async def _internal_execute_graph(self, graph_def: GraphDefinition, context: ExecutionContext, inherited_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        run = await GraphRun.create(context=context, graph_def=graph_def)
        task_queue = asyncio.Queue()
        
        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, result)
        
        for node_id in run.get_nodes_in_state(NodeState.PENDING):
            dependencies = run.get_dependencies(node_id)
            if all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in dependencies):
                run.set_node_state(node_id, NodeState.READY)
        
        for node_id in run.get_nodes_in_state(NodeState.READY):
            task_queue.put_nowait(node_id)

        if task_queue.empty() and not any(s == NodeState.SUCCEEDED for s in run.node_states.values()):
            return {}

        workers = [
            asyncio.create_task(self._worker(f"worker-{i}", run, task_queue))
            for i in range(self.num_workers)
        ]
        
        await task_queue.join()

        for w in workers:
            w.cancel()
        
        await asyncio.gather(*workers, return_exceptions=True)
        
        final_states = {
            nid: run.get_node_result(nid)
            for nid, n in run.node_map.items()
            if run.get_node_result(nid) is not None
        }
        return final_states

    async def _worker(self, name: str, run: 'GraphRun', queue: asyncio.Queue):
        while True:
            try:
                node_id = await queue.get()
            except asyncio.CancelledError:
                break

            run.set_node_state(node_id, NodeState.RUNNING)
            try:
                node = run.get_node(node_id)
                context = run.get_execution_context()

                await self.hook_manager.trigger(
                    "node_execution_start",
                    context=NodeExecutionStartContext(node=node, execution_context=context)
                )
                output = await self._execute_node(node, context)
                if isinstance(output, dict) and "error" in output:
                    run.set_node_state(node_id, NodeState.FAILED)

                    await self.hook_manager.trigger(
                        "node_execution_error",
                        context=NodeExecutionErrorContext(
                            node=node,
                            execution_context=context,
                            exception=ValueError(output["error"])
                        )
                    )
                else:
                    run.set_node_state(node_id, NodeState.SUCCEEDED)

                    await self.hook_manager.trigger(
                        "node_execution_success",
                        context=NodeExecutionSuccessContext(
                            node=node,
                            execution_context=context,
                            result=output
                        )
                    )
                run.set_node_result(node_id, output)
            except Exception as e:
                error_message = f"Worker-level error for node {node_id}: {type(e).__name__}: {e}"
                import traceback
                traceback.print_exc()
                run.set_node_state(node_id, NodeState.FAILED)
                run.set_node_result(node_id, {"error": error_message})

                await self.hook_manager.trigger(
                    "node_execution_error",
                    context=NodeExecutionErrorContext(
                        node=node,
                        execution_context=context,
                        exception=e
                    )
                )
            self._process_subscribers(node_id, run, queue)
            queue.task_done()

    def _process_subscribers(self, completed_node_id: str, run: 'GraphRun', queue: asyncio.Queue):
        completed_node_state = run.get_node_state(completed_node_id)
        for sub_id in run.get_subscribers(completed_node_id):
            if run.get_node_state(sub_id) != NodeState.PENDING:
                continue
            if completed_node_state == NodeState.FAILED:
                run.set_node_state(sub_id, NodeState.SKIPPED)
                run.set_node_result(sub_id, {"status": "skipped", "reason": f"Upstream failure of node {completed_node_id}."})
                self._process_subscribers(sub_id, run, queue)
                continue
            dependencies = run.get_dependencies(sub_id)
            is_ready = all(
                (dep_id not in run.node_map) or (run.get_node_state(dep_id) == NodeState.SUCCEEDED)
                for dep_id in dependencies
            )
            if is_ready:
                run.set_node_state(sub_id, NodeState.READY)
                queue.put_nowait(sub_id)

    async def _execute_node(self, node: GenericNode, context: ExecutionContext) -> Dict[str, Any]:
        pipeline_state: Dict[str, Any] = {}
        if not node.run: return {}
        
        lock = context.shared.global_write_lock

        for i, instruction in enumerate(node.run):
            runtime_name = instruction.runtime
            try:
                eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
                
                config_to_process = instruction.config.copy()

                config_to_process = await self.hook_manager.filter(
                    "before_config_evaluation",
                    config_to_process,
                    context=BeforeConfigEvaluationContext(
                        node=node,
                        execution_context=context,
                        instruction_config=config_to_process
                    )
                )

                runtime_instance: RuntimeInterface = self.registry.get_runtime(runtime_name)
                
                templates = {}
                template_fields = getattr(runtime_instance, 'template_fields', [])
                for field in template_fields:
                    if field in config_to_process:
                        templates[field] = config_to_process.pop(field)

                processed_config = await evaluate_data(config_to_process, eval_context, lock)

                processed_config = await self.hook_manager.filter(
                    "after_macro_evaluation",
                    processed_config,
                    context=AfterMacroEvaluationContext(
                        node=node,
                        execution_context=context,
                        evaluated_config=processed_config
                    )
                )

                if templates:
                    processed_config.update(templates)

                output = await runtime_instance.execute(
                    config=processed_config,
                    context=context,
                    subgraph_runner=self,
                    pipeline_state=pipeline_state
                )
                
                if not isinstance(output, dict):
                    error_message = f"Runtime '{runtime_name}' did not return a dictionary. Got: {type(output).__name__}"
                    return {"error": error_message, "failed_step": i, "runtime": runtime_name}
                pipeline_state.update(output)
            except Exception as e:
                import traceback
                traceback.print_exc()
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {type(e).__name__}: {e}"
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}
        return pipeline_state

def get_engine(request: Request) -> ExecutionEngine:
    return request.app.state.engine

```

### core_engine/utils.py
```
# plugins/core_engine/utils.py

from typing import Any, Dict
from backend.core.contracts import Container

class DotAccessibleDict:
    """
    一个【递归】代理类，它包装一个字典，并允许通过点符号进行属性访问。
    【关键修正】所有读取和写入操作都会直接作用于原始的底层字典。
    """
    def __init__(self, data: Dict[str, Any]):
        # 不再使用 object.__setattr__，而是直接存储引用。
        # Pydantic的BaseModel等复杂对象可能需要它，但我们这里用于简单字典，
        # 直接存储引用更清晰。
        self._data = data

    @classmethod
    def _wrap(cls, value: Any) -> Any:
        """递归包装值。如果值是字典，包装它；如果是列表，递归包装其内容。"""
        if isinstance(value, dict):
            return cls(value)
        if isinstance(value, list):
            # 列表本身不被包装，但其内容需要递归检查
            return [cls._wrap(item) for item in value]
        return value

    def __contains__(self, key: str) -> bool:
        """
        当执行 `key in obj` 时调用。
        直接代理到底层字典的 `in` 操作。
        """
        return key in self._data

    def __getattr__(self, name: str) -> Any:
        """
        当访问 obj.key 时调用。
        【核心修正】如果 'name' 不是 _data 的键，则检查它是否是 _data 的一个可调用方法 (如 .get, .keys)。
        """
        if name.startswith('__'):  # 避免代理魔术方法
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            
        try:
            # 优先检查底层字典中是否存在该键
            value = self._data[name]
            return self._wrap(value)
        except KeyError:
            # 如果键不存在，检查底层字典是否有一个同名的方法
            underlying_attr = getattr(self._data, name, None)
            if callable(underlying_attr):
                return underlying_attr  # 返回该方法本身，以便可以被调用
            
            # 如果都不是，则抛出异常
            raise AttributeError(f"'{type(self).__name__}' object has no attribute or method '{name}'")

    def __setattr__(self, name: str, value: Any):
        """当执行 obj.key = value 时调用。"""
        # --- 核心修正 ---
        # 如果 name 是 `_data`，就设置实例属性，否则直接修改底层字典。
        if name == '_data':
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __delattr__(self, name: str):
        """当执行 del obj.key 时调用。"""
        try:
            del self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # 保持辅助方法不变
    def __repr__(self) -> str:
        return f"DotAccessibleDict({self._data})"
    
    def __getitem__(self, key):
        return self._wrap(self._data[key])
    
    def __setitem__(self, key, value):
        self._data[key] = value

class ServiceResolverProxy:
    """
    一个代理类，它包装一个 DI 容器，使其表现得像一个字典。
    这使得宏系统可以通过 `services.service_name` 语法懒加载并访问容器中的服务。
    """
    def __init__(self, container: Container):
        """
        :param container: 要代理的 DI 容器实例。
        """
        self._container = container
        # 创建一个简单的缓存，避免对同一个单例服务重复调用 resolve
        self._cache: dict = {}

    def __getitem__(self, name: str):
        """
        这是核心魔法所在。当代码执行 `proxy['service_name']` 时，此方法被调用。
        """
        # 1. 检查缓存中是否已有该服务实例
        if name in self._cache:
            return self._cache[name]
        
        # 2. 如果不在缓存中，调用容器的 resolve 方法来创建或获取服务
        #    如果服务不存在，container.resolve 会抛出 ValueError，这是我们期望的行为。
        service_instance = self._container.resolve(name)
        
        # 3. 将解析出的服务实例存入缓存
        self._cache[name] = service_instance
        
        # 4. 返回服务实例
        return service_instance

    def get(self, key: str, default=None):
        """
        实现 .get() 方法，使其行为与标准字典一致。
        这对于某些工具（包括 DotAccessibleDict 的某些行为）来说很有用。
        """
        try:
            return self.__getitem__(key)
        except (ValueError, KeyError):
            # 如果 resolve 失败（服务未注册），则返回默认值
            return default

    def keys(self):
        """
        (可选) 实现 .keys() 方法。
        这可以让调试时（如 `list(services.keys())`）看到所有可用的服务。
        """
        # 直接返回容器中所有已注册工厂的名称
        return self._container._factories.keys()
    
    def __contains__(self, key: str) -> bool:
        """实现 `in` 操作符，例如 `if 'llm_service' in services:`"""
        return key in self._container._factories
```

### core_engine/manifest.json
```
{
    "name": "core-engine",
    "version": "1.0.0",
    "description": "Provides the graph parsing, scheduling, and execution engine.",
    "author": "Hevno Team",
    "priority": 50
}
```

### core_engine/dependency_parser.py
```
# plugins/core_engine/dependency_parser.py
import re
from typing import Set, Dict, Any, List
import asyncio


from backend.core.contracts import HookManager, ResolveNodeDependenciesContext, GenericNode


NODE_DEP_REGEX = re.compile(r'nodes\.([a-zA-Z0-9_]+)')

def extract_dependencies_from_string(s: str) -> Set[str]:
    if not isinstance(s, str):
        return set()
    if '{{' in s and '}}' in s and 'nodes.' in s:
        return set(NODE_DEP_REGEX.findall(s))
    return set()

def extract_dependencies_from_value(value: Any) -> Set[str]:
    deps = set()
    if isinstance(value, str):
        deps.update(extract_dependencies_from_string(value))
    elif isinstance(value, list):
        for item in value:
            deps.update(extract_dependencies_from_value(item))
    elif isinstance(value, dict):
        for k, v in value.items():
            deps.update(extract_dependencies_from_value(k))
            deps.update(extract_dependencies_from_value(v))
    return deps

async def build_dependency_graph_async(
    nodes: List[Dict[str, Any]],
    hook_manager: HookManager
) -> Dict[str, Set[str]]:
    dependency_map: Dict[str, Set[str]] = {}
    
    # 将所有节点字典预先转换为 Pydantic 模型实例，以便在钩子中使用
    node_map: Dict[str, GenericNode] = {node_dict['id']: GenericNode.model_validate(node_dict) for node_dict in nodes}

    for node_dict in nodes:
        node_id = node_dict['id']
        
        # 【核心修复】通过 node_id 从 node_map 中获取对应的模型实例
        node_instance = node_map[node_id]
        
        auto_inferred_deps = set()
        for instruction in node_dict.get('run', []):
            instruction_config = instruction.get('config', {})
            dependencies = extract_dependencies_from_value(instruction_config)
            auto_inferred_deps.update(dependencies)
    
        explicit_deps = set(node_dict.get('depends_on') or [])

        # 现在可以安全地调用 hook_manager 了
        custom_deps = await hook_manager.decide(
            "resolve_node_dependencies",
            context=ResolveNodeDependenciesContext(
                node=node_instance,
                auto_inferred_deps=auto_inferred_deps.union(explicit_deps)
            )
        )
        
        if custom_deps is not None:
            # 如果插件做出了决策，就使用插件的结果
            all_dependencies = custom_deps
        else:
            # 否则，使用默认逻辑
            all_dependencies = auto_inferred_deps.union(explicit_deps)
        
        dependency_map[node_id] = all_dependencies
    
    return dependency_map
```

### core_engine/state.py
```
# plugins/core_engine/state.py

from __future__ import annotations
import asyncio
import json
from uuid import UUID
from typing import Dict, Any, List, Optional

from fastapi import Request
from pydantic import ValidationError

from backend.core.contracts import (
    Sandbox, 
    StateSnapshot, 
    ExecutionContext, 
    SharedContext,
    BeforeSnapshotCreateContext,
    GraphCollection,
    HookManager,
    Container
)
from .utils import DotAccessibleDict, ServiceResolverProxy 

# --- Section 1: 状态存储类 (包含逻辑) ---

class SnapshotStore:
    """
    一个简单的内存快照存储。
    它操作从 contracts.py 导入的 StateSnapshot 模型。
    """
    def __init__(self):
        self._store: Dict[UUID, StateSnapshot] = {}

    def save(self, snapshot: StateSnapshot):
        if snapshot.id in self._store:
            pass
        self._store[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> Optional[StateSnapshot]:
        return self._store.get(snapshot_id)

    def find_by_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        return sorted(
            [s for s in self._store.values() if s.sandbox_id == sandbox_id],
            key=lambda s: s.created_at
        )

    def clear(self):
        self._store = {}


# --- Section 2: 核心上下文与快照的工厂/助手函数 ---

def create_main_execution_context(
    snapshot: StateSnapshot, 
    container: Container,
    hook_manager: HookManager, 
    run_vars: Dict[str, Any] = None
) -> ExecutionContext:
    shared_context = SharedContext(
        world_state=snapshot.world_state.copy(),
        session_info={
            "start_time": snapshot.created_at,
            "turn_count": 0
        },
        global_write_lock=asyncio.Lock(),
        
        # 关键步骤：
        # 1. 创建 ServiceResolverProxy 实例，它包装了我们的容器。
        # 2. 将这个代理实例传递给 DotAccessibleDict。
        #
        # 这样，`services` 字段就是一个 DotAccessibleDict，
        # 当宏执行 `services.llm_service` 时，
        # DotAccessibleDict 会调用 `proxy['llm_service']`，
        # 进而触发 `ServiceResolverProxy` 去调用 `container.resolve('llm_service')`。
        services=DotAccessibleDict(ServiceResolverProxy(container))
    )
    return ExecutionContext(
        shared=shared_context,
        initial_snapshot=snapshot,
        run_vars=run_vars or {},
        hook_manager=hook_manager
    )

def create_sub_execution_context(
    parent_context: ExecutionContext, 
    run_vars: Dict[str, Any] = None
) -> ExecutionContext:
    return ExecutionContext(
        shared=parent_context.shared,
        initial_snapshot=parent_context.initial_snapshot,
        run_vars=run_vars or {},
        hook_manager=parent_context.hook_manager
    )

async def create_next_snapshot(
    context: ExecutionContext,
    final_node_states: Dict[str, Any],
    triggering_input: Dict[str, Any]
) -> StateSnapshot:
    final_world_state = context.shared.world_state
    next_graph_collection = context.initial_snapshot.graph_collection

    if '__graph_collection__' in final_world_state:
        evolved_graph_data = final_world_state.pop('__graph_collection__', None)
        if evolved_graph_data:
            try:
                next_graph_collection = GraphCollection.model_validate(evolved_graph_data)
            except (ValidationError, json.JSONDecodeError) as e:
                print(f"Warning: Failed to parse evolved graph collection from world_state: {e}")

    snapshot_data = {
        "sandbox_id": context.initial_snapshot.sandbox_id,
        "graph_collection": next_graph_collection,
        "world_state": final_world_state,
        "parent_snapshot_id": context.initial_snapshot.id,
        "run_output": final_node_states,
        "triggering_input": triggering_input,
    }

    filtered_snapshot_data = await context.hook_manager.filter(
        "before_snapshot_create",
        snapshot_data,
        context=BeforeSnapshotCreateContext(
            snapshot_data=snapshot_data,
            execution_context=context
        )
    )
    
    return StateSnapshot.model_validate(filtered_snapshot_data)


# --- Section 3: FastAPI 依赖注入函数 ---

def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    return request.app.state.sandbox_store

def get_snapshot_store(request: Request) -> SnapshotStore:
    return request.app.state.snapshot_store


```

### core_persistence/tests/conftest.py
```

```

### core_persistence/tests/test_service.py
```
# plugins/core_persistence/tests/test_service.py
import pytest
import zipfile
import io
import json
from pydantic import BaseModel

from plugins.core_persistence.service import PersistenceService
from plugins.core_persistence.models import AssetType, PackageManifest, PackageType

# 一个简单的 Pydantic 模型用于测试 save/load
class MockAsset(BaseModel):
    name: str
    value: int

@pytest.fixture
def persistence_service(tmp_path) -> PersistenceService:
    """提供一个使用临时目录的 PersistenceService 实例。"""
    assets_dir = tmp_path / "assets"
    return PersistenceService(assets_base_dir=str(assets_dir))

# 保持你原有的初始化测试
def test_persistence_service_initialization(persistence_service: PersistenceService, tmp_path):
    assets_dir = tmp_path / "assets"
    assert assets_dir.exists()
    assert persistence_service.assets_base_dir == assets_dir

# --- 新增的单元测试 ---

def test_save_and_load_asset(persistence_service: PersistenceService):
    """测试资产的保存和加载往返流程。"""
    asset = MockAsset(name="test_asset", value=123)
    asset_type = AssetType.GRAPH # 使用任意一种类型来测试
    asset_name = "my_first_asset"

    # 保存
    path = persistence_service.save_asset(asset, asset_type, asset_name)
    assert path.exists()
    
    # 加载
    loaded_asset = persistence_service.load_asset(asset_type, asset_name, MockAsset)
    
    assert isinstance(loaded_asset, MockAsset)
    assert loaded_asset.name == "test_asset"
    assert loaded_asset.value == 123

def test_list_assets(persistence_service: PersistenceService):
    """测试列出指定类型的所有资产。"""
    # 初始应为空
    assert persistence_service.list_assets(AssetType.GRAPH) == []

    # 创建一些资产
    persistence_service.save_asset(MockAsset(name="a", value=1), AssetType.GRAPH, "graph_a")
    persistence_service.save_asset(MockAsset(name="b", value=2), AssetType.GRAPH, "graph_b")
    persistence_service.save_asset(MockAsset(name="c", value=3), AssetType.CODEX, "codex_c")

    # 验证列表
    graph_assets = persistence_service.list_assets(AssetType.GRAPH)
    assert sorted(graph_assets) == ["graph_a", "graph_b"]
    
    codex_assets = persistence_service.list_assets(AssetType.CODEX)
    assert codex_assets == ["codex_c"]

def test_export_package(persistence_service: PersistenceService):
    """测试包导出功能。"""
    manifest = PackageManifest(
        package_type=PackageType.GRAPH_COLLECTION,
        entry_point="data/main.graph.hevno.json"
    )
    data_files = {
        "main.graph.hevno.json": MockAsset(name="main_graph", value=1)
    }

    zip_bytes = persistence_service.export_package(manifest, data_files)
    
    # 验证 zip 内容
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        assert "manifest.json" in zf.namelist()
        assert "data/main.graph.hevno.json" in zf.namelist()
        
        manifest_data = json.loads(zf.read("manifest.json"))
        assert manifest_data["package_type"] == "graph_collection"

def test_import_package(persistence_service: PersistenceService):
    """测试包导入功能。"""
    # 先创建一个 zip 包
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("manifest.json", '{"package_type": "sandbox_archive", "entry_point": "sb.json"}')
        zf.writestr("data/sb.json", '{"name": "test"}')
        zf.writestr("data/snapshots/snap1.json", '{"id": "uuid"}')

    manifest, data_files = persistence_service.import_package(zip_buffer.getvalue())

    assert manifest.package_type == PackageType.SANDBOX_ARCHIVE
    assert "sb.json" in data_files
    assert "snapshots/snap1.json" in data_files
    assert data_files["sb.json"] == '{"name": "test"}'
```

### core_persistence/tests/__init__.py
```

```

### core_persistence/tests/test_api.py
```
# plugins/core_persistence/tests/test_api.py
import pytest
import io
import zipfile
from httpx import AsyncClient

# 保持你现有的测试
@pytest.mark.asyncio
async def test_persistence_api_exists(async_client):
    client = await async_client(["core-persistence"])
    response = await client.get("/api/persistence/assets")
    assert response.status_code == 200
    assert response.json() == {"message": "Asset listing endpoint for core_persistence."}

@pytest.mark.asyncio
async def test_api_does_not_exist_without_plugin(async_client):
    client = await async_client(["core-logging"]) 
    response = await client.get("/api/persistence/assets")
    assert response.status_code == 404

# --- 新增的 API 功能测试 ---

@pytest.mark.asyncio
async def test_import_package_api_success(async_client):
    """
    测试成功导入一个合法的 .hevno.zip 包。
    """
    # 1. 动态创建一个合法的 zip 包
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        manifest_content = """
        {
            "package_type": "graph_collection",
            "entry_point": "main.json",
            "metadata": {"author": "Test"}
        }
        """
        zf.writestr("manifest.json", manifest_content)
        zf.writestr("data/main.json", '{"name": "test_graph"}')

    zip_bytes = zip_buffer.getvalue()

    # 2. 创建一个只包含 core-persistence 的客户端
    client = await async_client(["core-persistence"])

    # 3. 发送 POST 请求
    files = {'file': ('test.hevno.zip', zip_bytes, 'application/zip')}
    response = await client.post("/api/persistence/package/import", files=files)

    # 4. 断言结果
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['package_type'] == 'graph_collection'
    assert response_data['metadata']['author'] == 'Test'


@pytest.mark.asyncio
async def test_import_package_api_invalid_file(async_client):
    """
    测试上传非 zip 文件或无效 zip 时的错误处理。
    """
    client = await async_client(["core-persistence"])

    # 场景1：非 .hevno.zip 文件名
    files = {'file': ('test.txt', b'hello', 'text/plain')}
    response = await client.post("/api/persistence/package/import", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()['detail']

    # 场景2：缺少 manifest 的 zip 文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("data/main.json", '{"name": "test_graph"}')
    zip_bytes = zip_buffer.getvalue()
    
    files = {'file': ('bad.hevno.zip', zip_bytes, 'application/zip')}
    response = await client.post("/api/persistence/package/import", files=files)
    assert response.status_code == 400
    assert "missing 'manifest.json'" in response.json()['detail']
```

### core_llm/providers/__init__.py
```

```

### core_llm/providers/gemini.py
```
# plugins/core_llm/providers/gemini.py

from typing import Any
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from google.generativeai import types as generation_types

# --- 核心修改: 导入路径修正 ---
from .base import LLMProvider
from ..models import (
    LLMResponse,
    LLMError,
    LLMResponseStatus,
    LLMErrorType,
)
from ..registry import provider_registry


class GeminiProvider(LLMProvider):
    """
    针对 Google Gemini API 的 LLMProvider 实现。
    """

    async def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        api_key: str,
        **kwargs: Any
    ) -> LLMResponse:
        """
        使用 Gemini API 生成内容。
        """
        try:
            # 每次调用都独立配置，以支持多密钥轮换
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(model_name)

            # 提取支持的生成配置
            generation_config = {
                "temperature": kwargs.get("temperature"),
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
                "max_output_tokens": kwargs.get("max_tokens"),
            }
            # 清理 None 值
            generation_config = {k: v for k, v in generation_config.items() if v is not None}

            response: generation_types.GenerateContentResponse = await model.generate_content_async(
                contents=prompt,
                generation_config=generation_config
            )

            # 检查是否因安全策略被阻止
            # 这是 Gemini 的“软失败”，不会抛出异常
            if not response.parts:
                if response.prompt_feedback.block_reason:
                    error_message = f"Request blocked due to {response.prompt_feedback.block_reason.name}"
                    return LLMResponse(
                        status=LLMResponseStatus.FILTERED,
                        model_name=model_name,
                        error_details=LLMError(
                            error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                            message=error_message,
                            is_retryable=False # 内容过滤不应重试
                        )
                    )

            # 提取 token 使用情况
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }
            
            return LLMResponse(
                status=LLMResponseStatus.SUCCESS,
                content=response.text,
                model_name=model_name,
                usage=usage
            )

        except generation_types.StopCandidateException as e:
            # 这种情况也属于内容过滤
            return LLMResponse(
                status=LLMResponseStatus.FILTERED,
                model_name=model_name,
                error_details=LLMError(
                    error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                    message=f"Generation stopped due to safety settings: {e}",
                    is_retryable=False,
                )
            )
        # 注意: 其他 google_exceptions 将会在此处被抛出，由上层服务捕获并传递给 translate_error

    def translate_error(self, ex: Exception) -> LLMError:
        """
        将 Google API 的异常转换为标准的 LLMError。
        """
        error_details = {"provider": "gemini", "exception": type(ex).__name__, "message": str(ex)}

        if isinstance(ex, google_exceptions.PermissionDenied):
            return LLMError(
                error_type=LLMErrorType.AUTHENTICATION_ERROR,
                message="Invalid API key or insufficient permissions.",
                is_retryable=False,  # 使用相同密钥重试是无意义的
                provider_details=error_details,
            )
        
        if isinstance(ex, google_exceptions.ResourceExhausted):
            return LLMError(
                error_type=LLMErrorType.RATE_LIMIT_ERROR,
                message="Rate limit exceeded. Please try again later or use a different key.",
                is_retryable=False,  # 对于单个密钥，应立即切换，而不是等待重试
                provider_details=error_details,
            )

        if isinstance(ex, google_exceptions.InvalidArgument):
            return LLMError(
                error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                message=f"Invalid argument provided to the API. Check model name and parameters. Details: {ex}",
                is_retryable=False,
                provider_details=error_details,
            )

        if isinstance(ex, (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)):
            return LLMError(
                error_type=LLMErrorType.PROVIDER_ERROR,
                message="The service is temporarily unavailable or the request timed out. Please try again.",
                is_retryable=True,
                provider_details=error_details,
            )
            
        if isinstance(ex, google_exceptions.GoogleAPICallError):
            return LLMError(
                error_type=LLMErrorType.NETWORK_ERROR,
                message=f"A network-level error occurred while communicating with Google API: {ex}",
                is_retryable=True,
                provider_details=error_details,
            )

        return LLMError(
            error_type=LLMErrorType.UNKNOWN_ERROR,
            message=f"An unknown error occurred with the Gemini provider: {ex}",
            is_retryable=False, # 默认未知错误不可重试，以防造成死循环
            provider_details=error_details,
        )
```

### core_llm/providers/base.py
```
# backend/llm/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..models import LLMResponse, LLMError


class LLMProvider(ABC):
    """
    一个抽象基-类，定义了所有 LLM 提供商适配器的标准接口。
    """

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        api_key: str,
        **kwargs: Any
    ) -> LLMResponse:
        """
        与 LLM 提供商进行交互以生成内容。

        这个方法必须处理所有可能的成功和“软失败”（如内容过滤）场景，
        并将它们封装在标准的 LLMResponse 对象中。
        如果发生无法处理的硬性错误（如网络问题、认证失败），它应该抛出原始异常，
        以便上层服务可以捕获并使用 translate_error 进行处理。

        :param prompt: 发送给模型的提示。
        :param model_name: 要使用的具体模型名称 (e.g., 'gemini-1.5-pro-latest')。
        :param api_key: 用于本次请求的 API 密钥。
        :param kwargs: 其他特定于提供商的参数 (e.g., temperature, max_tokens)。
        :return: 一个标准的 LLMResponse 对象。
        :raises Exception: 任何未被处理的、需要由 translate_error 解析的硬性错误。
        """
        pass

    @abstractmethod
    def translate_error(self, ex: Exception) -> LLMError:
        """
        将特定于提供商的原始异常转换为我们标准化的 LLMError 对象。

        这个方法是解耦的关键，它将具体的 SDK 错误与我们系统的内部错误处理逻辑分离开。

        :param ex: 从 generate 方法捕获的原始异常。
        :return: 一个标准的 LLMError 对象。
        """
        pass
```
