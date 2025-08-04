
# Hevno Engine - 后端 API 与开发者文档
---

## 1. 引言

欢迎来到 Hevno Engine！本档旨在为前端开发者提供与后端系统交互所需的所有信息。后端是一个基于插件化架构的、用于执行大型语言模型（LLM）流图的强大引擎。

作为前端开发者，您主要会通过以下两种方式与后端交互：
*   **REST API**: 用于管理核心资源，如创建和执行沙盒（Sandbox）、导入/导出数据等。
*   **WebSocket**: 用于实现实时、双向的通信，特别是接收来自引擎的实时事件（如状态更新）和向引擎发送指令。

本档将详细解释这些接口，并提供必要的核心概念和数据模型，以帮助您构建一个功能丰富的用户界面。

## 2. 核心概念与设计哲学

在深入 API 之前，理解引擎的设计思想至关重要。这有助于您理解 API 设计的“为什么”。

### 2.1 愿景：从“聊天机器人”到“世界模拟器”

我们的目标不是构建简单的聊天应用，而是创造一个可以模拟复杂、持久、可交互动态世界的引擎。前端界面（如图形化流图编辑器、交互式故事阅读器）是这个“世界模拟器”的窗口。

### 2.2 图执行哲学

1.  **指令式行为**: 节点的行为由一系列原子化的、有序的**指令**(`RuntimeInstruction`)定义。
2.  **状态先行**: 引擎的核心是**状态快照**(`StateSnapshot`)。每一次执行都是从一个旧快照到新快照的转换。这使得时间回溯（读档）变得极其简单。
3.  **约定优于配置**: 节点间的依赖关系大多通过宏 (`{{ nodes.A.output }}`) **自动推断**，无需手动连线。
4.  **默认并发安全**: 引擎在后台自动处理并发执行节点的竞态条件，开发者无需担心。

## 3. REST API 参考

所有 API 端点都以 `/api` 为前缀。

### 3.1 系统与插件 API (`/api/system`, `/api/plugins`)

#### **`GET /api/system/report`**
*   **摘要**: 获取完整的系统状态和元数据报告。
*   **描述**: 这是一个全面的诊断端点，返回有关已加载的 LLM 提供商、可用模型等信息。
*   **响应 (200 OK)**:
    ```json
    {
      "llm_providers": [
        {
          "name": "gemini",
          "supported_models": []
        }
      ]
    }
    ```

#### **`GET /api/plugins/manifest`**
*   **摘要**: 获取所有插件的元数据清单。
*   **描述**: 返回 `hevno.json` 中定义的所有插件的配置。这是前端动态加载和渲染插件UI（微前端架构）的**唯一事实来源**。前端应使用此清单来发现并加载插件。返回的 `entryPoint` 路径（例如 `/plugins/core-layout/dist/index.js`）是一个可直接访问的 URL，由后端的插件资源服务提供。
*   **响应 (200 OK)**:
    ```json
    [
      {
        "id": "core_logging",
        "source": "local"
      },
      {
        "id": "core-layout",
        "source": "local",
        "type": "frontend",
        "config": {
          "entryPoint": "/plugins/core-layout/dist/index.js",
          "priority": -10
        }
      },
      {
        "id": "world-state-viewer",
        "source": "local",
        "type": "frontend",
        "config": {
          "entryPoint": "/plugins/world-state-viewer/dist/index.js",
          "priority": 10,
          "contributions": {
            "views": {
              "workbench.sidebar": [{
                "id": "world-state-viewer.main",
                "component": "WorldStateViewer" 
              }]
            }
          }
        }
      }
    ]
    ```

#### **`GET /plugins/{plugin_id}/{resource_path:path}`**
*   **摘要**: 获取插件的静态资源。
*   **描述**: 此端点由 `core-persistence` 插件提供，允许后端像 Web 服务器一样为前端插件提供其静态文件（如 JS, CSS, 图片等）。它将 URL 路径动态映射到服务器上 `plugins` 目录内的实际文件，这是实现微前端架构的关键。
*   **路径参数**:
    *   `plugin_id` (string): 插件的 ID，例如 `core-layout`。
    *   `resource_path` (path): 从该插件根目录开始的资源路径，例如 `dist/index.js`。
*   **示例请求**:
    *   `GET /plugins/world-state-viewer/dist/index.js`
*   **响应 (200 OK)**:
    *   返回请求的静态文件内容，并附带正确的 `Content-Type` 头（例如 `application/javascript`）。

### 3.2 沙盒 API (`/api/sandboxes`)

沙盒 (`Sandbox`) 代表一个独立的、隔离的交互会话（例如，一局游戏，一个故事实例）。

#### **`GET /api/sandboxes`**
*   **摘要**: 获取所有已存在的沙盒列表。
*   **描述**: 返回一个包含系统中所有 `Sandbox` 对象的数组，默认按创建时间降序排列（最新的在前）。
*   **响应 (200 OK)**: 一个 `Sandbox` 对象的 JSON 数组。
    ```json
    [
      {
        "id": "a4b1c2d3-e4f5-4a6b-8c7d-9e8f7a6b5c4d",
        "name": "大臣的游戏",
        "head_snapshot_id": "f1e2d3c4-b5a6-4f7e-8d9c-0a9b8c7d6e5f",
        "created_at": "2023-10-27T12:30:00.123Z"
      },
      {
        "id": "b5c2d3e4-f5a6-4b7c-8d9e-0f9a8b7c6d5e",
        "name": "我的第一个互动小说",
        "head_snapshot_id": "f6e5d4c3-b2a1-4f7e-8d9c-0a9b8c7d6e5f",
        "created_at": "2023-10-27T10:00:00.123Z"
      }
    ]
    ```
*   **空状态**: 如果系统中没有任何沙盒，此端点将返回一个空的 JSON 数组 `[]`。


#### **`POST /api/sandboxes`**
*   **摘要**: 创建一个新的沙盒。
*   **描述**: 创建一个新的沙盒，并为其生成一个初始（创世）快照。这是与一个新世界交互的起点。
*   **请求体**: `application/json`
    ```json
    {
      "name": "我的第一个互动小说",
      "graph_collection": {
        "main": {
          "nodes": [
            {
              "id": "start",
              "run": [{
                "runtime": "llm.default",
                "config": {
                  "model": "gemini/gemini-1.5-flash",
                  "prompt": "你好，世界！"
                }
              }]
            }
          ]
        }
      },
      "initial_state": {
        "player_name": "爱丽丝",
        "inventory": []
      }
    }
    ```
*   **响应 (201 Created)**: 返回创建的 [Sandbox](#51-sandbox) 对象。
    ```json
    {
      "id": "a1b2c3d4-e5f6-4a6b-8c7d-9e8f7a6b5c4d",
      "name": "我的第一个互动小说",
      "head_snapshot_id": "f6e5d4c3-b2a1-4f7e-8d9c-0a9b8c7d6e5f",
      "created_at": "2023-10-27T10:00:00.123Z"
    }
    ```
*   **错误**: `409 Conflict` (如果沙盒ID已存在)。


#### **`POST /api/sandboxes/{sandbox_id}/step`**
*   **摘要**: 在沙盒的最新状态上执行一步计算。
*   **描述**: 驱动世界演化的核心端点。它接收用户输入，在当前 `head_snapshot_id` 指向的快照上执行图，并生成一个新的快照。
*   **路径参数**: `sandbox_id` (UUID) - 目标沙盒的ID。
*   **请求体**: `application/json` (用户输入，将注入到宏的 `run.trigger_input` 上下文中)。
    ```json
    {
      "user_message": "我选择左边的门",
      "damage_amount": 10
    }
    ```
*   **响应 (200 OK)**: 返回新生成的 [StateSnapshot](#52-statesnapshot) 对象。
*   **错误**:
    *   `404 Not Found`: 沙盒未找到。
    *   `409 Conflict`: 沙盒没有初始状态。
    *   `500 Internal Server Error`: 引擎执行出错或数据不一致。

#### **`GET /api/sandboxes/{sandbox_id}/history`**
*   **摘要**: 获取一个沙盒的所有历史快照。
*   **描述**: 返回一个沙盒从创世到当前状态的所有快照列表，按创建时间升序排列。
*   **路径参数**: `sandbox_id` (UUID)
*   **响应 (200 OK)**: [StateSnapshot](#52-statesnapshot) 对象数组。
    ```json
    [
      { "id": "snap_1_genesis", "created_at": "...", "world_state": {...} },
      { "id": "snap_2_turn_1", "created_at": "...", "world_state": {...} },
      { "id": "snap_3_turn_2", "created_at": "...", "world_state": {...} }
    ]
    ```
*   **错误**: `404 Not Found`

#### **`PUT /api/sandboxes/{sandbox_id}/revert`**
*   **摘要**: 将沙盒的状态回滚到指定的历史快照。
*   **描述**: 这是一个非常强大的“读档”功能。它将沙盒的 `head_snapshot_id` 指针直接移动到目标快照ID，不会删除任何历史记录。
*   **路径参数**: `sandbox_id` (UUID)
*   **查询参数**: `snapshot_id` (UUID) - 要回滚到的目标快照ID。
*   **响应 (200 OK)**:
    ```json
    {
      "message": "Sandbox '...' successfully reverted to snapshot ..."
    }
    ```
*   **错误**: `404 Not Found` (沙盒或快照未找到)。

#### **`GET /api/sandboxes/{sandbox_id}/export`**
*   **摘要**: 导出沙盒。
*   **描述**: 将一个沙盒及其完整历史打包成一个 `.hevno.zip` 文件供下载。
*   **路径参数**: `sandbox_id` (UUID)
*   **响应 (200 OK)**: 一个 `application/zip` 文件流。

#### **`POST /api/sandboxes/import`**
*   **摘要**: 导入沙盒。
*   **描述**: 从一个 `.hevno.zip` 文件恢复一个沙盒及其完整历史。
*   **请求体**: `multipart/form-data`，包含一个名为 `file` 的文件字段。
*   **响应 (200 OK)**: 返回新导入的 [Sandbox](#51-sandbox) 对象。
*   **错误**:
    *   `400 Bad Request`: 文件类型错误或包内容无效。
    *   `409 Conflict`: 导入的沙盒ID已存在。
    *   `422 Unprocessable Entity`: 包数据无法被正确解析。

### 3.3 持久化 API (`/api/persistence`)

此 API 由 `core-persistence` 插件提供，是 Hevno 引擎的文件系统核心。它负责管理后端存储的逻辑资产（如图、Codex），并为其他插件（如 `core-api`）提供底层的数据打包服务。

#### **`GET /api/persistence/assets/{asset_type}`**
*   **摘要**: 列出指定类型的所有已保存资产。
*   **描述**: 用于管理保存在后端文件系统中的核心逻辑资产。前端可以通过此接口获取服务器上已存储的、可供后端在创建沙盒或执行图时引用的资源列表。
*   **路径参数**:
    *   `asset_type` (Enum): 资产类型。目前支持的值为:
        *   `"graph"`: 列出所有已保存的图定义文件。
        *   `"codex"`: 列出所有已保存的知识库文件。
*   **响应 (200 OK)**: 一个包含所有已保存资产名称的 JSON 数组（不含文件扩展名）。
    ```json
    [
      "main_story_flow",
      "character_dialogue_logic"
    ]
    ```

#### **数据包导入/导出服务 (底层能力)**

`core-persistence` 插件还提供了将数据打包成 `.hevno.zip` 文件格式的核心服务能力。

*   **用途**: 为其他插件提供沙盒导入/导出等功能所需的底层打包和解包逻辑。
*   **工作方式**: 此功能本身**不直接提供**通用的导入/导出 API 端点。相反，其他插件（如 `core-api`）的服务会调用 `persistence_service` 来创建或解析 `.hevno.zip` 文件。具体的 API，例如 `/api/sandboxes/import` 和 `/api/sandboxes/export`，是由使用此服务的插件来定义和暴露的。

## 4. WebSocket API 参考 (`/ws/hooks`)

WebSocket 是实现前端与后端实时交互的关键。它本质上是一个双向的**钩子系统总线**。

### 4.1 连接

*   **URL**: `ws://<your_server_address>/ws/hooks`

客户端应在应用启动时建立一个持久的 WebSocket 连接。

### 4.2 客户端到服务端消息

前端可以向后端发送消息，以**触发后端的钩子**。这允许前端在不使用 REST API 的情况下，向后端系统广播事件。

*   **格式**: JSON 字符串
*   **结构**:
    ```json
    {
      "hook_name": "string",
      "data": { "key": "value" }
    }
    ```
*   `hook_name` (必需): 要在后端触发的钩子的名称。
*   `data` (可选): 一个包含任意数据的对象，将作为关键字参数传递给后端的钩子实现函数。

*   **示例**: 前端通知后端用户解锁了一个成就。
    ```json
    {
      "hook_name": "achievement.unlocked",
      "data": {
        "achievement_id": "first_step",
        "player_id": "user123"
      }
    }
    ```

### 4.3 服务端到客户端消息

后端会在关键事件发生时，向所有连接的客户端**广播**消息。前端通过监听这些消息来响应状态变化。

*   **格式**: JSON 字符串
*   **结构**: 与客户端到服务端消息相同。
    ```json
    {
      "hook_name": "string",
      "data": { "key": "value" }
    }
    ```
*   `hook_name`: 发生的事件名称。
*   `data`: 与事件相关的数据。

#### **核心监听事件**

*   **`snapshot_committed`**: **【最重要】** 当一次 `step` 执行完成并成功创建一个新的状态快照后，此事件被触发。这是前端更新UI（如世界状态、角色属性等）的主要信号。
    *   **示例载荷**:
        ```json
        {
          "hook_name": "snapshot_committed",
          "data": {
            "snapshot": {
              // 完整的 StateSnapshot 对象
              "id": "...",
              "sandbox_id": "...",
              "world_state": { "player_hp": 90, "location": "黑暗森林" },
              // ... 其他快照字段 ...
            }
          }
        }
        ```

*   **其他事件**: 插件系统允许任何后端事件被转发。例如，一个成就系统可能会转发 `achievement.unlocked` 事件，即使它是由另一个客户端触发的。前端应根据需要处理已知的钩子，并安全地忽略未知的钩子。

## 5. 核心数据模型参考

这些是您在 API 响应和 WebSocket 消息中会遇到的核心 JSON 对象结构。

### 5.1 `Sandbox`

代表一个独立的交互会话。

| 字段名             | 类型     | 描述                                     |
| ------------------ | -------- | ---------------------------------------- |
| `id`               | UUID     | 沙盒的唯一标识符。                       |
| `name`             | string   | 人类可读的名称。                         |
| `head_snapshot_id` | UUID     | 指向当前最新状态快照的ID。               |
| `created_at`       | DateTime | 创建时间的ISO 8601字符串。               |

**示例 JSON**:
```json
{
  "id": "a4b1c2d3-e4f5-4a6b-8c7d-9e8f7a6b5c4d",
  "name": "大臣的游戏",
  "head_snapshot_id": "f1e2d3c4-b5a6-4f7e-8d9c-0a9b8c7d6e5f",
  "created_at": "2023-10-27T12:30:00.123Z"
}
```

### 5.2 `StateSnapshot`

代表世界在某个特定时刻的完整状态。**此对象是不可变的**。

| 字段名               | 类型               | 描述                                                     |
| -------------------- | ------------------ | -------------------------------------------------------- |
| `id`                 | UUID               | 快照的唯一标识符。                                       |
| `sandbox_id`         | UUID               | 所属沙盒的ID。                                           |
| `graph_collection`   | GraphCollection    | 该快照生效时，驱动逻辑的图定义。                         |
| `world_state`        | object             | 核心的持久化世界状态，包含所有变量（如玩家属性、环境等）。 |
| `created_at`         | DateTime           | 创建时间的ISO 8601字符串。                               |
| `parent_snapshot_id` | UUID \| null       | 指向上一个快照的ID，形成历史链。创世快照为 `null`。       |
| `triggering_input`   | object             | 触发本次快照生成的输入。                                 |
| `run_output`         | object \| null     | 图执行完成后，所有节点的最终输出。                       |

**示例 JSON**:
```json
{
  "id": "f1e2d3c4-b5a6-4f7e-8d9c-0a9b8c7d6e5f",
  "sandbox_id": "a4b1c2d3-e4f5-4a6b-8c7d-9e8f7a6b5c4d",
  "graph_collection": { "main": { "nodes": [/*... */] } },
  "world_state": {
    "character_mood": "happy",
    "player_hp": 100
  },
  "created_at": "2023-10-27T12:35:10.456Z",
  "parent_snapshot_id": "e0d1c2b3-a4b5-4e6d-7c8b-9a8b7c6d5e4f",
  "triggering_input": { "user_choice": "option_a" },
  "run_output": {
    "node_A": { "output": "一些结果" },
    "node_B": { "llm_output": "LLM的回答" }
  }
}
```

### 5.3 `GraphCollection` 与 `GraphDefinition`

`GraphCollection` 是一个包含多个图定义的对象。入口图的键名必须是 `main`。

| `GraphDefinition` 字段 | 类型              | 描述                     |
| ---------------------- | ----------------- | ------------------------ |
| `nodes`                | `GenericNode[]`   | 组成该图的节点数组。     |
| `metadata`             | object            | 任意元数据。             |

**示例 JSON**:
```json
{
  "main": {
    "nodes": [ /* ... GenericNode 数组 ... */ ],
    "metadata": { "description": "主故事线" }
  },
  "sub_process": {
    "nodes": [ /* ... */ ]
  }
}
```

### 5.4 `GenericNode` 与 `RuntimeInstruction`

`GenericNode` 是图的基本执行单元。`RuntimeInstruction` 是定义节点行为的原子指令。

**`GenericNode` 结构**:

| 字段名       | 类型                     | 描述                                     |
| ------------ | ------------------------ | ---------------------------------------- |
| `id`         | string                   | 节点在图内的唯一ID。                     |
| `run`        | `RuntimeInstruction[]`   | 定义节点行为的有序指令列表。             |
| `depends_on` | `string[]` \| null       | 明确声明的依赖节点ID列表。               |
| `metadata`   | object                   | 任意元数据，如在编辑器中的位置。         |

**`RuntimeInstruction` 结构**:

| 字段名    | 类型   | 描述                                     |
| --------- | ------ | ---------------------------------------- |
| `runtime` | string | 要执行的运行时名称 (e.g., `"llm.default"`)。 |
| `config`  | object | 传递给该运行时的隔离配置。               |

**示例 JSON (一个节点)**:
```json
{
  "id": "greet_player",
  "run": [
    {
      "runtime": "system.io.log",
      "config": {
        "message": "即将问候玩家 {{world.player_name}}"
      }
    },
    {
      "runtime": "llm.default",
      "config": {
        "model": "gemini/gemini-1.5-flash",
        "prompt": "生成一句对 {{world.player_name}} 的问候。"
      }
    }
  ],
  "depends_on": ["initialize_player_state"]
}
```

### 5.5 `Memoria` 记忆系统模型

记忆系统保存在 `world_state.memoria` 中。

**`MemoryStream` 结构**:

| 字段名 | 类型 | 描述 |
| --- | --- | --- |
| `config` | object | 该流的配置，如自动总结设置。 |
| `entries` | `MemoryEntry[]` | 按时间顺序排列的记忆条目。 |
| `synthesis_trigger_counter` | int | 内部计数器，用于触发自动总结。 |

**`MemoryEntry` 结构**:

| 字段名 | 类型 | 描述 |
| --- | --- | --- |
| `id` | UUID | 记忆条目的唯一ID。 |
| `sequence_id` | int | 全局唯一的、严格递增的因果序列号。 |
| `level` | string | 层级, e.g., `"event"`, `"milestone"`, `"thought"`. |
| `tags` | `string[]` | 用于检索的标签。 |
| `content` | string | 记忆的文本内容。 |
| `created_at` | DateTime | 创建时间。 |

**示例 JSON (`world.memoria`)**:
```json
{
  "memoria": {
    "__global_sequence__": 2,
    "main_story": {
      "config": { /* ... */ },
      "entries": [
        {
          "id": "...",
          "sequence_id": 1,
          "level": "event",
          "tags": ["exploration", "village"],
          "content": "玩家抵达了宁静的溪谷村。",
          "created_at": "..."
        },
        {
          "id": "...",
          "sequence_id": 2,
          "level": "dialogue",
          "tags": ["npc_interaction", "mayor"],
          "content": "村长请求玩家帮助寻找失踪的猫。",
          "created_at": "..."
        }
      ],
      "synthesis_trigger_counter": 2
    }
  }
}
```

## 6. 图与宏系统参考

### 6.1 图定义格式

请参考 [5.3](#53-graphcollection-与-graphdefinition) 和 [5.4](#54-genericnode-与-runtimeinstruction) 章节。关键点是：
*   整个文件是一个 `GraphCollection`。
*   必须有一个名为 `main` 的图。
*   节点行为由 `run` 数组中的指令序列定义。

### 6.2 宏系统 (`{{...}}`)

宏是 Hevno 引擎的超能力，它允许在 JSON 配置中嵌入可执行的 Python 代码。

*   **语法**: 任何被 `{{ ... }}` 包裹的内容都会被视为 Python 代码并执行。
*   **求值时机**: 在每个指令执行**之前**，该指令的 `config` 会被求值。
*   **上下文**: 在宏内部，您可以访问以下全局对象：
    *   `world`: 持久化的世界状态 (`world_state` 的代理)。**可以读写**。
        *   `{{ world.player.hp }}`
        *   `{{ world.tasks.append('new task') }}`
    *   `nodes`: 已完成节点的结果。
        *   `{{ nodes.node_A.output.upper() }}`
    *   `pipe`: **节点内**上一个指令的输出。
        *   `{{ f'上一步的结果是: {pipe.output}' }}`
    *   `run`: 本次图执行的临时数据。
        *   `{{ run.trigger_input.user_message }}`
    *   `services`: **懒加载**地访问后端服务。
        *   `{{ services.llm_service.request(model='...', prompt='...') }}`
    *   `session`: 会话元信息。
    *   **内置模块**: `random`, `math`, `datetime`, `json`, `re` 可直接使用。

### 6.3 `system` 运行时参考

以下是 `core-engine` 提供的、可用于图定义的内置运行时。

| 运行时名称            | 摘要                             | 核心配置                 | 输出 (`pipe`中)                       |
| ----------------------- | -------------------------------- | -------------------------- | ----------------------------------------- |
| `system.io.input`     | 注入一个值到管道中。             | `value: any`               | `{"output": <value的结果>}`              |
| `system.io.log`       | 向后端打印一条日志。             | `message: string`, `level: string` | `{}` (无输出)                           |
| `system.data.format`  | 将列表/字典格式化为字符串。      | `items: list|dict`, `template: string`, `joiner: string` | `{"output": <格式化后的字符串>}`        |
| `system.data.parse`   | 解析字符串为 JSON/XML。          | `text: string`, `format: "json"|"xml"` | `{"output": <解析后的对象>}`            |
| `system.data.regex`   | 执行正则表达式并提取。           | `text: string`, `pattern: string`, `mode: "search"|"find_all"` | `{"output": <匹配结果>}`                  |
| `system.flow.call`    | 调用一个子图。                   | `graph: string`, `using: dict` | `{"output": <子图的最终结果>}`           |
| `system.flow.map`     | 并行迭代列表并执行子图。         | `list: list`, `graph: string`, `using: dict`, `collect: any` | `{"output": <所有子图运行结果的列表>}` |
| `system.execute`      | **二次求值**一个宏字符串。       | `code: string`             | `{"output": <代码执行结果>}`            |

---