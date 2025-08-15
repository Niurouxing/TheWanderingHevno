# plugins/core_engine/dependency_parser.py
import re
from typing import Set, Dict, Any, List
import asyncio

from plugins.core_engine.registry import RuntimeRegistry

NODE_DEP_REGEX = re.compile(r'nodes\.([^.]+)')

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
    runtime_registry: RuntimeRegistry 
) -> Dict[str, Set[str]]:
    dependency_map: Dict[str, Set[str]] = {}

    for node_dict in nodes:
        node_id = node_dict['id']
        auto_inferred_deps = set()

        for instruction in node_dict.get('run', []):
            runtime_name = instruction.get('runtime')
            if not runtime_name:
                continue

            # 1. 获取运行时类
            try:
                runtime_class = runtime_registry.get_runtime_class(runtime_name)
            except ValueError as e:
                # 如果运行时不存在，最好是抛出错误而不是静默失败
                raise ValueError(f"Error in node '{node_id}': {e}")

            # 2. 获取该运行时的依赖解析配置
            dep_config = runtime_class.get_dependency_config()
            ignore_fields = set(dep_config.get('ignore_fields', []))

            instruction_config = instruction.get('config', {})

            # 3. 根据配置进行智能扫描
            for field, value in instruction_config.items():
                if field in ignore_fields:
                    continue  # 跳过被忽略的字段
                
                # 对 value 进行递归扫描
                field_deps = extract_dependencies_from_value(value)
                auto_inferred_deps.update(field_deps)

        explicit_deps = set(node_dict.get('depends_on') or [])
        
        dependency_map[node_id] = auto_inferred_deps.union(explicit_deps)
    
    return dependency_map