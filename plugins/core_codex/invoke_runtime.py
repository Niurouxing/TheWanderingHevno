# plugins/core_codex/invoke_runtime.py

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Set, Type
from copy import deepcopy

from pydantic import ValidationError, BaseModel, Field

from backend.core.utils import DotAccessibleDict
from plugins.core_engine.contracts import (
    RuntimeInterface, 
    ExecutionContext,
    MacroEvaluationServiceInterface
)
from .models import CodexCollection, ActivatedEntry, TriggerMode, Codex

logger = logging.getLogger("hevno.runtime.codex")


def _merge_codices(lore_codices: Dict[str, Any], moment_codices: Dict[str, Any]) -> Dict[str, Any]:
    """
    智能地合并 Lore 和 Moment 中的 Codex。
    - 它会合并同名 Codex 的条目列表。
    - 如果条目 ID 相同，Moment 中的条目会覆盖 Lore 中的。
    """
    merged_data = deepcopy(lore_codices)
    for name, moment_codex_data in moment_codices.items():
        if name not in merged_data:
            merged_data[name] = deepcopy(moment_codex_data)
        else:
            lore_codex_data = merged_data[name]
            lore_codex_data['config'] = {**lore_codex_data.get('config', {}), **moment_codex_data.get('config', {})}
            
            lore_entries = lore_codex_data.get('entries', [])
            moment_entries = moment_codex_data.get('entries', [])
            
            entries_map: Dict[str, Any] = {entry['id']: entry for entry in lore_entries}
            for entry in moment_entries:
                entries_map[entry['id']] = entry
            
            lore_codex_data['entries'] = list(entries_map.values())
    
    return merged_data


class InvokeRuntime(RuntimeInterface):
    """
    codex.invoke: 从 Lore 和 Moment 中收集、合并、渲染知识条目，生成最终文本。
    """
    class FromSource(BaseModel):
        codex: str = Field(..., description="要扫描的知识库的名称。")
        source: Optional[str] = Field(
            default="", 
            description="一个包含宏的字符串，其求值结果将作为触发 on_keyword 模式的源文本。"
        )

    class ConfigModel(BaseModel):
        from_: List['InvokeRuntime.FromSource'] = Field(
            ..., 
            alias="from",
            description="定义要从哪些知识库中、使用什么源文本来激活条目的列表。"
        )
        recursion_enabled: bool = Field(
            default=False, 
            description="是否允许已激活条目的内容再次触发新的条目，形成逻辑链。"
        )
        debug: bool = Field(
            default=False, 
            description="是否在输出中返回详细的调试信息。"
        )

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
        except Exception as e:
            return {"error": f"Invalid configuration for codex.invoke: {e}"}

        macro_service: MacroEvaluationServiceInterface = context.shared.services.macro_evaluation_service
        lock = context.shared.global_write_lock
        
        lore_codices = context.shared.lore_state.get("codices", {})
        moment_codices = context.shared.moment_state.get("codices", {})
        unified_codex_data = _merge_codices(lore_codices, moment_codices)
        
        if not unified_codex_data:
            return {"output": ""}
            
        try:
            codex_collection = CodexCollection.model_validate(unified_codex_data).root
        except ValidationError as e:
            raise ValueError(f"Invalid codex structure after merging lore and moment: {e}")
            
        initial_pool: List[ActivatedEntry] = []
        structural_eval_context = macro_service.build_context(context)

        for source_config in validated_config.from_:
            codex_name = source_config.codex
            if not codex_name or not codex_collection.get(codex_name):
                continue
            
            codex_model = codex_collection[codex_name]
            source_text = await macro_service.evaluate(source_config.source, structural_eval_context, lock) if source_config.source else ""
            
            for entry in codex_model.entries:
                is_enabled = await macro_service.evaluate(entry.is_enabled, structural_eval_context, lock)
                if not is_enabled: continue
                
                keywords = await macro_service.evaluate(entry.keywords, structural_eval_context, lock)
                priority = await macro_service.evaluate(entry.priority, structural_eval_context, lock)

                is_activated, matched_keywords = False, []
                if entry.trigger_mode == TriggerMode.ALWAYS_ON:
                    is_activated = True
                elif entry.trigger_mode == TriggerMode.ON_KEYWORD and source_text and keywords:
                    matched_keywords = [kw for kw in keywords if re.search(re.escape(str(kw)), str(source_text), re.IGNORECASE)]
                    if matched_keywords: is_activated = True
                
                if is_activated:
                    activated = ActivatedEntry(
                        entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                        priority_val=int(priority), keywords_val=keywords, is_enabled_val=bool(is_enabled),
                        source_text=str(source_text), matched_keywords=matched_keywords, depth=0
                    )
                    initial_pool.append(activated)
        
        rendered_entry_ids: Set[str] = set()
        rendered_parts_with_priority = []
        rendering_pool = sorted(initial_pool, key=lambda x: x.priority_val, reverse=True)
        
        while rendering_pool:
            entry_to_render = rendering_pool.pop(0)
            if entry_to_render.entry_model.id in rendered_entry_ids: continue
            
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
            if validated_config.recursion_enabled and entry_to_render.depth < max_depth:
                for codex_name, codex_model in codex_collection.items():
                    for entry in codex_model.entries:
                        if entry.id in rendered_entry_ids or any(p.entry_model.id == entry.id for p in rendering_pool): continue
                        if entry.trigger_mode != TriggerMode.ON_KEYWORD: continue
                        
                        is_enabled = await macro_service.evaluate(entry.is_enabled, structural_eval_context, lock)
                        if not is_enabled: continue
                        keywords = await macro_service.evaluate(entry.keywords, structural_eval_context, lock)
                        new_matched_keywords = [kw for kw in keywords if re.search(re.escape(str(kw)), rendered_content, re.IGNORECASE)]
                        
                        if new_matched_keywords:
                            priority = await macro_service.evaluate(entry.priority, structural_eval_context, lock)
                            activated = ActivatedEntry(
                                entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                                priority_val=int(priority), keywords_val=keywords, is_enabled_val=is_enabled,
                                source_text=rendered_content, matched_keywords=new_matched_keywords,
                                depth=entry_to_render.depth + 1
                            )
                            rendering_pool.append(activated)
                rendering_pool.sort(key=lambda x: x.priority_val, reverse=True)
        
        final_sorted_parts = sorted(rendered_parts_with_priority, key=lambda p: p['priority'], reverse=True)
        final_text = "\n\n".join([p['content'] for p in final_sorted_parts])
        
        if validated_config.debug:
            return {"output": final_text, "debug_info": {"rendered_ids": list(rendered_entry_ids)}}
        
        return {"output": final_text}