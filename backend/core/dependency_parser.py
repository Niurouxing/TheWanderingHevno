# backend/core/dependency_parser.py 
import re
from typing import Set, Dict, Any, List

# 正则表达式，用于匹配 {{...}} 宏内部的 `nodes.node_id` 模式
NODE_DEP_REGEX = re.compile(r'nodes\.([a-zA-Z0-9_]+)')

def extract_dependencies_from_string(s: str) -> Set[str]:
    """从单个字符串中提取所有节点依赖。"""
    if not isinstance(s, str):
        return set()
    # 仅在检测到宏标记时才进行解析，以提高效率并避免误报
    if '{{' in s and '}}' in s and 'nodes.' in s:
        return set(NODE_DEP_REGEX.findall(s))
    return set()

def extract_dependencies_from_value(value: Any) -> Set[str]:
    """递归地从任何值（字符串、列表、字典）中提取依赖。"""
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

def build_dependency_graph(nodes: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    根据节点列表自动构建依赖图。
    会合并从宏中自动推断的依赖和从 `depends_on` 字段中明确声明的依赖。
    """
    dependency_map: Dict[str, Set[str]] = {}
    node_ids = {node['id'] for node in nodes}

    for node in nodes:
        node_id = node['id']
        
        # 1. 从宏中自动推断依赖 
        auto_inferred_deps = set()
        for instruction in node.get('run', []):
            instruction_config = instruction.get('config', {})
            dependencies = extract_dependencies_from_value(instruction_config)
            auto_inferred_deps.update(dependencies)
        
        # 2. 从 `depends_on` 字段中获取明确的依赖 
        explicit_deps = set(node.get('depends_on') or [])

        # 3. 合并两种依赖
        all_dependencies = auto_inferred_deps.union(explicit_deps)
        
        # 4. 过滤掉不存在的节点ID
        valid_dependencies = {dep for dep in all_dependencies if dep in node_ids}
        dependency_map[node_id] = valid_dependencies
    
    return dependency_map