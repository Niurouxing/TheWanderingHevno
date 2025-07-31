# backend/core/dependency_parser.py 
import re
from typing import Set, Dict, Any, List

# 正则表达式，用于匹配 {{...}} 宏内部的 `nodes.node_id` 模式
# 它不再关心 `nodes.` 是否紧跟在 `{{` 之后。
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
            # 递归地检查 key 和 value
            # 注意：在真实的JSON中，key不可能是宏。但为了稳健，还是检查。
            deps.update(extract_dependencies_from_value(k))
            deps.update(extract_dependencies_from_value(v))
    return deps

def build_dependency_graph(nodes: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    根据节点列表自动构建依赖图。
    
    返回一个字典，key 是节点ID，value 是其依赖的节点ID集合。
    """
    dependency_map: Dict[str, Set[str]] = {}
    node_ids = {node['id'] for node in nodes}

    for node in nodes:
        node_id = node['id']
        node_data = node.get('data', {})
        
        # 递归地从节点的整个 data 负载中提取依赖
        dependencies = extract_dependencies_from_value(node_data)
        
        # 过滤掉不存在的节点ID，这可能是子图的输入占位符
        valid_dependencies = {dep for dep in dependencies if dep in node_ids}
        
        dependency_map[node_id] = valid_dependencies
    
    return dependency_map