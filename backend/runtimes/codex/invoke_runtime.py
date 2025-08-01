# backend/runtimes/codex/invoke_runtime.py

import asyncio
from typing import Dict, Any, List, Optional, Set

from backend.core.interfaces import RuntimeInterface
from backend.core.types import ExecutionContext
from backend.core.evaluation import evaluate_data, build_evaluation_context
from backend.core.utils import DotAccessibleDict

# 从同级目录导入模型
from .models import CodexCollection, CodexEntry, TriggerMode

# 辅助数据结构
class ActivatedEntry:
    # ... 用来包装一个被激活的条目及其元数据 (如计算后的priority, 触发原因)
    pass

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
        # 获取配置，准备锁和基础求值上下文
        from_sources = config.get("from", [])
        recursion_enabled = config.get("recursion_enabled", False)
        debug_mode = config.get("debug", False)
        lock = context.shared.global_write_lock
        
        # 加载并验证 world.codices
        codices_data = context.shared.world_state.get("codices", {})
        try:
            codex_collection = CodexCollection.model_validate(codices_data).root
        except Exception as e:
            raise ValueError(f"Invalid codex structure in world.codices: {e}")

        # --- 1. 阶段一：选择与过滤 (Structural Evaluation) ---
        # 目标：填充 initial_pool
        initial_pool: List[ActivatedEntry] = []
        
        # 遍历 from 配置，对每个 source text 进行处理
        #   - 求值 source 宏
        #   - 遍历对应 codex 的所有 entry
        #   - 求值 is_enabled, keywords, priority (使用只包含 world, run 的上下文)
        #   - 根据 trigger_mode 和 keywords 匹配，决定是否激活
        #   - 如果激活，创建一个 ActivatedEntry 对象并加入 initial_pool

        # --- 2. 阶段二：渲染与注入 (Content Evaluation) ---
        # 目标：生成最终文本
        
        final_text_parts = []
        rendered_entry_ids: Set[str] = set()
        rendering_pool = sorted(initial_pool, key=lambda x: x.priority, reverse=True)
        
        # 如果启用了递归
        if recursion_enabled:
            # 实现 README 中描述的递归循环
            # while rendering_pool:
            #   - 重新排序
            #   - pop(0) 最高优先级条目
            #   - 渲染其 content (使用包含 nodes, trigger 的完整上下文)
            #   - 将渲染结果作为新 source，重新扫描所有未渲染的条目
            #   - 将新激活的条目加入 rendering_pool
            #   - 需要有深度/次数限制来防止无限循环
            pass
        else:
            # 简单模式：遍历一次，渲染所有 content
            for activated_entry in rendering_pool:
                # 渲染 content (使用完整上下文)
                # 将结果追加到 final_text_parts
                pass
        
        # --- 3. 构造输出 ---
        final_text = "\n\n".join(final_text_parts) # 使用双换行符分隔条目
        
        if debug_mode:
            # 构造包含 trace 信息的复杂输出
            return {"output": {"final_text": final_text, "trace": { ... }}}
        else:
            return {"output": final_text}