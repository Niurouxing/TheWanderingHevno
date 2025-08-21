# plugins/core_engine/evaluation.py 

import ast
import asyncio
import re
from typing import Any, Dict, List, Optional   
from functools import partial
import random
import math
import datetime
import json
import re as re_module

from backend.core.utils import DotAccessibleDict 
from .contracts import ExecutionContext

INLINE_MACRO_REGEX = re.compile(r"{{\s*(.+?)\s*}}", re.DOTALL)
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
    从 ExecutionContext 构建宏的执行环境，注入新的三层作用域。
    """
    context = {
        **PRE_IMPORTED_MODULES,
        # 注入三层作用域，并用 DotAccessibleDict 包装以支持点符号访问
        "definition": DotAccessibleDict(exec_context.shared.definition_state),
        "lore": DotAccessibleDict(exec_context.shared.lore_state),
        "moment": DotAccessibleDict(exec_context.shared.moment_state),
        
        # 共享服务和会话信息保持不变
        "services": exec_context.shared.services, # services 已经是 DotAccessibleDict
        "session": DotAccessibleDict(exec_context.shared.session_info),
        
        # run 和 nodes 是当前图执行所私有的
        "run": DotAccessibleDict(exec_context.run_vars),
        "nodes": DotAccessibleDict(exec_context.node_states),
    }
    if pipe_vars is not None:
        context['pipe'] = DotAccessibleDict(pipe_vars)
        
    return context

# ... (evaluate_expression 和 evaluate_data 函数保持不变) ...
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
    if isinstance(data, str):
        # 模式1: 检查是否为“全宏替换”
        # 这种模式很重要，因为它允许宏返回非字符串类型（如列表、布尔值）
        full_match = MACRO_REGEX.match(data)
        if full_match:
            code_to_run = full_match.group(1)
            # 这里返回的结果可以是任何类型
            return await evaluate_expression(code_to_run, eval_context, lock)

        # 模式2: 如果不是全宏，检查是否包含“内联模板”
        # 这种模式的结果总是字符串
        if '{{' in data and '}}' in data:
            matches = list(INLINE_MACRO_REGEX.finditer(data))
            if not matches:
                # 包含 {{ 和 }} 但格式不正确，按原样返回
                return data

            # 并发执行所有宏的求值
            codes_to_run = [m.group(1) for m in matches]
            tasks = [evaluate_expression(code, eval_context, lock) for code in codes_to_run]
            evaluated_results = await asyncio.gather(*tasks)

            # 将求值结果替换回原字符串
            # 使用一个迭代器来确保替换顺序正确
            results_iter = iter(evaluated_results)
            # re.sub 的 lambda 每次调用时，都会从迭代器中取下一个结果
            # 这比多次调用 str.replace() 更安全、更高效
            final_string = INLINE_MACRO_REGEX.sub(lambda m: str(next(results_iter)), data)
            
            return final_string

        # 如果两种模式都不匹配，说明是普通字符串
        return data

    if isinstance(data, dict):
        keys = list(data.keys())
        # 创建异步任务列表
        value_tasks = [evaluate_data(data[k], eval_context, lock) for k in keys]
        # 并发执行所有值的求值
        evaluated_values = await asyncio.gather(*value_tasks)
        # 重新组装字典
        return dict(zip(keys, evaluated_values))

    if isinstance(data, list):
        # 并发执行列表中所有项的求值
        item_tasks = [evaluate_data(item, eval_context, lock) for item in data]
        return await asyncio.gather(*item_tasks)

    return data