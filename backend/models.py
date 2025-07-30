# backend/models.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any

class GenericNode(BaseModel):
    id: str
    data: Dict[str, Any] = Field(
        ...,
        description="节点的核心配置，必须包含 'runtime' 字段来指定执行器"
    )

    @field_validator('data')
    @classmethod
    def check_runtime_exists(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        # 这个验证器保持不变，依然很好用
        if 'runtime' not in v:
            raise ValueError("Node data must contain a 'runtime' field.")
        runtime_value = v['runtime']
        if not (isinstance(runtime_value, str) or 
                (isinstance(runtime_value, list) and all(isinstance(item, str) for item in runtime_value))):
            raise ValueError("'runtime' must be a string or a list of strings.")
        return v

class GraphDefinition(BaseModel):
    # 移除了 'edges'
    nodes: List[GenericNode]

class GraphCollection(BaseModel):
    # 整个配置文件的顶层模型
    # key 是 graph_id，value 是 GraphDefinition
    graphs: Dict[str, GraphDefinition] = Field(..., alias='root')

    @field_validator('graphs')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v
        
    @classmethod
    def model_validate(cls, obj: Any, *args, **kwargs) -> 'GraphCollection':
        # 允许我们直接用一个字典来验证，而不需要 'root' 键
        # 例如 GraphCollection.model_validate({"main": ...})
        if isinstance(obj, dict) and 'graphs' not in obj:
            return super().model_validate({'root': obj}, *args, **kwargs)
        return super().model_validate(obj, *args, **kwargs)