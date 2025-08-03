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
    codex.invoke 运行时的实现。
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