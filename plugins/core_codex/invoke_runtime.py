# plugins/core_codex/invoke_runtime.py
import asyncio
import re
from typing import Dict, Any, List, Optional, Set
import pprint  # 导入 pprint 以便美观地打印字典

from pydantic import ValidationError

from backend.core.interfaces import RuntimeInterface
from backend.core.state import ExecutionContext
from backend.core.evaluation import evaluate_data, build_evaluation_context
from backend.core.utils import DotAccessibleDict
from backend.core.registry import runtime_registry

from .models import CodexCollection, ActivatedEntry

from .models import TriggerMode

@runtime_registry.register("system.invoke")
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
        from_sources = config.get("from", [])
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
        
        structural_eval_context = build_evaluation_context(context)

        for source_config in from_sources:
            codex_name = source_config.get("codex")
            if not codex_name: continue
            
            codex_model = codex_collection.get(codex_name)
            if not codex_model:
                raise ValueError(f"Codex '{codex_name}' not found in world.codices.")

            source_text_macro = source_config.get("source", "")
            source_text = await evaluate_data(source_text_macro, structural_eval_context, lock) if source_text_macro else ""

            for entry in codex_model.entries:
                is_enabled = await evaluate_data(entry.is_enabled, structural_eval_context, lock)
                if not is_enabled:
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
                        if re.search(re.escape(str(keyword)), source_text, re.IGNORECASE):
                            matched_keywords.append(keyword)
                    if matched_keywords:
                        is_activated = True
                
                if is_activated:
                    activated = ActivatedEntry(
                        entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                        priority_val=int(priority), keywords_val=keywords, is_enabled_val=bool(is_enabled),
                        source_text=source_text, matched_keywords=matched_keywords
                    )
                    initial_pool.append(activated)
                    initial_activation_trace.append({
                        "id": entry.id, "priority": int(priority),
                        "reason": entry.trigger_mode.value,
                        "matched_keywords": matched_keywords
                    })
        
        # --- 2. 阶段二：渲染与注入 (Content Evaluation) ---
        final_text_parts = []
        rendered_entry_ids: Set[str] = set()
        rendering_pool = sorted(initial_pool, key=lambda x: x.priority_val, reverse=True)
        evaluation_log = []
        recursive_activations = []

        recursion_depth_counter = 0
        max_depth = max((act.codex_config.recursion_depth for act in rendering_pool), default=3) if rendering_pool else 3

        loop_count = 0
        while rendering_pool and (not recursion_enabled or recursion_depth_counter < max_depth):
            loop_count += 1
            rendering_pool.sort(key=lambda x: x.priority_val, reverse=True)
            
            entry_to_render = rendering_pool.pop(0)

            if entry_to_render.entry_model.id in rendered_entry_ids:
                continue

            content_eval_context = build_evaluation_context(context)
            content_eval_context['trigger'] = DotAccessibleDict({
                "source_text": entry_to_render.source_text,
                "matched_keywords": entry_to_render.matched_keywords
            })

            rendered_content = await evaluate_data(entry_to_render.entry_model.content, content_eval_context, lock)
            
            final_text_parts.append(str(rendered_content))
            rendered_entry_ids.add(entry_to_render.entry_model.id)
            evaluation_log.append({"id": entry_to_render.entry_model.id, "status": "rendered"})
            
            if recursion_enabled:
                recursion_depth_counter += 1
                new_source_text = str(rendered_content)
                
                for codex_name, codex_model in codex_collection.items():
                    for entry in codex_model.entries:
                        if entry.id in rendered_entry_ids or any(p.entry_model.id == entry.id for p in rendering_pool):
                            continue
                        
                        if entry.trigger_mode == TriggerMode.ON_KEYWORD:
                            is_enabled = await evaluate_data(entry.is_enabled, structural_eval_context, lock)
                            if not is_enabled: continue

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
                                recursive_activations.append({
                                    "id": entry.id, "priority": int(priority),
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
            return {
                "output": {
                    "final_text": final_text,
                    "trace": trace_data
                }
            }
        
        return {"output": final_text}
