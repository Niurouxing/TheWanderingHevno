# backend/models.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any

# Edge模型保持不变
class Edge(BaseModel):
    source: str
    target: str

# 这是关键的重构：我们不再使用字面量类型 (Literal)
# 而是创建一个通用的节点模型
class GenericNode(BaseModel):
    id: str
    
    data: Dict[str, Any] = Field(
        ...,
        description="节点的核心配置，必须包含 'runtime' 字段来指定执行器"
    )

    @field_validator('data')
    @classmethod
    def check_runtime_exists(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if 'runtime' not in v:
            raise ValueError("Node data must contain a 'runtime' field.")
        
        runtime_value = v['runtime']
        if not (isinstance(runtime_value, str) or 
                (isinstance(runtime_value, list) and all(isinstance(item, str) for item in runtime_value))):
            raise ValueError("'runtime' must be a string or a list of strings.")
            
        return v

class Graph(BaseModel):
    nodes: List[GenericNode]
    edges: List[Edge]