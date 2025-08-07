# plugins/core_memoria/__init__.py (部分修改)

import logging
from typing import Dict, List, Any
from uuid import UUID

from backend.core.contracts import Container, HookManager
from plugins.core_engine.contracts import ExecutionContext
from .runtimes import MemoriaAddRuntime, MemoriaQueryRuntime, MemoriaAggregateRuntime
from .models import Memoria, MemoryEntry

logger = logging.getLogger(__name__)

def _create_memoria_event_queue() -> Dict[UUID, List[Dict[str, Any]]]:
    """
    工厂函数：创建一个简单的、内存中的事件队列。
    这个队列是 core_memoria 插件私有的，用于暂存后台任务完成的事件。
    - 键: sandbox_id
    - 值: 一个包含事件负载字典的列表
    """
    logger.debug("创建 memoria_event_queue 单例。")
    return {}

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

async def apply_pending_synthesis(context: ExecutionContext, container: Container) -> ExecutionContext:
    """
    【已重构】钩子实现：在图执行前应用待处理的综合事件。
    现在操作 context.shared.moment_state。
    """
    event_queue: Dict[UUID, List[Dict[str, Any]]] = container.resolve("memoria_event_queue")
    sandbox_id = context.initial_snapshot.sandbox_id
    
    pending_events = event_queue.pop(sandbox_id, [])
    if not pending_events:
        return context

    logger.info(f"Memoria: 发现 {len(pending_events)} 个待处理的综合事件，正在应用到 moment_state...")
    
    # --- 【核心修改】 ---
    # 从 moment_state 中获取和更新 memoria 数据
    moment_state = context.shared.moment_state
    memoria_data = moment_state.setdefault("memoria", {"__global_sequence__": 0})
    # -------------------
    
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
    
    # --- 【核心修改】 ---
    # 将更新后的 memoria 模型写回到 moment_state
    moment_state["memoria"] = memoria.model_dump()
    # -------------------

    return context

# --- 主注册函数 (保持不变) ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_memoria] 插件...")

    container.register("memoria_event_queue", _create_memoria_event_queue, singleton=True)
    logger.debug("服务 'memoria_event_queue' 已注册。")

    hook_manager.add_implementation(
        "collect_runtimes", 
        provide_memoria_runtimes, 
        plugin_name="core_memoria"
    )

    hook_manager.add_implementation(
        "before_graph_execution",
        apply_pending_synthesis,
        priority=50,
        plugin_name="core_memoria"
    )
    logger.debug("钩子实现 'collect_runtimes' 和 'before_graph_execution' 已注册。")

    logger.info("插件 [core_memoria] 注册成功。")