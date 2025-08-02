# Directory: .

### conftest.py
```
# conftest.py
import pytest
import asyncio
from typing import Generator, List
from fastapi import FastAPI
# 导入 ASGITransport 以包装我们的 app
from httpx import AsyncClient, ASGITransport

# 从平台核心导入
from backend.app import create_app
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.loader import PluginLoader

# --- 核心 Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """为整个测试会话创建一个事件循环。"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def clean_container() -> Container:
    """提供一个全新的、空的 DI 容器实例。"""
    return Container()

@pytest.fixture
def hook_manager() -> HookManager:
    """提供一个全新的、空的 HookManager 实例。"""
    return HookManager()

# --- 插件加载 Fixtures ---

class TestPluginLoader(PluginLoader):
    """一个特殊的插件加载器，可以按需加载指定的插件。"""
    def __init__(self, container: Container, hook_manager: HookManager, enabled_plugins: List[str]):
        super().__init__(container, hook_manager)
        self.enabled_plugins = enabled_plugins

    def _discover_plugins(self) -> List[dict]:
        """重写发现逻辑，只“发现”被启用的插件。"""
        all_plugins = super()._discover_plugins()
        print(f"TestPluginLoader: Found {len(all_plugins)} total plugins, filtering for {self.enabled_plugins}")
        enabled = [p for p in all_plugins if p['name'] in self.enabled_plugins]
        print(f"TestPluginLoader: Enabled {len(enabled)} plugins.")
        return enabled

@pytest.fixture
def loaded_plugins(
    clean_container: Container,
    hook_manager: HookManager
) -> Generator[None, List[str], None]:
    """
    一个【生成器 fixture】，允许测试按需加载一组特定的插件。
    """
    _loader = None
    
    def _load(plugin_names: List[str]):
        nonlocal _loader
        _loader = TestPluginLoader(clean_container, hook_manager, enabled_plugins=plugin_names)
        _loader.load_plugins()

    yield _load
    
    print("Plugin loading fixture teardown.")


# --- 应用与客户端 Fixtures ---

@pytest.fixture
async def test_app(
    loaded_plugins: Generator[None, List[str], None]
) -> Generator[FastAPI, List[str], None]:
    """
    一个更高阶的 fixture，它创建一个 FastAPI 应用实例，并加载指定的插件。
    """
    app_instance = None
    
    async def _create(plugin_names: List[str]):
        nonlocal app_instance
        
        if "core-logging" not in plugin_names:
            plugin_names.insert(0, "core-logging")

        app_instance = create_app()

        container = Container()
        hook_manager = HookManager()

        loader = TestPluginLoader(container, hook_manager, enabled_plugins=plugin_names)
        loader.load_plugins()

        app_instance.state.container = container
        app_instance.state.hook_manager = hook_manager

        routers_to_add = await hook_manager.filter("collect_api_routers", [])
        for router in routers_to_add:
            app_instance.include_router(router)
        
        return app_instance

    yield _create

@pytest.fixture
async def async_client(test_app: Generator[FastAPI, List[str], None]) -> Generator[AsyncClient, List[str], None]:
    """
    一个终极测试客户端 fixture。
    它接收一个插件列表，构建一个只包含这些插件的应用，并返回一个可以对其进行 HTTP 请求的客户端。
    """
    client_instance = None
    
    async def _create_client(plugin_names: List[str]):
        nonlocal client_instance
        app = await test_app(plugin_names)
        
        # --- 核心修复：使用 ASGITransport 来包装 app ---
        transport = ASGITransport(app=app)
        client_instance = AsyncClient(transport=transport, base_url="http://test")
        
        return client_instance

    yield _create_client
    
    if client_instance:
        await client_instance.aclose()
```

### pyproject.toml
```
# Hevno/pyproject.toml

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "hevno-engine"
version = "1.2.0"
authors = [
    { name="Hevno Team", email="contact@example.com" },
]
description = "A dynamically loaded, modular execution engine for Hevno, built with a plugin-first architecture."
readme = "README.md"
requires-python = ">=3.8"
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
# 核心依赖
dependencies = [
    "fastapi",
    "pydantic",
    "pyyaml",
    "pytest",
    "pytest-asyncio",
    "httpx",
]

[project.optional-dependencies]
dev = [ "uvicorn[standard]" ]

[project.entry-points."hevno.plugins"]
core_logging = "plugins.core_logging"

[tool.setuptools]
namespace-packages = ["plugins"]
[tool.setuptools.packages.find]
where = ["."]
include = ["backend*", "plugins*"]
[tool.setuptools.package-data]
"plugins.*" = ["*.json", "*.yaml"]


# --- Pytest 配置 (已修正) ---
[tool.pytest.ini_options]
# 明确指定测试文件的搜索路径
testpaths = [
    "tests",
    "plugins",
]

# 配置 pytest-asyncio
asyncio_mode = "auto"
```

### MANIFEST.in
```
# Hevno/MANIFEST.in

# 递归地包含 plugins 目录下的所有 .json 和 .yaml 文件
graft plugins
global-include *.json *.yaml

# 你也可以更精确地指定
# recursive-include plugins *.json
# recursive-include plugins *.yaml
```

### plugins/__init__.py
```

```

### tests/__init__.py
```

```

### backend/__init__.py
```

```

### backend/container.py
```
# backend/container.py
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class Container:
    """一个简单的依赖注入容器。"""
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}
        self._instances: Dict[str, Any] = {}
        logger.info("DI Container initialized.")

    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        """
        注册一个服务工厂。

        :param name: 服务的唯一名称。
        :param factory: 一个创建服务实例的函数 (可以无参，或接收 container 实例)。
        :param singleton: 如果为 True，服务只会被创建一次。
        """
        logger.debug(f"Registering service '{name}'. Singleton: {singleton}")
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
        
        # 简单的依赖注入：如果工厂需要容器本身，就传递它
        # 这是一个简化处理，更复杂的可以用 inspect.signature
        try:
            instance = factory(self)
        except TypeError:
            instance = factory()

        logger.debug(f"Resolved service '{name}'.")

        if self._singletons.get(name, True):
            self._instances[name] = instance
        
        return instance
```

### backend/app.py
```
# backend/app.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

# 导入微核心组件
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.loader import PluginLoader

# 注意我们不在这里导入任何插件或具体服务
# 这是一个干净、通用的启动器

# 使用 FastAPI 的新版生命周期管理器 (lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 应用启动时执行 ---
    # 实例化平台核心服务
    container = Container()
    hook_manager = HookManager()

    # 阶段一 & 二：发现、排序与注册 (同步过程)
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()
    
    # 日志系统此时应该已经由 core_logging 插件配置好了
    logger = logging.getLogger(__name__)
    logger.info("--- FastAPI Application Assembly ---")

    # 将核心服务附加到 app.state，以便 API 路由可以访问它们
    app.state.container = container
    app.state.hook_manager = hook_manager
    logger.info("Core services (Container, HookManager) attached to app.state.")

    # 阶段三：装配 (使用钩子系统)
    logger.info("Triggering 'collect_api_routers' filter hook to collect API routers from plugins...")
    # 我们启动一个空的列表，然后让 filter 钩子去填充它
    routers_to_add: list[APIRouter] = await hook_manager.filter("collect_api_routers", [])
    
    if routers_to_add:
        logger.info(f"Collected {len(routers_to_add)} router(s). Adding to application...")
        for router in routers_to_add:
            app.include_router(router)
            logger.debug(f"Added router with prefix '{router.prefix}' and tags {router.tags}")
    else:
        logger.info("No API routers were collected from plugins.")


    logger.info("--- Hevno Engine Ready ---")

    yield # 在此暂停，应用开始处理请求

    # --- 应用关闭时执行 ---
    logger.info("--- Hevno Engine Shutting Down ---")
    # 可以在这里添加清理逻辑


def create_app() -> FastAPI:
    """
    应用工厂函数：构建、配置并返回 FastAPI 应用实例。
    """
    app = FastAPI(
        title="Hevno Engine (Plugin Architecture)",
        version="1.2.0",
        lifespan=lifespan  # 注册生命周期管理器
    )

    # 中间件的配置移到这里，因为它不依赖于异步启动过程
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
```

### backend/main.py
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

### backend/core/hooks.py
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

### backend/core/__init__.py
```

```

### backend/core/loader.py
```
# backend/core/loader.py

import json
import logging
import importlib
import importlib.resources
import traceback
from typing import List, Dict

from backend.core.contracts import Container, HookManager, PluginRegisterFunc

# 在模块级别获取 logger
logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self, container: Container, hook_manager: HookManager):
        self._container = container
        self._hook_manager = hook_manager

    def load_plugins(self):
        """执行插件加载的全过程：发现、排序、注册。"""
        # 使用 print 是因为此时日志系统可能还未配置
        print("\n--- Hevno 插件系统：开始加载 ---")
        
        # 阶段一：发现
        all_plugins = self._discover_plugins()
        if not all_plugins:
            print("警告：未发现任何插件。")
            print("--- Hevno 插件系统：加载完成 ---\n")
            return

        # 阶段二：排序
        sorted_plugins = sorted(all_plugins, key=lambda p: (p['manifest'].get('priority', 100), p['name']))
        
        # 打印加载顺序，这是一个有用的元信息
        print("插件加载顺序已确定：")
        for i, p_info in enumerate(sorted_plugins):
            print(f"  {i+1}. {p_info['name']} (优先级: {p_info['manifest'].get('priority', 100)})")

        # 阶段三：注册
        self._register_plugins(sorted_plugins)
        
        # 使用配置好的 logger 记录最终信息
        logger.info("所有插件均已加载并注册完毕。")
        print("--- Hevno 插件系统：加载完成 ---\n")


    def _discover_plugins(self) -> List[Dict]:
        """扫描 'plugins' 包，读取所有子包中的 manifest.json 文件。"""
        discovered = []
        try:
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
                    import_path = f"plugins.{plugin_path.name}"
                    
                    plugin_info = { "name": manifest.get('name', plugin_path.name), "manifest": manifest, "import_path": import_path }
                    discovered.append(plugin_info)
                except Exception:
                    # 在发现阶段保持静默，只处理能成功解析的
                    pass
        
        except (ModuleNotFoundError, FileNotFoundError):
             # 同样保持静默，如果没有 plugins 目录就算了
            pass
            
        return discovered
    
    def _register_plugins(self, plugins: List[Dict]):
        """按顺序导入并调用每个插件的注册函数。"""
        for plugin_info in plugins:
            plugin_name = plugin_info['name']
            import_path = plugin_info['import_path']
            
            try:
                # --- 核心改动：这里不再打印日志 ---
                # 日志记录的责任已移交插件本身
                plugin_module = importlib.import_module(import_path)
                register_func: PluginRegisterFunc = getattr(plugin_module, "register_plugin")
                register_func(self._container, self._hook_manager)

            except Exception as e:
                # 只有在发生致命错误时，加载器才需要“发声”
                # 并且使用 print，因为它不依赖于可能出问题的日志系统
                print("\n" + "="*80)
                print(f"!!! 致命错误：加载插件 '{plugin_name}' ({import_path}) 失败 !!!")
                print("="*80)
                traceback.print_exc()
                print("="*80)
                # 遇到错误时，可以选择停止应用或继续加载其他插件
                # 这里我们选择停止，因为插件依赖可能被破坏
                raise RuntimeError(f"无法加载插件 {plugin_name}") from e
```

### backend/core/contracts.py
```
# backend/core/contracts.py
from __future__ import annotations
import asyncio
from typing import Any, Callable, Coroutine, Dict, List
from pydantic import BaseModel, Field

# --- 类型别名 ---
# 为了清晰，我们定义一些将来会用到的类型别名

# 一个插件的注册函数签名
# 它接收 DI 容器和事件总线作为参数
PluginRegisterFunc = Callable[['Container', 'HookManager'], None]

# --- 核心服务接口占位符 (为了类型提示) ---
# 实际的类在它们自己的模块中定义。这里只是一个“契约”。
# 注意：我们不在这里导入任何模块，只是使用字符串或前向引用。
class Container:
    """依赖注入容器的抽象契约。"""
    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        raise NotImplementedError
    
    def resolve(self, name: str) -> Any:
        raise NotImplementedError

class HookManager:
    """事件总线的抽象契约。"""
    async def trigger(self, hook_name: str, **kwargs: Any) -> None:
        raise NotImplementedError

# --- 核心数据模型 (示例，未来会扩展) ---
# 在这里定义如 StateSnapshot, ExecutionContext 等
# 目前，我们先留空，因为还没有核心引擎插件。

# --- 系统事件契约 ---
# 定义通过 HookManager 分发的事件的数据结构
# 这是插件间通信的“语言”

class AddApiRouterContext(BaseModel):
    """请求添加一个API路由到主应用的事件。"""
    router: Any # 在这里我们不关心具体类型，可以是 FastAPI.APIRouter
    prefix: str = ""
    tags: List[str] = Field(default_factory=list)
```

### plugins/core_logging/logging_config.yaml
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

### plugins/core_logging/__init__.py
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

### plugins/core_logging/manifest.json
```
{
    "name": "core-logging",
    "version": "1.0.0",
    "description": "Provides centralized, configurable logging for the Hevno platform.",
    "author": "Hevno Team",
    "priority": -100
}
```

### plugins/core_persistence/service.py
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

### plugins/core_persistence/models.py
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

### plugins/core_persistence/__init__.py
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

### plugins/core_persistence/api.py
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

### plugins/core_persistence/manifest.json
```
{
    "name": "core-persistence",
    "version": "1.0.0",
    "description": "Provides file system persistence, asset management, and package import/export.",
    "author": "Hevno Team",
    "priority": 10
}
```

### plugins/core_persistence/tests/conftest.py
```

```

### plugins/core_persistence/tests/test_service.py
```
# plugins/core_persistence/tests/test_service.py
import pytest
from plugins.core_persistence.service import PersistenceService

# 使用 pytest.mark.asyncio 来标记异步测试函数
@pytest.mark.asyncio
async def test_persistence_service_initialization(tmp_path):
    """
    测试 PersistenceService 能否在临时目录中正确初始化。
    `tmp_path` 是 pytest 内置的一个 fixture，提供一个临时的目录路径。
    """
    assets_dir = tmp_path / "assets"
    service = PersistenceService(assets_base_dir=str(assets_dir))
    
    assert assets_dir.exists()
    assert service.assets_base_dir == assets_dir

# 可以在这里添加更多关于 save_asset, load_asset, import/export 的单元测试
```

### plugins/core_persistence/tests/__init__.py
```

```

### plugins/core_persistence/tests/test_api.py
```
# plugins/core_persistence/tests/test_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_persistence_api_exists(async_client: AsyncClient):
    """
    测试场景：当只加载 `core_persistence` 插件时，它的 API 端点应该存在。
    """
    # 1. 使用 fixture 创建一个只包含 `core_persistence` 的应用客户端
    # `core-logging` 会被自动包含
    client = await async_client(["core-persistence"])
    
    # 2. 向插件的 API 端点发送请求
    response = await client.get("/api/persistence/assets")
    
    # 3. 断言结果
    assert response.status_code == 200
    assert response.json() == {"message": "Asset listing endpoint for core_persistence."}

@pytest.mark.asyncio
async def test_api_does_not_exist_without_plugin(async_client: AsyncClient):
    """
    测试场景：当不加载 `core_persistence` 插件时，它的 API 端点不应该存在。
    """
    # 1. 创建一个只包含 `core-logging` 的应用 (或者一个不存在的虚拟插件)
    client = await async_client(["core-logging"]) 
    
    # 2. 向本应不存在的端点发送请求
    response = await client.get("/api/persistence/assets")
    
    # 3. 断言它返回 404 Not Found
    assert response.status_code == 404
```
