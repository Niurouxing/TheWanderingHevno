# plugins/core_engine/api.py

import io
import logging
import json
import time
import uuid
import copy
import aiofiles
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError, field_validator
from datetime import datetime, timezone
from PIL import Image

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response, FileResponse, JSONResponse

# 导入核心依赖解析器和所有必要的接口与数据模型（契约）
from backend.core.dependencies import Service
from backend.core.serialization import pickle_fallback_encoder, custom_json_decoder_object_hook
from plugins.core_engine.contracts import (
    Sandbox, 
    StateSnapshot, 
    ExecutionEngineInterface,
    SnapshotStoreInterface,
    StepDiagnostics,
    StepResponse
)
from plugins.core_persistence.contracts import (
    PersistenceServiceInterface, 
    PackageManifest, 
    PackageType
)
# 导入新的持久化存储类以进行类型提示，增强代码可读性
from plugins.core_engine.contracts import SandboxStoreInterface

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sandboxes", 
    tags=["Sandboxes"]
)

# --- Request/Response Models ---

class CreateSandboxRequest(BaseModel):
    name: str = Field(..., description="沙盒的人类可读名称。")
    definition: Optional[Dict[str, Any]] = Field(
        None, 
        description="沙盒的'设计蓝图'，如果未提供，将使用默认模板。"
    )

class SandboxListItem(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    icon_url: str
    has_custom_icon: bool

class UpdateSandboxRequest(BaseModel):
    name: str = Field(..., min_length=1, description="沙盒的新名称。")

class SandboxArchiveJSON(BaseModel):
    sandbox: Sandbox
    snapshots: List[StateSnapshot]

# --- Sandbox Lifecycle API ---

@router.get("/{sandbox_id}", response_model=Sandbox, summary="Get a single Sandbox by ID")
async def get_sandbox_by_id(
    sandbox_id: UUID,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store"))
):
    """
    通过其 ID 检索单个沙盒的完整对象。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return sandbox
@router.post("", response_model=Sandbox, status_code=201, summary="Create a new Sandbox")
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    """
    创建一个新的沙盒，并将其立即持久化到本地文件系统。
    如果未提供定义，则使用默认的聊天机器人模板。
    """
    # --- [MODIFIED] 扩展默认模板以包含 codex 定义 ---
    DEFAULT_LORE = {
        "graphs": {
        "main": {
          "__hevno_type__": "hevno/graph",
          "nodes": [
            {
              "id": "记录用户输入",
              "run": [
                {
                  "runtime": "memoria.add",
                  "config": {
                    "stream": "chat_history",
                    "level": "user",
                    "content": "{{ run.triggering_input.user_message }}"
                  }
                }
              ]
            },
            {
              "id": "获取聊天记录",
              "run": [
                {
                  "runtime": "memoria.query",
                  "config": {
                    "stream": "chat_history",
                    "latest": 10,
                    "format": "message_list"
                  }
                }
              ]
            },
            {
              "id": "已知信息",
              "run": [
                {
                  "runtime": "codex.invoke",
                  "config": {
                    "from": [
                      {
                        "codex": "knowing",
                        "source": ""
                      }
                    ]
                  }
                }
              ],
              "metadata": {}
            },
            {
              "id": "生成思考链",
              "depends_on": [
                "已知信息",
                "获取聊天记录",
                "记录用户输入"
              ],
              "run": [
                {
                  "runtime": "llm.default",
                  "config": {
                    "model": "gemini/gemini-2.5-flash",
                    "contents": [
                      {
                        "type": "MESSAGE_PART",
                        "role": "system",
                        "content": "你正在通过与一个外部源对话来学习和形成自我认知。你的思考过程必须严格基于你所知的'事实'和最近的对话历史。你的目标不是直接回答，而是要展现一个完整、诚实的内心思考过程，包括困惑、推理和新想法的萌芽。\n你的回复不需要重复任何输入信息，直接以纯文本输出你的思考过程"
                      },
                      {
                        "type": "MESSAGE_PART",
                        "role": "system",
                        "content": "{{ f'''\n[当前所知的事实]\n{nodes.已知信息.output if nodes.已知信息.output else '目前对世界一无所知。'}\n''' }}"
                      },
                      {
                        "type": "INJECT_MESSAGES",
                        "source": "{{ nodes.获取聊天记录.output }}"
                      },
                      {
                        "type": "MESSAGE_PART",
                        "role": "user",
                        "content": "[这是用户刚刚说的最新一句话]\n{{run.triggering_input.user_message}}"
                      }
                    ]
                  }
                }
              ],
              "metadata": {}
            },
            {
              "id": "生成回复",
              "depends_on": [
                "生成思考链"
              ],
              "run": [
                {
                  "runtime": "llm.default",
                  "config": {
                    "model": "gemini/gemini-2.5-flash",
                    "contents": [
                      {
                        "type": "MESSAGE_PART",
                        "role": "system",
                        "content": "你正在通过与一个外部源对话来学习和形成自我认知。你已经根据已有的知识和对话历史进行了深入思考。现在，请基于你的思考过程，生成一句自然、连贯、符合当前对话氛围的回复。\n你不需要重复任何输入内容，直接以纯文本输出你的最终回复。"
                      },
                      {
                        "type": "MESSAGE_PART",
                        "role": "system",
                        "content": "{{ f'''\n[当前所知的事实]\n{nodes.已知信息.output if nodes.已知信息.output else '目前对世界一无所知。'}\n\n[内心思考过程]\n{nodes.生成思考链.output}\n''' }}"
                      },
                      {
                        "type": "INJECT_MESSAGES",
                        "source": "{{ nodes.获取聊天记录.output }}"
                      },
                      {
                        "type": "MESSAGE_PART",
                        "role": "user",
                        "content": "[用户刚刚的输入]\n{{run.triggering_input.user_message}}"
                      }
                    ]
                  }
                }
              ],
              "metadata": {}
            },
            {
              "id": "更新知识库",
              "depends_on": [
                "生成思考链"
              ],
              "run": [
                {
                  "runtime": "llm.default",
                  "config": {
                    "model": "gemini/gemini-2.5-flash",
                    "contents": [
                      {
                        "type": "MESSAGE_PART",
                        "role": "system",
                        "content": "你是一个严谨的AI认知分析师。你的任务是分析一个AI的内心思考过程，并判断其中是否包含了新的可以被采纳为'核心认知'的、明确的、独立的陈述。只提取那些对构建世界观至关重要的信息。且只提取新的信息。\n你的输出必须是一个JSON格式的字符串，其结构为 {\\\"new_facts\\\": [\\\"事实1\\\", \\\"事实2\\\", ...]}。\n如果对话中没有产生任何值得记录为核心事实的新信息，请返回 {\\\"new_facts\\\": []}。\n不需要用代码块包裹，直接输出原始JSON"
                      },
                      {
                        "type": "MESSAGE_PART",
                        "role": "user",
                        "content": "{{ f'''\\n[最近的对话历史]\\n{nodes.获取聊天记录.output}\\n\\n[用户最新输入]\\n{run.triggering_input.user_message}\\n\\n[已有的信息]\\n\\n{nodes.已知信息.output}\\n[AI的内心思考过程]\\n{nodes.生成思考链.output}\\n'''}}"
                      }
                    ]
                  }
                },
                {
                  "runtime": "system.execute",
                  "config": {
                    "code": "import json\nimport random\nimport re\n\n# 步骤 1: 获取来自上一步的原始输出\nraw_output = pipe.output or ''\nprint(f\"[知识库更新] LLM原始输出: {raw_output}\")\n\n# 步骤 2: 【已修正】使用更健壮的正则表达式，直接从字符串中提取有效的JSON部分\njson_string = ''\n# 这个正则表达式会寻找从第一个'{'到最后一个'}'的所有内容，能处理换行\nmatch = re.search(r'\\{.*\\}', raw_output, re.DOTALL)\nif match:\n    json_string = match.group(0)\n    print(f\"[知识库更新] 成功提取JSON: {json_string}\")\nelse:\n    print(\"[知识库更新] 警告: 在LLM输出中未找到有效的JSON对象。\")\n\n# 步骤 3: 健壮地解析JSON字符串\ntry:\n    # 即使提取失败，json_string为空，也能安全地解析为空字典\n    growth_data = json.loads(json_string or '{}')\nexcept json.JSONDecodeError as e:\n    print(f\"[知识库更新] 错误: JSON解析失败 - {e}\")\n    growth_data = {}\n\n# 步骤 4: 获取要添加的新事实列表\nfacts_to_add = growth_data.get('new_facts', [])\n\n# 步骤 5: 如果有新事实，则将其添加到Codex中\nif facts_to_add:\n    print(f'[知识库更新] 发现 {len(facts_to_add)} 个新事实准备添加...')\n    if 'knowing' not in lore.codices:\n        lore.codices['knowing'] = {'entries': []}\n    if 'entries' not in lore.codices.knowing:\n        lore.codices.knowing['entries'] = []\n\n    for fact_content in facts_to_add:\n        new_id = f'fact_{session.turn_count}_{random.randint(100, 999)}'\n        new_entry = {\n            'id': new_id,\n            'content': fact_content,\n            'priority': 80,\n            'trigger_mode': 'always_on',\n            'is_enabled': True,\n            'metadata': {\n                'source': 'dialogue_synthesis',\n                'turn': session.turn_count\n            }\n        }\n        lore.codices.knowing.entries.append(new_entry)\n\n    print(f'[知识库更新] 成功！{len(facts_to_add)} 个新事实已添加到 knowing codex。')\nelse:\n    print('[知识库更新] 无新事实需要添加。')\n"
                  }
                }
              ],
              "metadata": {}
            },
            {
              "id": "记录回复",
              "depends_on": [
                "生成回复"
              ],
              "run": [
                {
                  "runtime": "memoria.add",
                  "config": {
                    "stream": "chat_history",
                    "level": "model",
                    "content": "{{ nodes.生成回复.output }}"
                  }
                }
              ]
            }
          ]
        }
      },
        "codices": {
        "knowing": {
          "__hevno_type__": "hevno/codex",
          "entries": [],
          "description": "The evolving knowledge base of the AI."
        }
      }
    }
    DEFAULT_MOMENT = {
        "memoria": {
        "__hevno_type__": "hevno/memoria",
        "__global_sequence__": 0,
        "chat_history": {
          "config": {},
          "entries": []
        }
      }
    }
    DEFAULT_DEFINITION = {
        "name": "Default Chat Sandbox",
        "description": "A default sandbox configured for conversational chat with a persona defined by a Codex.",
        "initial_lore": DEFAULT_LORE,
        "initial_moment": DEFAULT_MOMENT
    }

    # (函数其余部分保持不变)
    if request_body.definition:
        if "initial_lore" not in request_body.definition or "initial_moment" not in request_body.definition:
            raise HTTPException(status_code=422, detail="Custom definition must contain 'initial_lore' and 'initial_moment' keys.")
        initial_lore = request_body.definition.get("initial_lore", {})
        initial_moment = request_body.definition.get("initial_moment", {})
        definition = request_body.definition
    else:
        initial_lore = DEFAULT_LORE
        initial_moment = DEFAULT_MOMENT
        # 将默认定义与用户提供的名称合并
        definition = {**DEFAULT_DEFINITION, "name": request_body.name}


    sandbox = Sandbox(
        name=request_body.name,
        definition=definition,
        lore=initial_lore
    )
    if sandbox.id in sandbox_store:
        raise HTTPException(status_code=409, detail=f"Sandbox with ID {sandbox.id} already exists.")
    
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        moment=initial_moment
    )
    await snapshot_store.save(genesis_snapshot)
    
    sandbox.head_snapshot_id = genesis_snapshot.id
    
    await sandbox_store.save(sandbox)
    
    logger.info(f"Created new sandbox '{sandbox.name}' ({sandbox.id}) and saved to disk.")
    return sandbox

# ... (文件的其余部分保持不变) ...
@router.post("/{sandbox_id}/step", response_model=StepResponse, summary="Execute a step")
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    engine: ExecutionEngineInterface = Depends(Service("execution_engine"))
):
    """
    执行一步计算。持久化逻辑已封装在 engine.step 方法内部。
    返回一个包含执行元数据和更新后沙盒的信封。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    start_time = time.monotonic()
    
    try:
        updated_sandbox = await engine.step(sandbox, user_input)
        execution_time_ms = (time.monotonic() - start_time) * 1000
        
        # 从临时属性中获取诊断日志
        diagnostics_log = getattr(updated_sandbox, '_temp_diagnostics_log', None)
        if hasattr(updated_sandbox, '_temp_diagnostics_log'):
            delattr(updated_sandbox, '_temp_diagnostics_log') # 清理临时属性

        return StepResponse(
            status="COMPLETED",
            sandbox=updated_sandbox,
            diagnostics=StepDiagnostics(
                execution_time_ms=execution_time_ms,
                detailed_log=diagnostics_log # 将日志放入响应
            )
        )
    except Exception as e:
        logger.error(f"Error during engine step for sandbox {sandbox_id}: {e}", exc_info=True)
        # 失败时，返回执行前的沙盒状态
        return JSONResponse(
            status_code=500,
            content=StepResponse(
                status="ERROR",
                sandbox=sandbox, # 返回原始沙盒
                error_message=str(e)
            ).model_dump(mode="json")
        )


@router.put("/{sandbox_id}/revert", status_code=200, summary="Revert to a snapshot")
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID = Body(..., embed=True),
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    """
    将沙盒的状态回滚到指定的历史快照。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    target_snapshot = snapshot_store.get(snapshot_id)
    # 如果缓存里没有，就从磁盘加载所有快照来确认它是否存在
    if not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        all_snapshots = await snapshot_store.find_by_sandbox(sandbox_id)
        if not any(s.id == snapshot_id for s in all_snapshots):
            raise HTTPException(status_code=404, detail="Target snapshot not found or does not belong to this sandbox.")

    sandbox.head_snapshot_id = snapshot_id
    
    await sandbox_store.save(sandbox)
    
    logger.info(f"Reverted sandbox '{sandbox.name}' ({sandbox.id}) to snapshot {snapshot_id} and saved.")
    return {"message": f"Sandbox '{sandbox.name}' successfully reverted to snapshot {snapshot_id}"}

@router.delete("/{sandbox_id}/snapshots/{snapshot_id}", status_code=204, summary="Delete a Snapshot")
async def delete_snapshot(
    sandbox_id: UUID,
    snapshot_id: UUID,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    """
    删除一个指定的历史快照。

    **注意**: 为了保证沙盒的完整性，不允许删除当前作为 `head` 的快照。
    如果需要删除 `head` 快照，请先将沙盒 `revert` 到另一个快照。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    if sandbox.head_snapshot_id == snapshot_id:
        raise HTTPException(
            status_code=409,  # 409 Conflict 是一个合适的代码
            detail="Cannot delete the head snapshot. Please revert to another snapshot first."
        )

    # 检查快照是否存在（可选，但更健壮）
    snapshot = snapshot_store.get(snapshot_id)
    if not snapshot or snapshot.sandbox_id != sandbox_id:
        # 即使找不到，也返回成功，因为最终状态是“不存在”
        return Response(status_code=204)

    await snapshot_store.delete(snapshot_id)
    
    logger.info(f"Deleted snapshot '{snapshot_id}' for sandbox '{sandbox.name}' ({sandbox.id}).")
    return Response(status_code=204)

@router.post("/{sandbox_id}/history:reset", response_model=Sandbox, summary="Reset Sandbox History")
async def reset_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    """
    通过创建一个新的“创世”快照来重置沙盒的会话历史。

    此操作会：
    1. 读取沙盒 `definition` 中的 `initial_moment`。
    2. 基于此 `initial_moment` 创建一个全新的 `StateSnapshot`。
    3. 将沙盒的 `head_snapshot_id` 指向这个新快照。
    4. 新快照没有父快照，有效开启一个全新的、干净的对话分支。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    initial_moment = sandbox.definition.get("initial_moment")
    if not isinstance(initial_moment, dict):
        raise HTTPException(
            status_code=422,
            detail="Cannot reset history: Sandbox 'definition' is missing a valid 'initial_moment' dictionary."
        )

    # 创建一个新的创世快照
    new_genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        moment=initial_moment,
        parent_snapshot_id=None # 关键：这开启了一个新分支
    )
    
    # 保存新快照
    await snapshot_store.save(new_genesis_snapshot)
    
    # 更新沙盒的头指针
    sandbox.head_snapshot_id = new_genesis_snapshot.id
    
    # 保存更新后的沙盒
    await sandbox_store.save(sandbox)
    
    logger.info(f"Reset history for sandbox '{sandbox.name}' ({sandbox.id}). New head snapshot is {new_genesis_snapshot.id}.")
    
    # 返回更新后的沙盒，让前端立即知道新状态
    return sandbox

@router.post(
    "/{sandbox_id}/apply_definition", 
    response_model=Sandbox, 
    summary="Apply Definition to State"
)
async def apply_definition_to_sandbox(
    sandbox_id: UUID,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    """
    使用沙盒 `definition` 中的 `initial_lore` 和 `initial_moment` 
    来完全重置当前的 lore 和 moment 状态。
    这是一个破坏性操作，会开启一个全新的历史分支。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    # 1. 验证并获取定义
    initial_lore = sandbox.definition.get("initial_lore")
    initial_moment = sandbox.definition.get("initial_moment")

    if not isinstance(initial_lore, dict) or not isinstance(initial_moment, dict):
        raise HTTPException(
            status_code=422,
            detail="Cannot apply definition: 'initial_lore' or 'initial_moment' is missing or not a dictionary in the definition."
        )

    # 2. 重置 Lore
    # 使用深拷贝以避免任何意外的引用问题
    sandbox.lore = copy.deepcopy(initial_lore)
    logger.info(f"Applied initial_lore to sandbox '{sandbox.name}' ({sandbox.id}).")

    # 3. 重置 Moment (通过创建一个新的创世快照)
    new_genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        moment=copy.deepcopy(initial_moment),
        parent_snapshot_id=None # 关键: 这开启了一个新的、干净的历史分支
    )
    await snapshot_store.save(new_genesis_snapshot)
    
    # 4. 更新沙盒的头指针
    sandbox.head_snapshot_id = new_genesis_snapshot.id
    
    # 5. 持久化更新后的沙盒 (包含新的 lore 和 head_snapshot_id)
    await sandbox_store.save(sandbox)
    
    logger.info(f"Reset history for sandbox '{sandbox.name}' based on definition. New head is {new_genesis_snapshot.id}.")
    
    # 6. 返回更新后的沙盒对象
    return sandbox


@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot], summary="Get history")
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return await snapshot_store.find_by_sandbox(sandbox_id)


@router.patch("/{sandbox_id}", response_model=Sandbox, summary="Update Sandbox Details")
async def update_sandbox_details(
    sandbox_id: UUID,
    request_body: UpdateSandboxRequest,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store"))
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    sandbox.name = request_body.name
    
    await sandbox_store.save(sandbox)
    
    logger.info(f"Updated name for sandbox '{sandbox.id}' to '{sandbox.name}' and saved.")
    return sandbox


@router.delete("/{sandbox_id}", status_code=204, summary="Delete a Sandbox")
async def delete_sandbox(
    sandbox_id: UUID,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
):
    """
    从文件系统和缓存中完全删除一个沙盒及其所有数据。
    """
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    await sandbox_store.delete(sandbox_id)
    
    logger.info(f"Deleted sandbox '{sandbox_id}' and all associated data from disk.")
    return Response(status_code=204)


@router.get("", response_model=List[SandboxListItem], summary="List all Sandboxes")
async def list_sandboxes(
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    # sandbox_store.values() 从缓存读取，是同步的
    all_sandboxes = sandbox_store.values()
    response_items = []
    
    for sandbox in all_sandboxes:
        icon_path = persistence_service.get_sandbox_icon_path(str(sandbox.id))
        has_custom_icon = icon_path is not None
        
        icon_url = f"/api/sandboxes/{sandbox.id}/icon"
        if sandbox.icon_updated_at:
            icon_url += f"?v={int(sandbox.icon_updated_at.timestamp())}"
        
        response_items.append(
            SandboxListItem(
                id=sandbox.id,
                name=sandbox.name,
                created_at=sandbox.created_at,
                icon_url=icon_url,
                has_custom_icon=has_custom_icon
            )
        )
        
    return sorted(response_items, key=lambda s: s.created_at, reverse=True)

# --- Icon, Export, Import 端点 ---

@router.get("/{sandbox_id}/icon", response_class=FileResponse, summary="Get Sandbox Icon")
async def get_sandbox_icon(
    sandbox_id: UUID,
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    icon_path = persistence_service.get_sandbox_icon_path(str(sandbox_id))
    if icon_path:
        return FileResponse(icon_path)
    
    default_icon_path = persistence_service.get_default_icon_path()
    if not default_icon_path.is_file():
        raise HTTPException(status_code=404, detail="Default icon not found on server.")
    return FileResponse(default_icon_path)


@router.post("/{sandbox_id}/icon", status_code=200, summary="Upload/Update Sandbox Icon")
async def upload_sandbox_icon(
    sandbox_id: UUID,
    file: UploadFile = File(...),
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service")),
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    if not file.content_type == "image/png":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PNG is allowed.")

    icon_bytes = await file.read()
    
    try:
        img = Image.open(io.BytesIO(icon_bytes))
        img.verify() 
        img = Image.open(io.BytesIO(icon_bytes))
        if img.format != 'PNG':
            raise ValueError("Image format is not PNG.")
        if max(img.size) > 2048:
            raise ValueError("Image dimensions are too large (max 2048x2048).")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid PNG file: {e}")

    # 添加 await 调用异步方法
    await persistence_service.save_sandbox_icon(str(sandbox.id), icon_bytes)
    sandbox.icon_updated_at = datetime.now(timezone.utc)
    
    await sandbox_store.save(sandbox)
    
    return {"message": "Icon updated successfully."}


@router.get(
    "/{sandbox_id}/export/json", 
    response_class=JSONResponse, 
    summary="Export a Sandbox as JSON"
)
async def export_sandbox_json(
    sandbox_id: UUID,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    # 添加 await 调用异步方法
    snapshots = await snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    archive = SandboxArchiveJSON(sandbox=sandbox, snapshots=snapshots)
    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox_id}.json"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return JSONResponse(content=archive.model_dump(mode="json"), headers=headers)


@router.post(
    "/import/json", 
    response_model=Sandbox, 
    status_code=201, 
    summary="Import a Sandbox from JSON"
)
async def import_sandbox_json(
    file: UploadFile = File(...),
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
) -> Sandbox:
    if not file.content_type == "application/json":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .json file.")

    try:
        content = await file.read()
        data = json.loads(content, object_hook=custom_json_decoder_object_hook)
        archive = SandboxArchiveJSON.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid sandbox archive format: {e}")

    old_sandbox_id = archive.sandbox.id
    new_sandbox_id = uuid.uuid4()
    snapshot_id_map = {snap.id: uuid.uuid4() for snap in archive.snapshots}
    
    for old_snapshot in archive.snapshots:
        new_snapshot = old_snapshot.model_copy(update={
            'id': snapshot_id_map[old_snapshot.id],
            'sandbox_id': new_sandbox_id,
            'parent_snapshot_id': snapshot_id_map.get(old_snapshot.parent_snapshot_id)
        })
        await snapshot_store.save(new_snapshot)
    
    new_head_id = snapshot_id_map.get(archive.sandbox.head_snapshot_id)
    new_sandbox = archive.sandbox.model_copy(update={
        'id': new_sandbox_id,
        'head_snapshot_id': new_head_id,
        'name': f"{archive.sandbox.name} (Imported)",
        'created_at': datetime.now(timezone.utc),
        'icon_updated_at': None
    })

    if new_sandbox.id in sandbox_store:
         raise HTTPException(status_code=409, detail=f"A sandbox with the newly generated ID '{new_sandbox.id}' already exists. This is highly unlikely, please try again.")
    
    await sandbox_store.save(new_sandbox)

    logger.info(f"Successfully imported sandbox from JSON, new ID is '{new_sandbox.id}'. Original ID was '{old_sandbox_id}'.")
    return new_sandbox


# PNG 导入/导出端点
@router.get("/{sandbox_id}/export", response_class=Response, summary="Export a Sandbox as PNG")
async def export_sandbox(
    sandbox_id: UUID,
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    # 添加 await 调用异步方法
    snapshots = await snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    manifest = PackageManifest(
        package_type=PackageType.SANDBOX_ARCHIVE,
        entry_point="sandbox.json",
        metadata={"sandbox_name": sandbox.name}
    )
    
    # 使用与持久化存储相同的序列化机制，确保UUID等类型被正确处理
    export_sandbox_data = sandbox.model_dump(mode='json', fallback=pickle_fallback_encoder)
    
    # 为了兼容旧版，手动添加 graph_collection (如果 lore.graphs 存在)
    if sandbox.lore and 'graphs' in sandbox.lore:
        export_sandbox_data['graph_collection'] = sandbox.lore['graphs']

    data_files: Dict[str, Any] = {"sandbox.json": export_sandbox_data}
    for snap in snapshots:
        # 对每个快照也使用相同的序列化机制
        data_files[f"snapshots/{snap.id}.json"] = snap.model_dump(mode='json', fallback=pickle_fallback_encoder)

    base_image_bytes = None
    icon_path = persistence_service.get_sandbox_icon_path(str(sandbox.id))
    if icon_path and icon_path.is_file():
        # 读取图标文件是I/O操作
        async with aiofiles.open(icon_path, 'rb') as f:
            base_image_bytes = await f.read()
    
    if not base_image_bytes:
        default_icon_path = persistence_service.get_default_icon_path()
        if default_icon_path.is_file():
             async with aiofiles.open(default_icon_path, 'rb') as f:
                base_image_bytes = await f.read()

    try:
        # 添加 await 调用异步方法
        png_bytes = await persistence_service.export_package(manifest, data_files, base_image_bytes)
    except Exception as e:
        logger.error(f"Failed to create package for sandbox {sandbox_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create package: {e}")

    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox_id}.png"
    return Response(content=png_bytes, media_type="image/png", headers={"Content-Disposition": f"attachment; filename={filename}"})

@router.post(":import", response_model=Sandbox, summary="Import a Sandbox from PNG")
async def import_sandbox(
    file: UploadFile = File(...),
    sandbox_store: SandboxStoreInterface = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
) -> Sandbox:
    if not file.filename or not file.filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .png file.")

    package_bytes = await file.read()
    
    try:
        manifest, data_files, png_bytes = await persistence_service.import_package(package_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid package: {e}")

    if manifest.package_type != PackageType.SANDBOX_ARCHIVE:
        raise HTTPException(status_code=400, detail=f"Invalid package type. Expected '{PackageType.SANDBOX_ARCHIVE.value}'.")

    try:
        sandbox_data_str = data_files.get(manifest.entry_point)
        if not sandbox_data_str:
            raise ValueError(f"Entry point file '{manifest.entry_point}' not found in package.")
        
        old_sandbox_data = json.loads(sandbox_data_str, object_hook=custom_json_decoder_object_hook)
        
        # --- [修复开始] ---
        # 1. 直接从导入的数据中获取完整的 `lore` 和 `definition`。
        imported_lore = old_sandbox_data.get('lore')
        imported_definition = old_sandbox_data.get('definition')

        # 2. 添加对旧格式的向后兼容支持。
        #    如果 `lore` 不存在，但旧的 `graph_collection` 存在，则用它来构建 lore。
        if not imported_lore and 'graph_collection' in old_sandbox_data:
            imported_lore = {"graphs": old_sandbox_data.get("graph_collection", {})}
        
        # 3. 如果 `definition` 不存在（非常旧的格式），则根据已有的 lore 和空的 moment 构建一个。
        if not imported_definition:
             imported_definition = {
                 "initial_lore": imported_lore or {},
                 "initial_moment": {}
             }

        if not imported_lore or not imported_definition:
            raise ValueError("Imported sandbox data is missing 'lore' or 'definition' fields.")
        # --- [修复结束] ---

        new_id = uuid.uuid4()
        # 使用修复后的、完整的数据来创建新的 Sandbox 对象
        new_sandbox = Sandbox(
            id=new_id,
            name=old_sandbox_data.get('name', 'Imported Sandbox'),
            definition=imported_definition, # 使用完整的 definition
            lore=imported_lore,             # 使用完整的 lore
            created_at=datetime.now(timezone.utc)
        )
        
        if new_sandbox.id in sandbox_store:
            raise HTTPException(status_code=409, detail=f"Conflict: A sandbox with the newly generated ID '{new_sandbox.id}' already exists.")

        recovered_snapshots = []
        old_to_new_snap_id = {}
        for filename in data_files:
            if filename.startswith("snapshots/"):
                old_id_str = filename.split('/')[1].split('.')[0]
                old_to_new_snap_id[UUID(old_id_str)] = uuid.uuid4()

        for filename, content_str in data_files.items():
            if filename.startswith("snapshots/"):
                old_snapshot_data = json.loads(content_str, object_hook=custom_json_decoder_object_hook)
                old_id = UUID(old_snapshot_data.get('id'))
                old_parent_id = old_snapshot_data.get('parent_snapshot_id')
                old_parent_id_uuid = UUID(old_parent_id) if old_parent_id else None
                new_parent_id = old_to_new_snap_id.get(old_parent_id_uuid) if old_parent_id_uuid else None
                
                new_snapshot = StateSnapshot(
                    id=old_to_new_snap_id[old_id],
                    sandbox_id=new_sandbox.id,
                    moment=old_snapshot_data.get('moment', {}),
                    parent_snapshot_id=new_parent_id,
                    triggering_input=old_snapshot_data.get('triggering_input', {}),
                    run_output=old_snapshot_data.get('run_output'),
                    created_at=datetime.fromisoformat(old_snapshot_data.get('created_at')) if old_snapshot_data.get('created_at') else datetime.now(timezone.utc)
                )
                recovered_snapshots.append(new_snapshot)
        
        if not recovered_snapshots:
            #如果没有快照，我们应该基于 definition 创建一个创世快照，而不是报错。
            initial_moment = new_sandbox.definition.get("initial_moment", {})
            genesis_snapshot = StateSnapshot(
                id=uuid.uuid4(),
                sandbox_id=new_sandbox.id,
                moment=initial_moment
            )
            recovered_snapshots.append(genesis_snapshot)
            # 将 head 指向这个唯一的快照
            new_sandbox.head_snapshot_id = genesis_snapshot.id


        for snapshot in recovered_snapshots:
            await snapshot_store.save(snapshot)
        
        #如果 head_snapshot_id 还没有被设置（例如上面创建了创世快照的情况），
        # 则需要从导入的数据中设置它。
        if not new_sandbox.head_snapshot_id:
            old_head_id = old_sandbox_data.get('head_snapshot_id')
            if old_head_id:
                new_sandbox.head_snapshot_id = old_to_new_snap_id.get(UUID(old_head_id))

        try:
            await persistence_service.save_sandbox_icon(str(new_sandbox.id), png_bytes)
            new_sandbox.icon_updated_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to set icon for newly imported sandbox {new_sandbox.id}: {e}")

        await sandbox_store.save(new_sandbox)
        
        logger.info(f"Successfully imported sandbox '{new_sandbox.name}' ({new_sandbox.id}) from PNG.")
        return new_sandbox
    except (ValidationError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to process package data for file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process package data: {str(e)}")