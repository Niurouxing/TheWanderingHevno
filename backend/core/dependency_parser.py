# backend/core/dependency_parser.py
import re
from typing import Set, Dict, Any, List

# 正则表达式，用于匹配 {{ nodes.node_id... }} 格式的宏
# - 匹配 '{{' 和 '}}'
# - 捕获 'nodes.' 后面的第一个标识符 (node_id)
# - 这是一个非贪婪匹配，以处理嵌套宏等情况
NODE_DEP_REGEX = re.compile(r'{{\s*nodes\.([a-zA-Z0-9_]+)')

def extract_dependencies_from_string(s: str) -> Set[str]:
    """从单个字符串中提取所有节点依赖。"""
    if not isinstance(s, str):
        return set()
    return set(NODE_DEP_REGEX.findall(s))

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
