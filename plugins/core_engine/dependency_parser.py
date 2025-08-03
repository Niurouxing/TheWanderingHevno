# plugins/core_engine/dependency_parser.py
import re
from typing import Set, Dict, Any, List
import asyncio


from backend.core.contracts import HookManager
from .contracts import ResolveNodeDependenciesContext, GenericNode

NODE_DEP_REGEX = re.compile(r'nodes\.([a-zA-Z0-9_]+)')

def extract_dependencies_from_string(s: str) -> Set[str]:
    if not isinstance(s, str):
        return set()
    if '{{' in s and '}}' in s and 'nodes.' in s:
        return set(NODE_DEP_REGEX.findall(s))
    return set()

def extract_dependencies_from_value(value: Any) -> Set[str]:
    deps = set()
    if isinstance(value, str):
        deps.update(extract_dependencies_from_string(value))
    elif isinstance(value, list):
        for item in value:
            deps.update(extract_dependencies_from_value(item))
    elif isinstance(value, dict):
        for k, v in value.items():
            deps.update(extract_dependencies_from_value(k))
            deps.update(extract_dependencies_from_value(v))
    return deps

async def build_dependency_graph_async(
    nodes: List[Dict[str, Any]],
    hook_manager: HookManager
) -> Dict[str, Set[str]]:
    dependency_map: Dict[str, Set[str]] = {}
    
    # 将所有节点字典预先转换为 Pydantic 模型实例，以便在钩子中使用
    node_map: Dict[str, GenericNode] = {node_dict['id']: GenericNode.model_validate(node_dict) for node_dict in nodes}

    for node_dict in nodes:
        node_id = node_dict['id']
        
        # 【核心修复】通过 node_id 从 node_map 中获取对应的模型实例
        node_instance = node_map[node_id]
        
        auto_inferred_deps = set()
        for instruction in node_dict.get('run', []):
            instruction_config = instruction.get('config', {})
            dependencies = extract_dependencies_from_value(instruction_config)
            auto_inferred_deps.update(dependencies)
    
        explicit_deps = set(node_dict.get('depends_on') or [])

        # 现在可以安全地调用 hook_manager 了
        custom_deps = await hook_manager.decide(
            "resolve_node_dependencies",
            context=ResolveNodeDependenciesContext(
                node=node_instance,
                auto_inferred_deps=auto_inferred_deps.union(explicit_deps)
            )
        )
        
        if custom_deps is not None:
            # 如果插件做出了决策，就使用插件的结果
            all_dependencies = custom_deps
        else:
            # 否则，使用默认逻辑
            all_dependencies = auto_inferred_deps.union(explicit_deps)
        
        dependency_map[node_id] = all_dependencies
    
    return dependency_map