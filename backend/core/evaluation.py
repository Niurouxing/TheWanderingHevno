# backend/core/evaluation.py
import ast
import asyncio
import re
from typing import Any, Dict, List
from functools import partial

# 预编译宏的正则表达式，用于快速查找
MACRO_REGEX = re.compile(r"^{{\s*(.+)\s*}}$", re.DOTALL)

# --- 预置的、开箱即用的模块 ---
# 我们在这里定义它们，以便在构建上下文时注入
import random
import math
import datetime
import json
import re as re_module

PRE_IMPORTED_MODULES = {
    "random": random,
    "math": math,
    "datetime": datetime,
    "json": json,
    "re": re_module,
}

def build_evaluation_context(exec_context: 'ExecutionContext') -> Dict[str, Any]:
    """从 ExecutionContext 构建一个扁平的字典，用作宏的执行环境。"""
    # 这个上下文将作为 exec() 的 `globals`
    return {
        **PRE_IMPORTED_MODULES,
        "world": exec_context.world_state,
        "nodes": exec_context.node_states,
        "run": exec_context.run_vars,
        "session": exec_context.session_info,
    }

async def evaluate_expression(code_str: str, context: Dict[str, Any]) -> Any:
    """
    安全地执行一段 Python 代码字符串并返回结果。
    这是宏系统的执行核心。
    """
    # 使用 ast 来智能处理返回值
    # 1. 解析代码
    try:
        tree = ast.parse(code_str, mode='exec')
    except SyntaxError as e:
        raise ValueError(f"Macro syntax error: {e}\nCode: {code_str}")

    result_var = "_macro_result"
    
    # 2. 如果最后一条语句是表达式，将其结果赋值给 _macro_result
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        # 创建一个赋值节点
        assign_node = ast.Assign(
            targets=[ast.Name(id=result_var, ctx=ast.Store())],
            value=tree.body[-1].value
        )
        # 替换最后一个表达式节点
        tree.body[-1] = ast.fix_missing_locations(assign_node)

    # 3. 在非阻塞的执行器中运行同步的 exec
    loop = asyncio.get_running_loop()
    
    # exec 需要一个 globals 和一个 locals 字典
    local_scope = {}

    # partial 将函数和其参数打包，以便 run_in_executor 调用
    exec_func = partial(exec, compile(tree, filename="<macro>", mode="exec"), context, local_scope)
    
    await loop.run_in_executor(None, exec_func)
    
    # 4. 返回结果
    return local_scope.get(result_var)


async def evaluate_data(data: Any, eval_context: Dict[str, Any]) -> Any:
    """
    递归地遍历一个数据结构 (dict, list)，查找并执行所有宏。
    这是 `_execute_node` 将调用的主入口函数。
    """
    if isinstance(data, str):
        match = MACRO_REGEX.match(data)
        if match:
            code_to_run = match.group(1)
            # 发现宏，执行它并返回结果
            return await evaluate_expression(code_to_run, eval_context)
        # 不是宏，原样返回
        return data
        
    if isinstance(data, dict):
        # 异步地处理字典中的所有值
        # 注意：我们不处理 key，只处理 value
        keys = data.keys()
        values = [evaluate_data(v, eval_context) for v in data.values()]
        evaluated_values = await asyncio.gather(*values)
        return dict(zip(keys, evaluated_values))

    if isinstance(data, list):
        # 异步地处理列表中的所有项
        items = [evaluate_data(item, eval_context) for item in data]
        return await asyncio.gather(*items)

    # 对于其他类型（数字、布尔等），原样返回
    return data