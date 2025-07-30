# backend/models.py
from pydantic import BaseModel, Field, field_validator, RootModel
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

    nodes: List[GenericNode]

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    """
    整个配置文件的顶层模型。
    使用 RootModel，模型本身就是一个 `Dict[str, GraphDefinition]`。
    """
    
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        """验证器现在作用于 'root' 字段，即模型本身。"""
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v