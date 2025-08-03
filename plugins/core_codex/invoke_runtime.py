# plugins/core_codex/invoke_runtime.py

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Set

from pydantic import ValidationError

# 从平台核心导入通用工具
from backend.core.utils import DotAccessibleDict
# 从 core_engine 的公共契约导入所需接口和模型
from plugins.core_engine.contracts import (
    RuntimeInterface, 
    ExecutionContext,
    MacroEvaluationServiceInterface
)

from .models import CodexCollection, ActivatedEntry, TriggerMode

logger = logging.getLogger("hevno.runtime.codex")


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
        
        macro_service: MacroEvaluationServiceInterface = context.shared.services.macro_evaluation_service
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

        # --- 1. 阶段一：初始激活 ---
        initial_pool: List[ActivatedEntry] = []
        structural_eval_context = macro_service.build_context(context)

        logger.debug("--- [CODEX.INVOKE START] ---")
        logger.debug(f"Recursion enabled: {recursion_enabled}")

        for source_config in from_sources:
            codex_name = source_config.get("codex")
            if not codex_name or not codex_collection.get(codex_name):
                continue
            
            codex_model = codex_collection.get(codex_name)
            source_text_macro = source_config.get("source", "")
            source_text = await macro_service.evaluate(source_text_macro, structural_eval_context, lock) if source_text_macro else ""
            
            logger.debug(f"Scanning codex '{codex_name}' with source text: '{source_text}'")

            for entry in codex_model.entries:
                is_enabled = await macro_service.evaluate(entry.is_enabled, structural_eval_context, lock)
                if not is_enabled:
                    continue
                
                keywords = await macro_service.evaluate(entry.keywords, structural_eval_context, lock)
                priority = await macro_service.evaluate(entry.priority, structural_eval_context, lock)

                is_activated, matched_keywords = False, []
                if entry.trigger_mode == TriggerMode.ALWAYS_ON:
                    is_activated = True
                elif entry.trigger_mode == TriggerMode.ON_KEYWORD and source_text and keywords:
                    for keyword in keywords:
                        if re.search(re.escape(str(keyword)), str(source_text), re.IGNORECASE):
                            matched_keywords.append(keyword)
                    if matched_keywords:
                        is_activated = True
                
                if is_activated:
                    activated = ActivatedEntry(
                        entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                        priority_val=int(priority), keywords_val=keywords, is_enabled_val=bool(is_enabled),
                        source_text=str(source_text), matched_keywords=matched_keywords,
                        depth=0  # 初始激活的条目深度为 0
                    )
                    initial_pool.append(activated)
                    logger.debug(f"  [+] Initial activation: '{entry.id}' (prio: {priority}, depth: 0)")
        
        # --- 2. 阶段二：渲染与递归 ---
        rendered_entry_ids: Set[str] = set()
        rendered_parts_with_priority = []
        rendering_pool = sorted(initial_pool, key=lambda x: x.priority_val, reverse=True)
        
        logger.debug("--- [STARTING RENDER LOOP] ---")
        
        # 【BUG修复】循环条件简化，只要池中有待渲染条目就继续。
        while rendering_pool:
            pool_state_log = ", ".join([f"{e.entry_model.id}({e.priority_val})" for e in rendering_pool])
            logger.debug(f"Loop Start | Pool: [{pool_state_log}]")

            entry_to_render = rendering_pool.pop(0)

            if entry_to_render.entry_model.id in rendered_entry_ids:
                logger.debug(f"  Skipping '{entry_to_render.entry_model.id}' as it's already rendered.")
                continue
            
            logger.debug(f"  -> Rendering '{entry_to_render.entry_model.id}' (prio: {entry_to_render.priority_val}, depth: {entry_to_render.depth})")
            
            content_eval_context = macro_service.build_context(context)
            content_eval_context['trigger'] = DotAccessibleDict({
                "source_text": entry_to_render.source_text,
                "matched_keywords": entry_to_render.matched_keywords
            })
            
            rendered_content = str(await macro_service.evaluate(entry_to_render.entry_model.content, content_eval_context, lock))
            
            rendered_parts_with_priority.append({
                "content": rendered_content, "priority": entry_to_render.priority_val, "id": entry_to_render.entry_model.id
            })
            rendered_entry_ids.add(entry_to_render.entry_model.id)
            
            # 【BUG修复】递归深度检查现在只保护递归激活步骤，而不是终止整个循环。
            max_depth = entry_to_render.codex_config.recursion_depth
            if recursion_enabled and entry_to_render.depth < max_depth:
                new_source_text = rendered_content
                logger.debug(f"     Recursion check (depth {entry_to_render.depth} < max_depth {max_depth}). Source: '{new_source_text[:50]}...'")
                
                newly_activated_this_pass = []
                for codex_name, codex_model in codex_collection.items():
                    for entry in codex_model.entries:
                        if entry.id in rendered_entry_ids or any(p.entry_model.id == entry.id for p in rendering_pool):
                            continue
                        
                        if entry.trigger_mode == TriggerMode.ON_KEYWORD:
                            # ... (内部逻辑与之前一致) ...
                            is_enabled = await macro_service.evaluate(entry.is_enabled, structural_eval_context, lock)
                            if not is_enabled: continue
                            keywords = await macro_service.evaluate(entry.keywords, structural_eval_context, lock)
                            new_matched_keywords = [kw for kw in keywords if re.search(re.escape(str(kw)), new_source_text, re.IGNORECASE)]
                            
                            if new_matched_keywords:
                                priority = await macro_service.evaluate(entry.priority, structural_eval_context, lock)
                                activated = ActivatedEntry(
                                    entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                                    priority_val=int(priority), keywords_val=keywords, is_enabled_val=is_enabled,
                                    source_text=new_source_text, matched_keywords=new_matched_keywords,
                                    depth=entry_to_render.depth + 1 # 新激活的条目深度+1
                                )
                                newly_activated_this_pass.append(activated)
                                logger.debug(f"       [+] Recursive activation: '{entry.id}' (prio: {priority}, depth: {activated.depth})")
                
                if newly_activated_this_pass:
                    rendering_pool.extend(newly_activated_this_pass)
                    rendering_pool.sort(key=lambda x: x.priority_val, reverse=True)
        
        # --- 3. 构造输出 ---
        logger.debug("--- [FINALIZING OUTPUT] ---")
        pre_sort_log = ", ".join([f"{p['id']}({p['priority']})" for p in rendered_parts_with_priority])
        logger.debug(f"Rendered parts (in render order): [{pre_sort_log}]")
        
        # 【设计核心】最终输出严格按优先级排序
        final_sorted_parts = sorted(rendered_parts_with_priority, key=lambda p: p['priority'], reverse=True)
        
        post_sort_log = ", ".join([f"{p['id']}({p['priority']})" for p in final_sorted_parts])
        logger.debug(f"Final parts (sorted by priority): [{post_sort_log}]")

        final_text = "\n\n".join([p['content'] for p in final_sorted_parts])
        
        logger.debug(f"Final output text:\n---\n{final_text}\n---")
        logger.debug("--- [CODEX.INVOKE END] ---")

        if debug_mode:
            return { "output": { "final_text": final_text, "trace": {} } } # 省略 trace 实现
        
        return {"output": final_text}