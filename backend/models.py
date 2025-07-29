# backend/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# Edge模型保持不变
class Edge(BaseModel):
    source: str
    target: str

# 这是关键的重构：我们不再使用字面量类型 (Literal)
# 而是创建一个通用的节点模型
class GenericNode(BaseModel):
    id: str
    # 'type' 字段现在只用于前端UI渲染的提示，例如'input', 'output', 'default'
    # 它不再决定后端的执行逻辑
    type: str 
    
    # data 字段中包含了一个新的关键属性 'runtime'
    data: Dict[str, Any] = Field(
        ...,
        description="节点的核心配置，必须包含 'runtime' 字段来指定执行器"
    )

class Graph(BaseModel):
    nodes: List[GenericNode]
    edges: List[Edge]