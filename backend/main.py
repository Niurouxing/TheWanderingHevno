# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 1. 导入新的模型和核心组件
from backend.models import Graph
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry

# 2. 导入并注册基础运行时
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime

# --- 初始化和插件加载 ---
def setup_application():
    app = FastAPI(
        title="Hevno Backend",
        description="The core execution engine for Hevno project.",
        version="0.1.0-refactored"
    )
    
    # 注册核心运行时
    runtime_registry.register("system.input", InputRuntime)
    runtime_registry.register("system.template", TemplateRuntime)
    runtime_registry.register("llm.default", LLMRuntime)

    # --- 这里是未来插件系统的入口 ---
    # def load_plugins():
    #     # 伪代码: 扫描 'plugins' 目录
    #     # for plugin_module in find_plugins():
    #     #     plugin_module.register(runtime_registry, function_registry, ...)
    # load_plugins()
    
    # CORS中间件
    origins = ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

app = setup_application()
execution_engine = ExecutionEngine(registry=runtime_registry)

# --- API 端点 ---
@app.post("/api/graphs/execute")
async def execute_graph_endpoint(graph: Graph):
    try:
        result_context = await execution_engine.execute(graph)
        return result_context
    except ValueError as e:
        # 捕获已知的用户输入错误，例如环路
        raise HTTPException(status_code=400, detail=f"Invalid graph structure: {e}")
    except Exception as e:
        # 未预料到的服务器内部错误
        # 可以在这里添加日志记录
        # import logging; logging.exception("Graph execution failed")
        raise HTTPException(status_code=500, detail=f"An unexpected graph execution error occurred: {e}")
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on refactored architecture!"}