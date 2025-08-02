# Directory: .

### pyproject.toml
```
# Hevno/pyproject.toml (修正版)

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
]

[project.optional-dependencies]
# 开发环境依赖
dev = [
    "uvicorn[standard]",
]

# --- 新增：定义插件入口点 ---
[project.entry-points."hevno.plugins"]
# "入口点名称" = "模块路径:可调用对象"
# 我们这里只需要模块，所以不需要指定对象
core_logging = "plugins.core_logging"
# 当你添加新插件 `core_auth` 时，只需在这里加一行：
# core_auth = "plugins.core_auth"

# --- setuptools 配置 ---
[tool.setuptools]
# 明确告诉 setuptools 将 plugins 视为一个命名空间包
# 这对于未来的扩展性非常重要
namespace-packages = ["plugins"]

[tool.setuptools.packages.find]
# 自动发现所有包
where = ["."] # 在根目录下寻找
include = ["backend*", "plugins*"] # 包含 backend 和所有以 plugins 开头的包

[tool.setuptools.package-data]
# 使用通配符包含所有插件的非py文件
# 当你添加新插件时，无需再修改这里
"plugins.*" = ["*.json", "*.yaml"]
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
from fastapi import FastAPI
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
    
    # 日志系统已配置
    logger = logging.getLogger(__name__)
    logger.info("--- FastAPI Application Assembly ---")

    # 将核心服务附加到 app.state
    app.state.container = container
    app.state.hook_manager = hook_manager
    logger.info("Core services (Container, HookManager) attached to app.state.")

    # 触发异步钩子
    logger.info("Triggering 'add_api_routers' hook to collect API routes from plugins...")
    await hook_manager.trigger("add_api_routers", app=app)
    logger.info("API routes collected.")

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
from typing import Any, Callable, Dict, List, Awaitable

logger = logging.getLogger(__name__)

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
        # 注意: 此时日志系统可能还未配置，所以这条日志可能不会按预期格式显示
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

    # filter 和 decide 方法可以根据需要添加
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
import importlib.resources  # 关键导入！
from typing import List, Dict

# 从 contracts 导入类型
from backend.core.contracts import Container, HookManager, PluginRegisterFunc

logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self, container: Container, hook_manager: HookManager):
        self._container = container
        self._hook_manager = hook_manager

    def load_plugins(self):
        """
        执行插件加载的全过程：发现、排序、注册。
        """
        logger.info("--- Starting Plugin Loading (File-based Discovery) ---")
        
        # 阶段一：发现与读取元数据
        all_plugins = self._discover_plugins()
        if not all_plugins:
            logger.warning("No plugins discovered. Skipping loading.")
            return

        # 阶段二：排序
        sorted_plugins = sorted(all_plugins, key=lambda p: p['manifest'].get('priority', 100))

        # 阶段三：注册
        self._register_plugins(sorted_plugins)
        
        logger.info("--- Finished Plugin Loading ---")

    def _discover_plugins(self) -> List[Dict]:
        """
        扫描 'plugins' 包，读取所有子包中的 manifest.json 文件。
        这种方法在开发环境和安装后都能正常工作。
        """
        discovered = []
        try:
            # 使用 importlib.resources.files() 获取到 'plugins' 包的路径
            # 这会返回一个 Traversable 对象，无论是在文件系统还是在 zip 包里都能用
            plugins_package_path = importlib.resources.files('plugins')
            
            for plugin_path in plugins_package_path.iterdir():
                if not plugin_path.is_dir():
                    continue

                manifest_path = plugin_path / "manifest.json"
                if not manifest_path.is_file():
                    logger.warning(f"Plugin directory '{plugin_path.name}' is missing manifest.json, skipping.")
                    continue
                
                try:
                    # 读取 manifest 文件内容
                    manifest_content = manifest_path.read_text(encoding='utf-8')
                    manifest = json.loads(manifest_content)
                    
                    # 构造插件的导入路径，例如 "plugins.core_logging"
                    import_path = f"plugins.{plugin_path.name}"
                    
                    plugin_info = {
                        "name": manifest.get('name', plugin_path.name),
                        "manifest": manifest,
                        "import_path": import_path
                    }
                    
                    logger.debug(f"Discovered plugin '{plugin_info['name']}' with priority {manifest.get('priority', 100)}")
                    discovered.append(plugin_info)
                except Exception as e:
                    logger.error(f"Failed to read or parse manifest for '{plugin_path.name}': {e}")
        
        except ModuleNotFoundError:
            logger.warning("Could not find the 'plugins' package. Make sure it's installed and has an __init__.py.")
        except Exception as e:
            logger.error(f"An unexpected error occurred during plugin discovery: {e}", exc_info=True)
            
        return discovered
    
    def _register_plugins(self, plugins: List[Dict]):
        """按顺序导入并调用每个插件的注册函数。"""
        for plugin_info in plugins:
            plugin_name = plugin_info['name']
            import_path = plugin_info['import_path']
            
            try:
                logger.info(f"Loading plugin: '{plugin_name}' from module '{import_path}'...")
                plugin_module = importlib.import_module(import_path)
                
                register_func: PluginRegisterFunc = getattr(plugin_module, "register_plugin")
                
                # 注意：manifest.json 中不再需要 entry_point 字段了，因为我们是根据目录结构自动推断的
                register_func(self._container, self._hook_manager)
                
                logger.info(f"Successfully loaded and registered plugin: '{plugin_name}'")

            except AttributeError:
                logger.error(f"Plugin '{plugin_name}' module '{import_path}' has no 'register_plugin' function.")
            except Exception as e:
                logger.critical(f"FATAL: Failed to load plugin '{plugin_name}': {e}", exc_info=True)
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
# plugins/core-logging/__init__.py
import os
import yaml
import logging
import logging.config
from pathlib import Path

# 从平台核心导入所需的类型，以实现类型提示和解耦
from backend.core.contracts import Container, HookManager

# 获取当前插件的目录
# 这使得配置文件路径的定位更加健壮
PLUGIN_DIR = Path(__file__).parent

def register_plugin(container: Container, hook_manager: HookManager):
    """
    这是 core-logging 插件的注册入口。
    它在应用启动流程的极早期被调用。
    """
    print("[core-logging] register_plugin called.")
    
    # 1. 加载日志配置
    config_path = PLUGIN_DIR / "logging_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        logging_config = yaml.safe_load(f)

    # 2. 检查环境变量覆盖
    # 这允许我们在容器或生产环境中轻松修改日志级别，而无需更改文件
    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level and env_log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        print(f"[core-logging] Overriding root log level with env var LOG_LEVEL={env_log_level.upper()}")
        logging_config['root']['level'] = env_log_level.upper()

    # 3. 应用配置
    # 这是最关键的一步：配置 Python 全局的 logging 系统
    logging.config.dictConfig(logging_config)
    
    # 4. 获取一个 logger 实例并打印一条消息，以验证配置是否生效
    # 从此刻起，任何模块调用 `logging.getLogger()` 都会获得一个已配置好的记录器
    logger = logging.getLogger(__name__)
    logger.info("核心日志系统已成功配置。Hevno 平台的所有后续日志将遵循此配置。")
    logger.debug("这是一个 DEBUG 级别的消息，只有当日志级别设置为 DEBUG 时才会显示。")
    
    # 未来：在这里注册 SSE 流式传输服务和 API 端点
    # from .streamer import LogStreamerService, create_log_stream_router
    # container.register("log_streamer", LogStreamerService)
    # hook_manager.add_implementation("add_api_routers", create_log_stream_router)
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
