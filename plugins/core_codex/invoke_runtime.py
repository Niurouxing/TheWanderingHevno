# plugins/core_codex/invoke_runtime.py (已修复)

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
# 【修复】导入 Codex 模型，以便进行智能合并
from .models import CodexCollection, ActivatedEntry, TriggerMode, Codex

logger = logging.getLogger("hevno.runtime.codex")


def _merge_codices(lore_codices: Dict[str, Any], moment_codices: Dict[str, Any]) -> Dict[str, Any]:
    """
    一个更智能的合并函数，用于合并 Lore 和 Moment 中的 Codex。
    - 它会合并同名 Codex 的条目列表。
    - 如果条目 ID 相同，Moment 中的条目会覆盖 Lore 中的。
    """
    # 先深拷贝 lore 的数据作为基础，避免修改原始状态
    from copy import deepcopy
    merged_data = deepcopy(lore_codices)

    for name, moment_codex_data in moment_codices.items():
        if name not in merged_data:
            # 如果 Lore 中没有这个 Codex，直接添加
            merged_data[name] = deepcopy(moment_codex_data)
        else:
            # 如果 Lore 中有同名 Codex，进行条目级别的合并
            lore_codex_data = merged_data[name]
            
            # 合并 config, moment 优先
            lore_codex_data['config'] = {**lore_codex_data.get('config', {}), **moment_codex_data.get('config', {})}
            
            # 合并 entries, moment 优先
            lore_entries = lore_codex_data.get('entries', [])
            moment_entries = moment_codex_data.get('entries', [])
            
            # 使用字典来处理覆盖逻辑，以 entry id 为键
            entries_map: Dict[str, Any] = {entry['id']: entry for entry in lore_entries}
            for entry in moment_entries:
                entries_map[entry['id']] = entry
            
            # 将合并后的条目转换回列表
            lore_codex_data['entries'] = list(entries_map.values())
    
    return merged_data


class InvokeRuntime(RuntimeInterface):
    """
    【已重构】codex.invoke 运行时的实现。
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
        

        lore_codices = context.shared.lore_state.get("codices", {})
        moment_codices = context.shared.moment_state.get("codices", {})
        
        unified_codex_data = _merge_codices(lore_codices, moment_codices)
        
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