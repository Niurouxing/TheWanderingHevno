# plugins/core_memoria/__init__.py

import logging
from typing import Dict, List, Any
from uuid import UUID

# 从平台核心导入接口和类型
from backend.core.contracts import Container, HookManager
# 从 core_engine 契约中导入所需的上下文模型，以确保类型安全
from plugins.core_engine.contracts import ExecutionContext

# 导入本插件内部的组件
from .runtimes import MemoriaAddRuntime, MemoriaQueryRuntime, MemoriaAggregateRuntime
from .models import Memoria, MemoryEntry

logger = logging.getLogger(__name__)


# --- 服务工厂 (Service Factory) ---
def _create_memoria_event_queue() -> Dict[UUID, List[Dict[str, Any]]]:
    """
    工厂函数：创建一个简单的、内存中的事件队列。
    这个队列是 core-memoria 插件私有的，用于暂存后台任务完成的事件。
    - 键: sandbox_id
    - 值: 一个包含事件负载字典的列表
    """
    logger.debug("创建 memoria_event_queue 单例。")
    return {}


# --- 钩子实现 (Hook Implementations) ---

async def provide_memoria_runtimes(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的所有运行时。"""
    memoria_runtimes = {
        "memoria.add": MemoriaAddRuntime,
        "memoria.query": MemoriaQueryRuntime,
        "memoria.aggregate": MemoriaAggregateRuntime,
    }
    
    for name, runtime_class in memoria_runtimes.items():
        if name not in runtimes:
            runtimes[name] = runtime_class
            logger.debug(f"Provided '{name}' runtime to the engine.")
            
    return runtimes

async def apply_pending_synthesis(context: ExecutionContext) -> ExecutionContext:
    """
    钩子实现：监听 'before_graph_execution' 钩子。
    在图的逻辑开始执行之前，检查是否有待处理的综合事件，
    并以原子方式将它们应用到当前的世界状态中。
    """
    # 1. 从容器解析我们自己的事件队列
    #    这是一个从 ExecutionContext 安全获取容器实例的技巧。
    #    context.shared.services 是一个代理对象，但我们可以访问其内部的 _container。
    container: Container = context.shared.services._container 
    event_queue: Dict[UUID, List[Dict[str, Any]]] = container.resolve("memoria_event_queue")
    sandbox_id = context.initial_snapshot.sandbox_id
    
    # 2. 检查并原子性地获取待处理事件
    pending_events = event_queue.pop(sandbox_id, [])
    if not pending_events:
        return context  # 如果没有事件，快速退出，不做任何操作

    logger.info(f"Memoria: 发现 {len(pending_events)} 个待处理的综合事件，正在应用到 world_state...")
    
    # 3. 将事件逻辑应用到 world_state
    #    我们直接修改 context.shared.world_state，因为它是对真实世界状态的可变引用。
    world_state = context.shared.world_state
    
    memoria_data = world_state.setdefault("memoria", {"__global_sequence__": 0})
    memoria = Memoria.model_validate(memoria_data)
    
    for event in pending_events:
        if event.get("type") == "memoria_synthesis_completed":
            stream_name = event.get("stream_name")
            if not stream_name:
                continue
                
            stream = memoria.get_stream(stream_name)
            if stream:
                # 重置触发器计数器
                stream.synthesis_trigger_counter = 0
                
                # 创建并添加新的总结条目
                summary_entry = MemoryEntry(
                    sequence_id=memoria.get_next_sequence_id(),
                    level=event.get("level", "summary"),
                    tags=event.get("tags", ["synthesis", "auto-generated"]),
                    content=str(event.get("content", ""))
                )
                stream.entries.append(summary_entry)
                memoria.set_stream(stream_name, stream)
                logger.debug(f"已将新总结应用到流 '{stream_name}'。")
    
    # 将更新后的 memoria 模型写回到世界状态字典中
    world_state["memoria"] = memoria.model_dump()

    # 4. 返回被修改过的 context，以便后续流程使用更新后的状态
    return context


# --- 主注册函数 (Main Registration Function) ---
def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-memoria 插件的注册入口，由平台加载器调用。"""
    logger.info("--> 正在注册 [core-memoria] 插件...")

    # 1. 注册本插件私有的事件队列服务
    container.register("memoria_event_queue", _create_memoria_event_queue, singleton=True)
    logger.debug("服务 'memoria_event_queue' 已注册。")

    # 2. 注册钩子实现，将我们的运行时提供给 core-engine
    hook_manager.add_implementation(
        "collect_runtimes", 
        provide_memoria_runtimes, 
        plugin_name="core-memoria"
    )

    # 3. 注册钩子实现，用于在图执行前处理后台任务的结果
    hook_manager.add_implementation(
        "before_graph_execution",
        apply_pending_synthesis,
        priority=50,  # 使用默认优先级
        plugin_name="core-memoria"
    )
    logger.debug("钩子实现 'collect_runtimes' 和 'before_graph_execution' 已注册。")

    logger.info("插件 [core-memoria] 注册成功。")