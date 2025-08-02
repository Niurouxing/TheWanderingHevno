# backend/core/dependency_parser.py
import re
from typing import Set, Dict, Any, List

from backend.core.hooks import HookManager
from backend.core.plugin_types import ResolveNodeDependenciesContext
from backend.core.models import GenericNode

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

def build_dependency_graph(
    nodes: List[Dict[str, Any]], 
    hook_manager: HookManager
) -> Dict[str, Set[str]]:
    dependency_map: Dict[str, Set[str]] = {}
    node_map = {node['id']: GenericNode(**node) for node in nodes}

    for node in nodes:
        node_id = node['id']
        auto_inferred_deps = set()
        for instruction in node.get('run', []):
            instruction_config = instruction.get('config', {})
            dependencies = extract_dependencies_from_value(instruction_config)
            auto_inferred_deps.update(dependencies)
        
        explicit_deps = set(node.get('depends_on') or [])

        custom_deps = asyncio.run(hook_manager.decide(
            "resolve_node_dependencies",
            context=ResolveNodeDependenciesContext(
                node=node_instance,
                auto_inferred_deps=auto_inferred_deps.union(explicit_deps)
            )
        ))

        if custom_deps is not None:
            # 如果插件做出了决策，就使用插件的结果
            all_dependencies = custom_deps
        else:
            # 否则，使用默认逻辑
            all_dependencies = auto_inferred_deps.union(explicit_deps)
        
        # 不再过滤，保留所有依赖
        dependency_map[node_id] = all_dependencies
    
    return dependency_map