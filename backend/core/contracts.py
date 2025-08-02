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