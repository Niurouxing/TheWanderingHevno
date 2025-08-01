# backend/core/evaluation.py
import ast
import asyncio
import re
from typing import Any, Dict, List, Optional   
from functools import partial
from backend.core.utils import DotAccessibleDict
from backend.core.types import ExecutionContext # 显式导入

# 预编译宏的正则表达式和预置模块保持不变...
MACRO_REGEX = re.compile(r"^{{\s*(.+)\s*}}$", re.DOTALL)
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
    从 ExecutionContext 构建宏的执行环境。
    这个函数现在变得非常简单，因为它信任传入的上下文。
    """
    context = {
        **PRE_IMPORTED_MODULES,
        # 直接从共享上下文中获取 world 和 session
        "world": DotAccessibleDict(exec_context.shared.world_state),
        "session": DotAccessibleDict(exec_context.shared.session_info),
        # run 和 nodes 是当前图执行所私有的
        "run": DotAccessibleDict(exec_context.run_vars),
        "nodes": DotAccessibleDict(exec_context.node_states),
    }
    if pipe_vars is not None:
        context['pipe'] = DotAccessibleDict(pipe_vars)
        
    return context

async def evaluate_expression(code_str: str, context: Dict[str, Any], lock: asyncio.Lock) -> Any:
    """..."""
    # ast.parse 可能会失败，需要 try...except
    try:
        tree = ast.parse(code_str, mode='exec')
    except SyntaxError as e:
        raise ValueError(f"Macro syntax error: {e}\nCode: {code_str}")

    # 如果代码块为空，直接返回 None
    if not tree.body:
        return None

    # 如果最后一行是表达式，我们将其转换为一个赋值语句，以便捕获结果
    result_var = "_macro_result"
    if isinstance(tree.body[-1], ast.Expr):
        # 包装最后一条表达式
        assign_node = ast.Assign(
            targets=[ast.Name(id=result_var, ctx=ast.Store())],
            value=tree.body[-1].value
        )
        tree.body[-1] = ast.fix_missing_locations(assign_node)
    
    # 将 AST 编译为代码对象
    code_obj = compile(tree, filename="<macro>", mode="exec")
    
    # 在锁的保护下运行
    async with lock:
        # 在另一个线程中运行，以避免阻塞事件循环
        # 注意：这里我们直接修改传入的 context 字典来捕获结果
        await asyncio.get_running_loop().run_in_executor(
            None, exec, code_obj, context
        )
    
    # 从被修改的上下文字典中获取结果
    return context.get(result_var)

async def evaluate_data(data: Any, eval_context: Dict[str, Any], lock: asyncio.Lock) -> Any:
    # (lock 不再是可选的)
    """..."""
    if isinstance(data, str):
        match = MACRO_REGEX.match(data)
        if match:
            code_to_run = match.group(1)
            # 确保 lock 被传递
            return await evaluate_expression(code_to_run, eval_context, lock)
        return data

        
    if isinstance(data, dict):
        keys = data.keys()
        # 传递 lock
        values = [evaluate_data(v, eval_context, lock) for v in data.values()]
        evaluated_values = await asyncio.gather(*values)
        return dict(zip(keys, evaluated_values))

    if isinstance(data, list):

        items = [evaluate_data(item, eval_context, lock) for item in data]
        return await asyncio.gather(*items)

    return data