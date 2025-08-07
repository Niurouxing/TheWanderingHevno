# plugins/core_codex/invoke_runtime.py (已重构)

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Set

from pydantic import ValidationError

from backend.core.utils import DotAccessibleDict
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
    它现在能从 Lore 和 Moment 两个作用域中合并知识库。
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
        
        # 1. 从 Lore 和 Moment 中分别获取 codex 数据
        lore_codices = context.shared.lore_state.get("codices", {})
        moment_codices = context.shared.moment_state.get("codices", {})
        
        # 2. 合并两个作用域的知识库，Moment 中的同名 Codex 会覆盖 Lore 中的
        #    这是新模型的关键实现点
        unified_codex_data = {**lore_codices, **moment_codices}
        
        if not unified_codex_data:
            logger.warning("No codices found in lore_state or moment_state.")
            return {"output": ""}
            
        try:
            codex_collection = CodexCollection.model_validate(unified_codex_data).root
        except ValidationError as e:
            raise ValueError(f"Invalid codex structure after merging lore and moment: {e}")

        initial_pool: List[ActivatedEntry] = []
        structural_eval_context = macro_service.build_context(context)

        logger.debug("--- [CODEX.INVOKE START] ---")
        logger.debug(f"Recursion enabled: {recursion_enabled}")
        logger.debug(f"Available codices after merge: {list(codex_collection.keys())}")

        for source_config in from_sources:
            codex_name = source_config.get("codex")
            if not codex_name or not codex_collection.get(codex_name):
                logger.debug(f"Codex '{codex_name}' requested but not found in merged collection. Skipping.")
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
                        depth=0
                    )
                    initial_pool.append(activated)
                    logger.debug(f"  [+] Initial activation: '{entry.id}' (prio: {priority}, depth: 0)")
        
        rendered_entry_ids: Set[str] = set()
        rendered_parts_with_priority = []
        rendering_pool = sorted(initial_pool, key=lambda x: x.priority_val, reverse=True)
        
        logger.debug("--- [STARTING RENDER LOOP] ---")
        
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
                                    depth=entry_to_render.depth + 1
                                )
                                newly_activated_this_pass.append(activated)
                                logger.debug(f"       [+] Recursive activation: '{entry.id}' (prio: {priority}, depth: {activated.depth})")
                
                if newly_activated_this_pass:
                    rendering_pool.extend(newly_activated_this_pass)
                    rendering_pool.sort(key=lambda x: x.priority_val, reverse=True)
        
        logger.debug("--- [FINALIZING OUTPUT] ---")
        pre_sort_log = ", ".join([f"{p['id']}({p['priority']})" for p in rendered_parts_with_priority])
        logger.debug(f"Rendered parts (in render order): [{pre_sort_log}]")
        
        final_sorted_parts = sorted(rendered_parts_with_priority, key=lambda p: p['priority'], reverse=True)
        
        post_sort_log = ", ".join([f"{p['id']}({p['priority']})" for p in final_sorted_parts])
        logger.debug(f"Final parts (sorted by priority): [{post_sort_log}]")

        final_text = "\n\n".join([p['content'] for p in final_sorted_parts])
        
        logger.debug(f"Final output text:\n---\n{final_text}\n---")
        logger.debug("--- [CODEX.INVOKE END] ---")

        if debug_mode:
            return { "output": { "final_text": final_text, "trace": {} } }
        
        return {"output": final_text}