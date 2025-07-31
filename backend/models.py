# backend/models.py
from pydantic import BaseModel, Field, field_validator, RootModel
from typing import List, Dict, Any

class GenericNode(BaseModel):
    id: str
    data: Dict[str, Any] = Field(
        ...,
        description="节点的核心配置。如果提供了 'runtime' 字段，它将指定执行器。"
    )

    @field_validator('data')
    @classmethod
    def check_runtime_if_exists(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        # 3. 修改验证器逻辑：只在 'runtime' 存在时检查它
        if 'runtime' in v:
            runtime_value = v['runtime']
            if not (isinstance(runtime_value, str) or 
                    (isinstance(runtime_value, list) and all(isinstance(item, str) for item in runtime_value))):
                raise ValueError("'runtime' must be a string or a list of strings.")
        # 如果 'runtime' 不存在，则节点是有效的，直接返回
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