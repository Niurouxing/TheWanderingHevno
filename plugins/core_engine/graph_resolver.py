# plugins/core_engine/graph_resolver.py

import logging
from typing import Dict, Any
from copy import deepcopy

from .contracts import ExecutionContext, GraphCollection

logger = logging.getLogger(__name__)

class GraphResolver:
    """
    负责在每次图执行前，根据上下文动态地“组装”出最终要执行的图集合。
    """
    def resolve(self, context: ExecutionContext) -> GraphCollection:
        """
        根据上下文中的 Lore 和 Moment 作用域，合并和验证图定义。
        Moment 中的图会覆盖 Lore 中的同名图。
        """
        logger.debug("Resolving graph collection from Lore and Moment states...")

        # 1. 从 lore_state 获取基础图集合，如果没有则为空字典
        # 使用 deepcopy 以避免意外修改原始上下文
        base_graphs = deepcopy(context.shared.lore_state.get('graphs', {}))
        
        # 2. 从 moment_state 获取覆盖图集合
        override_graphs = deepcopy(context.shared.moment_state.get('graphs', {}))

        # 3. 将两者合并。字典的 update 方法天然地实现了覆盖逻辑。
        # 如果 override_graphs 中有与 base_graphs 同名的键，其值将覆盖 base_graphs 中的值。
        final_graph_data = {**base_graphs, **override_graphs}
        
        if not final_graph_data:
            raise ValueError("No graph definitions found in 'lore.graphs' or 'moment.graphs'.")

        logger.debug(f"Final merged graph keys: {list(final_graph_data.keys())}")
        
        # 4. 使用 Pydantic 模型进行验证
        try:
            validated_collection = GraphCollection.model_validate(final_graph_data)
        except Exception as e:
            logger.error(f"Failed to validate the final merged graph collection: {e}")
            raise ValueError(f"Invalid graph structure after merging Lore and Moment. Error: {e}")

        return validated_collection