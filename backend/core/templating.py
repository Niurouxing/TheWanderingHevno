# backend/core/templating.py (最终正确版)
import jinja2
from typing import Any
from backend.core.runtime import ExecutionContext

# create_template_environment 不再需要，可以删除或简化为一个只创建env的函数
def get_jinja_env():
    return jinja2.Environment(
        enable_async=True,
        # 修复：使用 StrictUndefined，这样当变量不存在时会抛出 UndefinedError
        undefined=jinja2.StrictUndefined 
    )

async def render_template(template_str: str, context: ExecutionContext) -> str:
    """
    一个辅助函数，使用最新的上下文来渲染模板。
    """
    if '{{' not in template_str:
        return template_str
        
    env = get_jinja_env()
    template = env.from_string(template_str)
    
    # 动态构建完整的渲染上下文
    render_context = {
        "nodes": context.state,
        "vars": context.global_vars,
        "session": context.session_info,
        # 未来可以在这里注入函数
    }

    try:
        return await template.render_async(render_context)
    except Exception as e:
        raise IOError(f"Template rendering failed: {e}")