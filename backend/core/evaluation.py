# backend/core/evaluation.py
import ast
import asyncio
import re
from typing import Any, Dict, List, Optional   
from functools import partial
from backend.core.utils import DotAccessibleDict
from backend.core.types import ExecutionContext # 显式导入，避免循环引用问题


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


def build_evaluation_context(
    exec_context: ExecutionContext,
    pipe_vars: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    从 ExecutionContext 和可选的管道变量构建一个扁平的字典，用作宏的执行环境。
    """
    context = {
        **PRE_IMPORTED_MODULES,
        "world": DotAccessibleDict(exec_context.world_state),
        "nodes": DotAccessibleDict(exec_context.node_states),
        "run": DotAccessibleDict(exec_context.run_vars),
        "session": DotAccessibleDict(exec_context.session_info),
        # --- 新增：将内部变量（包括锁）传递给上下文 ---
        "__internal__": exec_context.internal_vars
    }
    if pipe_vars is not None:
        context['pipe'] = DotAccessibleDict(pipe_vars)
        
    return context

# --- 修改 evaluate_expression ---
async def evaluate_expression(code_str: str, context: Dict[str, Any]) -> Any:
    """
    安全地执行一段 Python 代码字符串并返回结果。
    在执行前获取全局写入锁，确保宏的原子性。
    """
    # 1. 从上下文中提取锁
    lock = context.get("__internal__", {}).get("global_write_lock")
    
    # 2. 解析代码 (与之前相同)
    try:
        tree = ast.parse(code_str, mode='exec')
    except SyntaxError as e:
        raise ValueError(f"Macro syntax error: {e}\nCode: {code_str}")

    result_var = "_macro_result"
    
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        assign_node = ast.Assign(
            targets=[ast.Name(id=result_var, ctx=ast.Store())],
            value=tree.body[-1].value
        )
        tree.body[-1] = ast.fix_missing_locations(assign_node)

    # 3. 准备在非阻塞执行器中运行的同步函数
    loop = asyncio.get_running_loop()
    local_scope = {}
    exec_func = partial(exec, compile(tree, filename="<macro>", mode="exec"), context, local_scope)
    
    # 4. 在执行期间持有锁
    if lock:
        async with lock:
            # 锁被持有，现在可以在另一个线程中安全地执行阻塞代码
            await loop.run_in_executor(None, exec_func)
    else:
        # 如果没有锁（例如在测试环境中），直接执行
        await loop.run_in_executor(None, exec_func)
    
    # 5. 返回结果 (与之前相同)
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