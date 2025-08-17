# plugins/core_engine/schema_api.py
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.dependencies import Service
from .registry import RuntimeRegistry

logger = logging.getLogger(__name__)

schema_router = APIRouter(
    prefix="/api/editor",
    tags=["Editor API - Schemas"],
)

@schema_router.get("/schemas", summary="Get all runtime and node schemas for the editor")
async def get_editor_schemas(
    runtime_registry: RuntimeRegistry = Depends(Service("runtime_registry"))
):
    """
    为前端编辑器提供所有必要的 schema 定义。
    这包括所有已注册的运行时的配置 schema。
    """
    runtime_schemas = {}
    # _registry 是 RuntimeRegistry 的内部实现细节，直接访问以获取类
    for name, runtime_class in runtime_registry._registry.items():
        try:
            config_model = runtime_class.get_config_model()
            # 使用 Pydantic 的 .model_json_schema() 方法生成标准 JSON Schema
            runtime_schemas[name] = config_model.model_json_schema()
        except Exception as e:
            logger.error(f"Failed to generate schema for runtime '{name}': {e}", exc_info=True)
            runtime_schemas[name] = {
                "title": "Error",
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "default": f"Schema generation failed for {name}: {e}"
                    }
                }
            }
            
    return {
        "runtimes": runtime_schemas
    }