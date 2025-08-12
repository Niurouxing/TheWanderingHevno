# plugins/core_engine/models.py
from pydantic import BaseModel, Field, RootModel, field_validator
from typing import List, Dict, Any, Optional # <-- 导入 Optional

class RuntimeInstruction(BaseModel):
    """
    一个运行时指令，封装了运行时名称及其隔离的配置。
    这是节点执行逻辑的基本单元。
    """
    runtime: str
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="该运行时专属的、隔离的配置字典。"
    )

class GenericNode(BaseModel):
    """
    节点模型，现在以一个有序的运行时指令列表为核心。
    """
    id: str
    run: List[RuntimeInstruction] = Field(
        ...,
        description="定义节点执行逻辑的有序指令列表。"
    )
    depends_on: Optional[List[str]] = Field(
        default=None,
        description="一个可选的列表，用于明确声明此节点在执行前必须等待的其他节点的ID。用于处理无法通过宏自动推断的隐式依赖。"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphDefinition(RootModel[Dict[str, Any]]):
    """
    图定义，本质上是一个字典。
    它必须包含一个 'nodes' 键，其值为一个节点列表。
    """
    @field_validator('root')
    @classmethod
    def check_nodes_exist_and_are_valid(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """验证器，确保 'nodes' 键存在且其内容是有效的节点列表。"""
        if "nodes" not in v:
            raise ValueError("A 'nodes' list must be defined in the graph definition.")
        
        # Pydantic v2 会自动验证内部列表的类型，如果 GenericNode 被正确定义。
        # 这里我们手动触发一次验证以确保健壮性。
        validated_nodes = [GenericNode.model_validate(node) for node in v["nodes"]]
        v["nodes"] = validated_nodes # 可以选择用验证过的模型替换原始数据
        return v

    @property
    def nodes(self) -> List[GenericNode]:
        """提供便捷的属性访问器，用法与旧模型保持一致。"""
        return self.root['nodes']
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """提供便捷的属性访问器。"""
        return self.root.get('metadata', {})

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    """
    整个配置文件的顶层模型。
    使用 RootModel，模型本身就是一个 `Dict[str, GraphDefinition]`。
    """
    
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        """验证器，确保存在一个 'main' 图作为入口点。"""
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v