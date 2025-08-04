
# Hevno Engine

**一个为构建复杂、持久、可交互的 AI 世界而生的状态图执行引擎。**

---

## 1. 我们的愿景与核心设计哲学

### 1.1 我们的愿景：从“聊天机器人”到“世界模拟器”

当前的语言模型（LLM）应用，大多停留在“一问一答”的聊天机器人模式，这极大地限制了 LLM 的潜能。我们相信，LLM 的未来在于构建**复杂、持久、可交互的动态世界**。

想象一下：

*   一个能与你玩《是，大臣》策略游戏的 AI，其中每个角色（哈克、汉弗莱、伯纳）都是一个独立的、有自己动机和知识库的 LLM 实例。
*   一个能让你沉浸式体验的互动小说，你的每一个决定都会被记录，并动态地解锁、修改甚至创造新的故事线和世界规则。

这些不再是简单的“提示工程”，而是**状态管理**、**并发控制**和**动态逻辑编排**的复杂工程问题。

**Hevno Engine 的诞生，正是为了解决这个问题。** 它的核心使命是提供一个强大的后端框架，让开发者能够轻松地将离散的 LLM 调用，编织成有记忆、能演化、可回溯的智能代理和交互式世界。我们不是在构建另一个聊天应用，我们是在构建一个**创造世界的引擎**。

### 1.2 核心设计哲学：您如何构建世界

这四条哲学是您作为“世界创造者”与 Hevno 引擎交互的基础。它们定义了您如何通过图（Graph）来描述和构建动态世界的行为逻辑。

> **注意**: 这些哲学描述的是由 `core_engine` 插件实现的**图执行模型**，与后端代码的组织方式（插件架构）是两个不同但互补的概念。

#### 1.2.1 哲学一：以运行时为中心，指令式地构建行为

> **"Behavior is a sequence of instructions."**

我们摒弃了将所有配置混杂在一起的模式，转而采用一种更清晰、更强大的**指令式**设计。在 Hevno 中：

*   **极简的节点 (`GenericNode`)**: 节点本身只是一个容器。
*   **行为由指令驱动**: 节点的具体行为由其 `run` 字段中一个**有序的指令列表**所定义。
*   **原子指令 (`RuntimeInstruction`)**: 每个指令都包含一个 `runtime`（一个可执行的功能单元）和它自己独立的 `config`（配置）。这确保了逻辑的清晰和数据的隔离。
*   **强大的节点内管道**: 引擎会严格按照指令列表的顺序执行。后一个指令的宏，可以访问到前一个指令执行后产生的最新状态。

**Hevno 的指令式设计:**
```json
// 一个先通过宏设置世界状态，再调用 LLM 的复杂节点
{
    "id": "advanced_llm",
    "run": [
    {
        "runtime": "system.execute",
        "config": {
        "code": "{{ world.character_mood = 'happy' }}"
        }
    },
    {
        "runtime": "llm.default",
        "config": {
        "prompt": "{{ f'根据角色愉悦的心情 ({world.character_mood})，生成一句问候。' }}"
        }
    }
    ]
}
```
这种设计将节点的行为分解为一系列原子的、可预测的步骤，提供了无与伦比的控制力和可读性。

#### 1.2.2 哲学二：状态先行，计算短暂

> **"State is permanent, execution is ephemeral."**

一个交互式模拟世界的核心恰恰是“状态”。我们构建了一个以状态为核心的架构：

*   **沙盒 (`Sandbox`)**: 代表一个完整的、隔离的交互环境（例如，一局游戏、一个项目）。
*   **不可变快照 (`StateSnapshot`)**: 我们不直接修改状态。每一次交互（如图执行）都会产生一个全新的、完整的状态快照。这包含了当时所有的持久化变量 (`world_state`) 和驱动逻辑的图 (`graph_collection`)。
*   **引擎的角色**: `ExecutionEngine` 本身是无状态的。它的工作是接收一个旧的 `StateSnapshot`，执行计算，然后生成一个新的 `StateSnapshot`。它是一个纯粹的**状态转换函数**。

**执行流程示意：**
```
+---------------------------------------+
|          (Old StateSnapshot)          |
|  - world_state                        |
|  - graph_collection                   |
+---------------------------------------+
                   |
                   |
                   v
+---------------------------------------+
|           Execution Engine            |
|          (State Transition)           |
|              run_graph()              |
+---------------------------------------+
                   |
                   |
                   v
+---------------------------------------+
|          (New StateSnapshot)          |
|  - world_state (updated)              |
|  - graph_collection (possibly evolved)|
+---------------------------------------+
```

这种架构天然地带来了巨大的好处：
1.  **完美的回溯能力**: “读档”操作变成了简单地将沙盒的指针指向一个历史快照。
2.  **健壮的并发与调试**: 不可变性消除了大量的并发问题，并使得追踪状态变化变得异常简单。
3.  **动态的逻辑演化**: 因为图的定义本身也是状态的一部分，所以图可以被它自己执行的逻辑所修改（例如，一个指令可以更新 `world_state` 中存储的图定义），实现世界的“自我进化”。

#### 1.2.3 哲学三：约定与配置相结合，智能推断与明确声明并存

> **"Be smart, but provide an escape hatch."**

我们力求为图的创建者提供最流畅的体验，在大多数情况下，你无需关心节点间的连接。但我们也承认，在复杂场景下，明确性优于魔法。

*   **智能的依赖推断 (约定)**: 在我们的图定义中，你通常找不到 `edges` 字段。当一个节点的指令在其 `config` 中通过宏 `{{ nodes.A.output }}` 引用了另一个节点 `A` 时，引擎会自动建立一条从 `A` 到当前节点的执行依赖。这是我们的主要约定，能处理 90% 的场景。

*   **明确的依赖声明 (配置)**: 对于那些无法通过宏自动推断的**隐式依赖**（例如，一个节点通过副作用修改了 `world` 状态，而另一个节点依赖这个状态），我们提供了一个明确的 `depends_on` 字段。这让你可以在需要时精确控制执行顺序，消除竞态条件。

**依赖推断示例:**
```json
// 节点 B 自动依赖节点 A，因为它的宏引用了 nodes.A
{
  "id": "B",
  "run": [{
    "runtime": "llm.default",
    "config": { "prompt": "{{ f'基于A的结果: {nodes.A.output}' }}" }
  }]
}
```

**明确声明依赖示例:**
```json
// B 节点读取由 A 节点设置的世界变量，这是一种隐式依赖。
// 我们使用 depends_on 来确保 A 在 B 之前执行。
{
    "id": "A_set_state",
    "run": [{ "runtime": "system.execute", "config": { "code": "{{ world.theme = 'fantasy' }}" }}]
},
{
    "id": "B_read_state",
    "depends_on": ["A_set_state"],
    "run": [{
    "runtime": "llm.default",
    "config": { "prompt": "{{ f'生成一个关于 {world.theme} 世界的故事。' }}" }
    }]
}
```
这种“约定为主，配置为辅”的设计，将开发者的精力从繁琐的工程细节中解放出来，同时在关键时刻给予他们完全的控制权。

#### 1.2.4 哲学四：默认安全，并发无忧 (Safe by Default, Concurrently Sound)

> **"Write natural code, get parallel safety for free."**

在 Hevno 中，图的节点可以并行执行，这极大地提升了效率。但并发也带来了风险：如果两个并行节点同时修改同一个世界状态（如 `world.counter`），就会产生不可预测的结果（竞态条件）。

我们坚信，开发者不应该为了利用并发而成为并发控制专家。因此，Hevno Engine 内置了**宏级原子锁**机制：

*   **默认开启，完全透明**: 您无需编写任何特殊代码。引擎会自动确保每一个宏脚本的执行都是一个**原子操作**。
*   **无竞态条件之忧**: 当您在宏中编写 `world.counter += 1` 时，即使有十个节点同时执行这段代码，引擎也能保证其过程不会被打断，最终结果绝对正确。
*   **专注业务逻辑**: 您可以像在单线程环境中一样自然地编写代码，将全部精力投入到构建世界逻辑中，而引擎在幕后处理了所有复杂的并发安全问题。

**并发写入示例:**
```json
// 节点 A 和 B 会被并行执行
// 但由于宏级原子锁，对 world.gold 的修改是安全的
{
  "id": "A_earn_gold",
  "run": [{ "runtime": "system.execute", "config": { "code": "world.gold += 10" } }]
},
{
  "id": "B_spend_gold",
  "run": [{ "runtime": "system.execute", "config": { "code": "world.gold -= 5" } }]
}
```
这种设计让您能够无缝地从简单的线性逻辑扩展到复杂的高性能并行图，而无需修改一行状态操作代码。

---

## 2. 软件架构：一个可插拔的插件化系统

Hevno 的后端架构遵循“微内核 + 插件”的设计模式，其灵感来自于 VS Code 或 OBS 等高度可扩展的软件。这种设计旨在实现最大限度的**模块化**、**解耦**和**可扩展性**。

### 2.1 宏大构想：从单体应用到微内核平台

旧的架构是一个紧耦合的单体，`container.py` 和 `app.py` 知道所有服务的创建细节。新的架构则完全不同：

*   **平台内核 (`backend/`)**: `backend` 目录被精简为一个与业务无关的“微内核”。它不包含任何具体的业务逻辑（如图执行、LLM 调用），只提供所有插件赖以生存的基础设施。
*   **插件 (`plugins/`)**: 所有的核心功能，如执行引擎、API 接口、LLM 网关、持久化服务等，都被重构成独立的、可互换的插件包。每个插件都是一个自包含的功能单元。

您可以将 Hevno 平台想象成一个**操作系统**：
*   **内核 (`backend/`)** 提供了进程管理（`Container`）和系统调用（`HookManager`）等底层能力。
*   **驱动和程序 (`plugins/`)** 是在操作系统上运行的独立软件，它们遵循操作系统的规则（`Contracts`），共同构建出完整的用户体验。

### 2.2 架构的三大支柱

插件化系统建立在三个核心概念之上，它们共同构成了插件之间协作的基石。

#### 支柱一：共享契约 (`backend/core/contracts.py`) - 通用语言

这是整个系统中最关键的文件，是所有插件必须遵守的“法律”和“API 规范”。它定义了：

1.  **核心数据模型**: 如 `StateSnapshot`, `Sandbox`, `GenericNode` 等。确保了所有插件对“状态”和“图”有统一的理解。
2.  **核心服务接口**: 如 `ExecutionEngineInterface`, `SnapshotStoreInterface`。插件不应依赖于其他插件的具体实现类，而应依赖这些抽象接口。这使得任何插件（例如一个第三方的持久化插件）都可以替代核心插件，只要它实现了相同的接口。
3.  **系统事件模型**: 为所有通过钩子系统传递的事件定义了标准的 Pydantic 模型，如 `NodeExecutionStartContext`。

> **黄金法则**: 一个插件只能导入 `backend.core.contracts` 和它自身包内的模块。它**永远不应**直接从另一个插件（如 `from plugins.core_engine.engine import ExecutionEngine`）导入具体实现。

#### 支柱二：依赖注入容器 (`backend/container.py`) - 服务总管

容器是一个通用的服务定位器，它解耦了“服务的使用”和“服务的创建”。

*   **工作模式**:
    1.  **注册 (Registration)**: 在启动时，每个插件的 `register_plugin` 函数会向容器注册一个或多个**工厂函数**。这个工厂函数知道如何创建该插件提供的服务。
    2.  **解析 (Resolution)**: 当系统中任何部分（另一个服务或一个 API 端点）需要一个服务时，它不会自己去 `new` 一个实例，而是向容器请求 `container.resolve("service_name")`。容器会查找对应的工厂，创建实例（如果是第一次请求且是单例），并返回它。

*   **带来的好处**:
    *   **解耦**: `core_engine` 插件不需要知道 `LLMService` 是如何被创建的，它只需要知道去容器里找一个名为 `"llm_service"` 的服务即可。
    *   **可配置性**: 我们可以轻松地替换实现。例如，在测试环境中，可以注册一个 `MockLLMService` 工厂来代替真实的 `LLMService` 工厂，而使用服务的代码无需任何改动。
    *   **懒加载**: 服务只在第一次被请求时才会被创建，避免了不必要的启动开销。

**示例：`LLMService` 的生命周期**
```python
# 1. 在 core_llm/__init__.py 中，插件注册了一个工厂
def _create_llm_service(container: Container):
    # ...复杂的服务创建逻辑，可能依赖其他服务...
    return LLMService(...)

def register_plugin(container: Container, hook_manager: HookManager):
    container.register("llm_service", _create_llm_service)
```
```python
# 2. 在 core_engine/evaluation.py 中，宏上下文被构建
#    注意 'services' 是一个特殊的代理对象
services = DotAccessibleDict(ServiceResolverProxy(container))
```
```python
# 3. 在图的宏中，用户懒加载并使用服务
#    这是第一次访问 services.llm_service，
#    它会触发 ServiceResolverProxy -> container.resolve("llm_service")
#    -> _create_llm_service()，最终返回实例。
"{{ services.llm_service.request(...) }}"
```

#### 支柱三：钩子系统 (`backend/core/hooks.py`) - 协作总线

如果说 DI 容器解决了“谁来创建服务”的问题，那么钩子系统就解决了“插件如何安全地对话和扩展彼此”的问题。它是一个发布-订阅（Pub/Sub）事件总线。

*   **工作模式**:
    1.  **触发 (Trigger)**: 一个插件（发布者）在某个关键执行点，会通过 `hook_manager` 触发一个命名的事件（钩子），并传递相关数据。例如，`core_engine` 在需要所有运行时的时候，会触发 `"collect_runtimes"` 钩子。
    2.  **实现 (Implementation)**: 其他插件（订阅者）可以向 `hook_manager` 注册一个异步函数，以响应该钩子。
    3.  **执行 (Execution)**: `hook_manager` 负责调用所有已注册的实现函数，并根据钩子类型（如 `filter`）聚合它们的返回值。

*   **钩子类型**:
    *   **通知 (`trigger`)**: “我刚刚做完了这件事，通知大家一下。” 所有实现并发执行，返回值被忽略。
    *   **过滤 (`filter`)**: “我有一份数据，谁想在上面添加或修改一些东西？” 所有实现按优先级顺序链式执行，后一个实现会接收前一个修改过的数据。非常适合用于收集信息。

**示例：`core_engine` 如何从所有插件收集运行时和 API 路由**
```python
# 在 core_engine/__init__.py 中...
async def populate_runtime_registry(container: Container):
    # 引擎广播：“我需要运行时，请把你们的运行时给我。”
    all_runtimes = await hook_manager.filter("collect_runtimes", {})
    # ...然后注册收集到的所有运行时...

# 在 app.py 中...
async def lifespan(app: FastAPI):
    # 应用启动时广播：“我需要 API 路由，请把你们的路由给我。”
    all_routers = await hook_manager.filter("collect_api_routers", [])
    for router in all_routers:
        app.include_router(router)
```
```python
# 在 core_llm/__init__.py 中...
async def provide_runtime(runtimes: dict) -> dict:
    runtimes["llm.default"] = LLMRuntime # LLM 插件响应
    return runtimes

# 在 core_api/__init__.py 中...
async def provide_own_routers(routers: list) -> list:
    routers.append(sandbox_router) # API 插件响应
    return routers

# 注册钩子实现
def register_plugin(container: Container, hook_manager: HookManager):
    hook_manager.add_implementation("collect_runtimes", provide_runtime)
    hook_manager.add_implementation("collect_api_routers", provide_own_routers)
```
通过这种方式，`core_engine` 和 `app.py` 根本不需要知道 `core_llm` 或 `core_api` 插件的存在，但依然能获取它们提供的功能，实现了彻底的解耦。

### 2.3 插件剖析：如何构建一个插件

每个位于 `plugins/` 目录下的子目录都是一个独立的插件。一个标准插件的结构如下：

```
plugins/
└── my_awesome_plugin/
    ├── __init__.py         # 插件的入口和注册点
    ├── manifest.json       # 插件的元数据
    ├── service.py          # 插件提供的核心服务
    ├── router.py           # 插件提供的 API 路由
    └── models.py           # 插件特有的数据模型
```

*   **`manifest.json`**: 定义了插件的元数据，如名称、版本、描述，以及最重要的**加载优先级 (`priority`)**。优先级越低的插件越先被加载。
*   **`__init__.py`**: 这是插件的入口文件，必须包含一个名为 `register_plugin(container: Container, hook_manager: HookManager)` 的函数。平台加载器会调用此函数，将内核服务注入进来，插件在此函数内完成所有服务和钩子的注册。

### 2.4 应用启动生命周期

整个应用的启动过程被清晰地定义在 `app.py` 的 `lifespan` 函数中，它展示了上述机制如何协同工作：

1.  **内核初始化**: 创建 `Container` 和 `HookManager` 实例。
2.  **同步注册阶段**: `PluginLoader` 被调用。它会：
    a. 扫描 `plugins` 目录并根据 `manifest.json` 的 `priority` 排序。
    b. 按顺序调用每个插件的 `register_plugin` 函数。在此阶段，插件只向容器注册**服务工厂**，和向钩子管理器注册**钩子实现**。服务实例**尚未被创建**。
3.  **异步初始化阶段**: `lifespan` 触发 `"services_post_register"` 钩子。
    *   监听此钩子的插件（如 `core_engine` 和 `core_api`）现在可以安全地从容器中解析依赖，并执行需要 `async` 的初始化任务，例如从其他插件收集并填充自己的注册表（如 `RuntimeRegistry`）。
4.  **API 路由收集**: `lifespan` 触发 `"collect_api_routers"` 钩子，收集所有插件提供的 FastAPI `APIRouter` 实例，并挂载到主 `app` 上。
5.  **启动完成**: 触发 `"app_startup_complete"` 钩子，应用正式就绪，开始接受请求。


## 3. 图与宏系统定义

本章节将深入探讨您作为“世界创造者”与 Hevno 引擎交互的核心——**图定义**。这部分内容主要由 `core_engine` 插件实现，但其使用方式对所有插件都是通用的。

### 3.1 图定义格式与核心概念

#### 3.1.1 顶层结构：图集合 (Graph Collection)

一个完整的工作流定义是一个 JSON 对象，其 `key` 为图的名称，`value` 为图的定义。

*   **约定入口图的名称必须为 `"main"`**。
*   这允许多个可复用的图存在于同一个配置文件中。

**示例:**
```json
{
  "main": {
    "nodes": [ /* ... 主图的节点 ... */ ]
  },
  "process_character_arc": {
    "nodes": [ /* ... 一个可复用子图的节点 ... */ ]
  }
}
```

#### 3.1.2 节点 (Node) 与指令 (Instruction)

节点是图的基本执行单元，其行为由一个或多个有序的指令定义。

```json
{
  "id": "unique_node_id_within_graph",
  "depends_on": ["another_node_id"],
  "run": [
    {
      "runtime": "runtime_name_A",
      "config": {
        "param1": "value1",
        "param2": "{{ nodes.data_provider.output }}" 
      }
    },
    {
      "runtime": "runtime_name_B",
      "config": {
        // 这个指令的配置
      }
    }
  ]
}
```
*   `id`: 节点在图内的唯一标识符。
*   `run`: 一个**有序的**指令列表，定义节点的行为。
*   `depends_on` (可选): 一个节点 ID 的列表。用于明确声明当前节点必须在列表中的所有节点成功执行后才能开始，解决了无法自动推断的隐式依赖问题。

### 3.2 Hevno 宏系统：可编程的配置

欢迎来到 Hevno 宏系统，这是让您的静态图定义变得鲜活、动态和智能的核心引擎。我们摒弃了复杂的模板语言，转而拥抱一种更强大、更直观的理念：

> **在配置中，像写 Python 一样思考。**

宏系统允许您在图定义（JSON 文件）的字符串值中直接嵌入可执行的 Python 代码。它不仅能用于简单的变量替换，更是实现动态逻辑、状态操作和世界演化的瑞士军刀。

#### 3.2.1 核心理念：逐步求值，精确控制

##### 3.2.1.1 唯一的语法：`{{ ... }}`

您只需要记住一种语法。任何被双大括号 `{{ ... }}` 包裹起来的内容，都会被 Hevno 引擎视为一段可执行的 Python 代码。

```json
// 简单求值
{ "config": { "value": "{{ 1 + 1 }}" } }

// 访问世界状态
{ "config": { "prompt": "{{ f'你好，{world.player_name}！' }}" } }

// 执行复杂逻辑并修改状态
{
  "config": {
    "script": "{{
      if world.player.is_tired:
          world.player.energy -= 10
      else:
          world.player.energy += 5
    }}"
  }
}
```

##### 3.2.1.2 智能的执行模型：指令前的即时求值 (Just-in-Time Evaluation)

这是理解宏系统强大能力的关键。宏的求值不是在节点开始时一次性完成的，而是与节点的指令执行紧密相连。

在一个节点内，引擎会严格按照 `run` 列表中的指令顺序执行。在**每一个**指令即将执行其 `runtime` **之前**，引擎会自动**遍历该指令的 `config`**。当它遇到一个值为 `{{...}}` 宏格式的字符串时，它会**执行一次**该宏，并用其返回结果**替换**掉原有的宏字符串。

这意味着：
1.  **所见即所得**：当您的运行时（如 `llm.default`）拿到 `prompt` 参数时，它**永远**是最终的、计算好的字符串。
2.  **节点内状态流动**：一个指令的宏，可以**立即访问**到该节点内**上一个指令**执行后产生的任何状态变化。这是实现复杂节点内逻辑链的关键。
3.  **隐式返回值**: 如果您的代码块最后一行是一个表达式（例如一个数字、一个字符串、一个函数调用），它的结果将成为这个宏的值。否则，其值为 `None`。

#### 3.2.2 入门指南 (为所有用户)

##### 3.2.2.1 访问核心数据：您的世界交互窗口

宏最强大的能力，在于它能访问和操纵 Hevno 引擎在执行图过程中的所有内部状态。您可以把宏想象成一个开在指令配置上的“开发者控制台”，能让您直接与引擎的“记忆”互动。

在 `{{ ... }}` 内部，您可以访问一个包含了**所有可用上下文信息**的全局命名空间。这些上下文对象都支持便捷的**点符号访问**（如 `world.player.hp`）。

*   **持久化世界状态 (`world`)**: 这是您的沙盒（Sandbox）的长期记忆。所有需要跨越多个执行步骤、长期存在的数据都应存放在这里。您可以读取它，也可以向其中写入新数据或修改现有数据，这些改动将被永久记录在下一个状态快照中。
    *   **用途**: 存储玩家属性（如 `world.player.hp`）、任务进度、世界环境、角色关系等。
    *   **示例 (读取)**: `"{{ f'玩家当前生命值：{world.player.hp}' }}"`
    *   **示例 (写入)**: `"{{ world.quest_log.append('新任务：击败恶龙') }}"`

*   **已完成节点的结果 (`nodes`)**: 这是一个对象，其属性是所有在当前节点执行之前，已经成功完成的节点的 `id`。您可以访问这些节点的最终输出结果。这是实现**节点间**数据流动的关键。
    *   **用途**: 将一个节点的输出作为另一个节点的输入。
    *   **示例**: `"{{ nodes.get_character_name.output.upper() }}"`

*   **节点内管道状态 (`pipe`)**: 这是一个特殊的对象，它包含了**本节点内**所有**上一个指令**执行完成后的输出结果。它允许您在一个节点内部构建强大的数据处理管道，实现**指令间**的数据流动。
    *   **用途**: 将 `system.io.input` 的结果传给 `llm.default`。
    *   **示例**:
        ```json
        "run": [
            { "runtime": "system.io.input", "config": { "value": "a cat" } },
            { "runtime": "llm.default", "config": { "prompt": "{{ f'Tell me a story about {pipe.output}' }}" } }
        ]
        ```

*   **本次运行的临时数据 (`run`)**: 这是一个临时存储区域，其生命周期仅限于**单次**图的执行。执行结束后，其中的所有数据都会被丢弃。
    *   **用途**: 存储触发本次运行的外部输入（如用户的聊天消息）、本次运行中途的临时计算结果等。
    *   **示例**: `"{{ run.trigger_input.user_message }}"`

*   **【新增】可用的服务 (`services`)**: 这是一个特殊的代理对象，是您访问所有已注册插件服务的入口。服务是**懒加载**的：只有当您在宏中第一次访问某个服务（如 `services.llm_service`）时，DI 容器才会创建或获取该服务的实例。
    *   **用途**: 从宏中直接调用任何插件提供的功能，例如发起 LLM 请求或访问持久化存储。
    *   **示例**:
        ```json
        {
          "runtime": "system.execute",
          "config": {
            "code": "{{ services.llm_service.request(model='gemini/gemini-pro', prompt='你好！') }}"
          }
        }
        ```

*   **会话元信息 (`session`)**: 包含了关于整个交互会话的全局信息，例如会话开始的时间、总共执行的回合数等。
    *   **用途**: 用于记录、调试或实现与时间相关的逻辑。
    *   **示例**: `"{{ f'当前是第 {session.turn_count} 回合' }}"`

##### 3.2.2.2 “开箱即用”的工具箱

我们预置了一些标准 Python 模块，您无需 `import` 即可直接使用：`random`, `math`, `datetime`, `json`, `re`。

*   掷一个20面的骰子: `"{{ random.randint(1, 20) }}"`
*   从列表中随机选一个: `"{{ random.choice(['红色', '蓝色', '绿色']) }}"`

#### 3.2.3 实用示例

##### 示例1：动态生成 NPC 对话

根据玩家的声望 (`world.player_reputation`)，NPC 会有不同的反应。

```json
{
  "id": "npc_greeting",
  "run": [
    {
      "runtime": "llm.default",
      "config": {
        "prompt": "{{
          rep = world.player_reputation
          if rep > 50:
              f'欢迎，尊敬的 {world.player_name}！见到您真是我的荣幸。'
          elif rep < -50:
              '哼，你还敢出现在我面前？'
          else:
              '哦，是你啊。'
        }}"
      }
    }
  ]
}
```

##### 示例2：在一个节点内完成“计算伤害并更新状态”

这个例子完美地展示了指令式执行和 `pipe` 对象的能力。

```json
{
    "id": "take_damage",
    "run": [
    {
        "runtime": "system.io.input",
        "config": {
        "value": "{{ run.trigger_input.damage }}"
        }
    },
    {
        "runtime": "system.execute",
        "config": {
        "code": "{{
            damage_amount = pipe.output
            world.player_hp -= damage_amount
            world.battle_log.append(f'玩家受到了 {damage_amount} 点伤害。')
        }}"
        }
    }
    ]
}
```
**执行流程**:
1.  第一个指令执行，它的输出 (`damage` 值) 被放入 `pipe` 对象。
2.  第二个指令开始执行，它的 `config` 中的宏被求值。
3.  `pipe.output` 成功地获取了上一步的伤害值。
4.  `world` 状态被成功修改。

#### 3.2.4 并发安全：引擎的承诺与您的责任

Hevno 引擎天生支持并行节点执行，这意味着没有依赖关系的节点会被同时运行以提升性能。为了让您在享受并行优势的同时，不必担心复杂的数据竞争问题，我们内置了强大的**宏级原子锁 (Macro-level Atomic Lock)** 机制。

##### 3.2.4.1 引擎的承诺：透明的并发安全

Hevno 引擎的核心承诺是：**为所有基于 Python 基础数据类型（字典、列表、数字、字符串等）的世界状态操作，提供完全透明的、默认开启的并发安全保护。**

这意味着，当您在宏中编写以下代码时，我们保证其结果在任何并行执行下都是正确和可预测的：
*   `world.counter += 1`
*   `world.player['stats']['strength'] -= 5`
*   `world.log.append("New event")`

**工作原理：** 在执行任何一个宏脚本（即 `{{ ... }}` 中的全部内容）之前，引擎会自动获取一个全局写入锁。在宏脚本执行完毕后，锁会自动释放。这保证了**每一个宏脚本的执行都是一个不可分割的原子操作**。您无需做任何事情，即可免费获得这份安全保障。

##### 3.2.4.2 问题的“完美风暴”：何时会超出引擎的保护范围？

我们的自动化保护机制是有边界的。一个操作**必定会**产生不可预测的并发问题（竞态条件），当且仅当它**同时满足以下所有条件**：

1.  **使用自定义类管理可变状态：** 您在宏中定义了 `class MyObject:` 并在其实例中直接存储可变数据（如 `self.hp = 100`），并将其存入 `world`。
2.  **使用非纯方法修改状态：** 您调用了该实例的一个方法来直接修改其内部状态（如 `my_obj.take_damage(10)`，其内部实现是 `self.hp -= 10`）。
3.  **真正的并行执行：** 您将这个修改操作放在了两个或多个**无依赖关系**的并行节点中。
4.  **操作同一数据实例：** 这些并行节点操作的是**同一个对象实例**（e.g., `world.player_character`）。

这个场景的本质是，您创建了一个引擎无法自动理解其内部工作原理的“黑盒”（您的自定义类），并要求引擎在并行环境下保证其内部操作的原子性。这是一个理论上无法被通用引擎自动解决的问题。

##### 3.2.4.3 解决方案路径：从推荐模式到自定义运行时

如果您发现自己确实需要实现上述的复杂场景，我们提供了从易到难、从推荐到专业的解决方案路径：

**第一层（强烈推荐）：遵循“数据-逻辑分离”设计模式**

这是解决此问题的**首选方案**。它不需要您理解并发的复杂性，只需稍微调整代码组织方式：

*   **状态用字典：** `world.player = {'hp': 100}`
*   **逻辑用函数：** `def take_damage(p, amount): p['hp'] -= amount`
*   **在宏中调用：** `{{ take_damage(world.player, 10) }}`

这种模式能完美地被我们的自动化安全机制所覆盖，是 99% 的用户的最佳选择。

**第二层（最终选择）：编写自定义运行时（插件）**

如果您是高级开发者，并且有强烈的理由必须使用自定义类和方法来处理并发状态（例如，与外部系统集成或实现极其复杂的领域模型），那么正确的做法是**将这个责任从宏中移出，封装到一个自定义的运行时中**。

**为什么应该使用自定义运行时？**

*   **明确的控制权：** 在您自己的运行时 `execute` 方法中，您可以直接访问 `ExecutionContext` 并获取全局的 **`asyncio.Lock`**。这让您可以**精确地、手动地**控制加锁的范围，以保护您的自定义对象操作。
*   **清晰的职责划分：**
    *   **宏（Macro）** 的设计目标是**快速、便捷的逻辑编排和数据转换**，它不应该承载复杂的、需要手动管理的并发控制逻辑。
    *   **运行时（Runtime）** 的设计目标是**执行封装好的、具有明确输入和输出的、可重用的功能单元**。处理与特定自定义对象相关的、复杂的原子操作，正是运行时的用武之地。
*   **可测试与可复用：** 将复杂逻辑封装在运行时中，使得该逻辑单元可以被独立测试，并在图定义中被多次复用。

#### 3.2.5 高级指南 (为开发者)

##### 3.2.5.1 宏的转义与 `system.execute`

这是宏系统最强大的功能之一，允许您创建能与 LLM 进行深度交互的代理。

**场景**: 您想让 LLM 能够通过返回特定指令来操纵世界状态。

**步骤 1: 发送“转义”的指令给 LLM**

您需要向 LLM 发送包含 `{{...}}` 语法的提示，但又不希望它在发送前被引擎执行。诀窍是**在宏内部使用字符串字面量**。

```json
// 指令 1: 指导 LLM
{
  "runtime": "llm.default",
  "config": {
    "prompt": "{{
      # 使用 f-string 和单引号来构建最终的 prompt
      # 这样 '{{...}}' 部分就会被当作普通文本
      f'''
      你是一个游戏助手。要将玩家的生命值设置为100，你应该返回：'{{ world.player_hp = 100 }}'
      
      现在，请为我恢复玩家的能量。
      '''
    }}"
  }
}
```
引擎在预处理此指令时，会执行 f-string，生成一个包含 `{{ world.player_hp = 100 }}` **文本**的字符串，然后将其发送给 LLM。

**步骤 2: 执行 LLM 返回的指令**

假设上一步的 LLM 返回了字符串 `"{{ world.player_energy = 100 }}"`。这个字符串现在存储在 `pipe.llm_output` 中。它只是一个普通的字符串，不会自动执行。

要执行它，我们需要在下一个指令使用 `system.execute` 运行时。

```json
// 指令 2: 执行 LLM 的返回
{
  "runtime": "system.execute",
  "config": {
    // 1. 在预处理阶段，这个宏被执行，
    //    'code' 的值变成了字符串 "{{ world.player_energy = 100 }}"
    "code": "{{ pipe.llm_output }}",
  }
}
```
`system.execute` 运行时会接收到 `code` 字段的值，并对其进行**二次求值**，从而真正执行 `world.player_energy = 100`，修改世界状态。

##### 3.2.5.2 动态定义函数与 `import`

您可以 `import` 任何库，或在 `world` 对象上动态创建函数，以构建可复用的逻辑或实现世界的自我演化。

```json
{
  "id": "teach_world_new_trick",
  "run": [{
    "runtime": "system.execute",
    "config": { "code": "{{
      import numpy as np # 导入外部库

      def calculate_weighted_average(values, weights):
          return np.average(values, weights=weights)

      if not hasattr(world, 'utils'): world.utils = {}
      world.utils['weighted_avg'] = calculate_weighted_average
    }}"
  }}]
}
```
在后续节点中，您就可以直接调用 `{{ world.utils.weighted_avg(...) }}`。

## 4. `system` 运行时参考

Hevno 引擎通过 `core_engine` 插件提供了一套功能强大、职责清晰的内置运行时，它们都位于 `system` 命名空间下。这套运行时是构建复杂图逻辑的基础工具。

### 4.1. 核心设计原则

*   **职责明确**: 每个运行时都封装一个有意义的、可复用的逻辑单元。
*   **LLM的纯粹性**: 保持 `llm.default` 的核心职责——与LLM API交互。所有的数据预处理（如格式化）和后处理（如解析）都应由独立的 `system` 运行时完成。
*   **通用性与可组合性**: 运行时被设计为通用的“瑞士军刀”，能够通过组合解决广泛的问题。
*   **优先使用宏**: 对于简单的状态读写操作（如 `world.player.hp` 的读取和修改），应鼓励直接使用宏。

### 4.2. `system.io` (输入/输出)

#### 4.2.1. `system.io.input`
*   **摘要**: 将一个静态或动态生成的值注入到节点管道中。这是节点内部数据处理流程最基础的“数据源”。
*   **配置**:
    *   `value` (any, 必需): 要注入的值，支持宏。
*   **输出**: `{"output": <value 求值后的结果>}`.
*   **示例**:
    ```json
    {
      "runtime": "system.io.input",
      "config": {
        "value": "{{ f'当前玩家是 {world.player_name}' }}"
      }
    }
    ```

#### 4.2.2. `system.io.log`
*   **摘要**: 向后端日志系统输出一条消息，用于调试图执行流程。
*   **配置**:
    *   `message` (string, 必需): 要记录的日志消息，支持宏。
    *   `level` (string, 可选): 日志级别，可选 `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"`。默认为 `"info"`。
*   **输出**: `{}` (纯副作用)。
*   **示例**:
    ```json
    {
      "runtime": "system.io.log",
      "config": {
        "message": "Debug: Player HP is {{ world.player_hp }} before combat.",
        "level": "debug"
      }
    }
    ```

### 4.3. `system.data` (数据处理)

#### 4.3.1. `system.data.format`
*   **摘要**: 将列表或字典数据源格式化为单一字符串。
*   **配置**:
    *   `items` (list | dict, 必需): 要格式化的数据源。
    *   `template` (string, 必需): 格式化模板。`items` 为列表时，可使用 `{item}`；为字典时，可使用 `{key}` 和 `{value}`。
    *   `joiner` (string, 可选): 连接符，默认为 `"\n"`。
*   **输出**: `{"output": <格式化后的最终字符串>}`.
*   **示例**:
    ```json
    {
      "runtime": "system.data.format",
      "config": {
        "items": "{{ nodes.get_recent_events.output }}",
        "template": "- {item.content} (Source: {item.source})",
        "joiner": "\\n"
      }
    }
    ```

#### 4.3.2. `system.data.parse`
*   **摘要**: 将字符串（如LLM的输出）解析为结构化的数据对象（JSON/XML）。
*   **配置**:
    *   `text` (string, 必需): 待解析的字符串。
    *   `format` (string, 必需): 解析格式，支持 `"json"` 和 `"xml"`。
    *   `selector` (string, 可选): 仅 `format` 为 `"xml"` 时使用，一个简化的类XPath选择器。
    *   `strict` (boolean, 可选): 是否启用严格模式，默认为 `false`。
*   **输出**: 成功时为 `{"output": <解析后的对象>}`，失败（非严格模式）时为 `{"output": {"error": "..."}}`。
*   **示例**:
    ```json
    {
      "runtime": "system.data.parse",
      "config": {
        "text": "{{ pipe.llm_output }}",
        "format": "json"
      }
    }
    ```

#### 4.3.3. `system.data.regex`
*   **摘要**: 对输入文本执行正则表达式匹配，并提取内容。
*   **配置**:
    *   `text` (string, 必需): 源文本。
    *   `pattern` (string, 必需): 正则表达式模式，支持命名捕获组。
    *   `mode` (string, 可选): 匹配模式，可选 `"search"` (默认) 或 `"find_all"`。
*   **输出**: `{"output": <匹配结果>}` (字典、字符串、列表或 `null`)。
*   **示例**:
    ```json
    {
      "runtime": "system.data.regex",
      "config": {
        "text": "{{ pipe.llm_output }}",
        "pattern": "<thinking>(?P<thought>.+?)</thinking>"
      }
    }
    ```

### 4.4. `system.flow` (流程控制)

#### 4.4.1. `system.flow.call`
*   **摘要**: 调用并执行一个可复用的子图。
*   **配置**:
    *   `graph` (string, 必需): 要调用的子图名称。
    *   `using` (dict, 可选): 传递给子图的输入。
*   **输出**: `{"output": <子图所有最终节点状态的字典>}`.
*   **示例**:
    ```json
    {
      "runtime": "system.flow.call",
      "config": {
        "graph": "process_damage",
        "using": {
          "damage_input": "{{ run.trigger_input.damage_amount }}"
        }
      }
    }
    ```

#### 4.4.2. `system.flow.map`
*   **摘要**: 对一个列表进行并行迭代，为每个元素执行一次子图。
*   **配置**:
    *   `list` (list, 必需): 要迭代的列表。
    *   `graph` (string, 必需): 为每个列表项执行的子图名称。
    *   `using` (dict, 可选): 传递给子图的输入，上下文中额外包含 `source.item` 和 `source.index`。
    *   `collect` (any, 可选): 一个宏，用于从每次子图运行结果中聚合数据。
*   **输出**: `{"output": <包含所有子图运行结果的列表>}`.
*   **示例**:
    ```json
    {
      "runtime": "system.flow.map",
      "config": {
        "list": "{{ world.enemies_in_area }}",
        "graph": "calculate_threat",
        "using": { "enemy_data": "{{ source.item }}" },
        "collect": "{{ nodes.threat_assessment.output }}"
      }
    }
    ```

### 4.5. `system.execute` (高级)

*   **摘要**: 对一个字符串形式的宏代码进行二次求值和执行。
*   **目的**: 作为宏系统的终极“逃生舱口”，用于实现标准运行时无法覆盖的动态逻辑（如执行由LLM生成的代码）。
*   **配置**:
    *   `code` (string, 必需): 包含宏代码的字符串。
*   **输出**: `{"output": <code字段执行后的结果>}`.



## 5. 插件生态系统：动态扩展世界

Hevno Engine 的核心力量来自于其动态、可插拔的插件系统。我们相信，最好的功能来自于社区，因此整个架构被设计为允许任何人轻松地创建、分享和使用插件来扩展引擎的能力。您甚至可以替换掉核心插件，以完全定制您的 Hevno 体验。

### 5.1 声明式插件管理 (`hevno.json`)

我们摒弃了手动管理 `plugins` 文件夹的传统方式，转而采用一种更现代、更健壮的**声明式管理**。您项目所需的所有插件都定义在一个位于项目根目录的 `hevno.json` 文件中。这个文件是您项目插件依赖的**唯一事实来源**。

一个专门的命令行工具 `hevno` 会读取这个文件，并自动完成插件的下载、安装和更新。

**`hevno.json` 格式约定:**

```json
{
  "plugins": {
    "core_engine": {
      "source": "local"
    },
    "stable-dice-roller": {
      "source": "git",
      "url": "https://github.com/Community/hevno-dice-roller",
      "ref": "v1.2.0"
    },
    "my-dev-plugin": {
      "source": "git",
      "url": "https://github.com/YourName/my-plugin-dev",
      "ref": "main",
      "strategy": "latest"
    }
  }
}
```

*   **`plugins`**: 插件字典。
    *   **键 (`core_engine`, `stable-dice-roller`)**: 插件的唯一标识符。这将是它在 `plugins/` 目录下的文件夹名称。
    *   **值 (插件配置对象)**:
        *   `source`: 定义插件来源。
            *   `"local"`: 表示这是一个项目本地的核心插件，由主仓库管理，插件管理器会跳过它。
            *   `"git"`: 表示这是一个需要从远程 Git 仓库下载的第三方插件。
        *   `url` (当 `source` 为 `git` 时): Git 仓库的 HTTPS URL。
        *   `ref` (当 `source` 为 `git` 时): 指定要使用的 Git 版本。可以是**分支名** (如 `main`)、**标签** (如 `v1.2.0`) 或精确的**提交哈希**。
        *   `subdirectory` (可选): 如果插件的代码位于仓库的某个子目录中，在此处指定其路径。
        *   `strategy` (可选): 定义插件的更新策略。
            *   `"pin"` (默认): **固定版本**。插件会被固定在 `ref` 指定的提交上。`sync` 命令如果发现插件已存在，会跳过它。这是用于生产和稳定依赖的最佳实践。
            *   `"latest"`: **追踪最新**。`sync` 命令会总是删除本地的旧版本，并从 `ref` 指定的分支（如 `main`）重新下载最新版本。这非常适合在开发阶段追踪一个活跃开发的插件。

### 5.2 插件管理工作流 (`hevno` CLI)

Hevno Engine 自带一个命令行工具，让插件管理变得轻而易举。

#### 首次设置项目

新开发者克隆您的项目后，只需几个简单步骤即可启动：

```bash
# 1. 克隆仓库
git clone https://github.com/Niurouxing/TheWanderingHevno.git
cd TheWanderingHevno

# 2. 安装项目依赖（包括命令行工具）
pip install -e ".[dev]"

# 3. 同步插件
#    这个命令会读取 hevno.json 并下载所有 Git 插件
hevno plugins sync

# 4. 启动应用
uvicorn backend.main:app --reload
```

#### 管理插件

*   **添加一个稳定的、固定版本的插件:**
    ```bash
    # `ref` 可以是标签或提交哈希
    hevno plugins add https://github.com/some-dev/hevno-weather-plugin --ref v1.0.0
    ```

*   **添加一个开发中的、需要追踪最新版本的插件:**
    ```bash
    # 使用 --track-latest 标志
    hevno plugins add https://github.com/YourName/my-plugin-dev --ref main --track-latest
    ```

*   **移除插件:**
    ```bash
    hevno plugins remove hevno-weather-plugin
    ```

*   **更新插件:**
    *   对于**固定版本 (`pin`)**的插件: 在 `hevno.json` 中，手动将 `ref` 修改为新的版本号或提交哈希，然后运行 `hevno plugins sync`。
    *   对于**追踪最新 (`latest`)**的插件: 只需运行 `hevno plugins sync`，管理器就会自动获取指定分支的最新代码。

### 5.3 插件开发约定

想要为您自己的 Hevno 项目或为社区贡献一个插件吗？遵循以下简单的约定即可：

1.  **目录结构**: 每个插件都是一个独立的 Python 包，位于 `plugins/` 目录下。一个标准的插件包含：
    ```
    plugins/
    └── my-awesome-plugin/
        ├── __init__.py         # 插件入口点，必须包含 register_plugin 函数
        ├── manifest.json       # 插件元数据（名称、优先级等）
        ├── ... (service.py, router.py, etc.)
    ```

2.  **`manifest.json`**: 这是插件的“身份证”，定义了其元数据。
    ```json
    {
        "name": "my-awesome-plugin",
        "version": "1.0.0",
        "description": "A brief description of what this plugin does.",
        "author": "Your Name",
        "priority": 50,
        "dependencies": ["core_engine"] 
    }
    ```
    *   `priority`: 加载优先级，数字越小越先加载。核心插件有预设的优先级（如 `core_logging` 是 -100，`core_engine` 是 50）。

3.  **入口点 `__init__.py`**: 每个插件必须提供一个 `register_plugin` 函数，这是引擎与插件通信的桥梁。
    ```python
    # plugins/my-awesome-plugin/__init__.py
    from backend.core.contracts import Container, HookManager

    def register_plugin(container: Container, hook_manager: HookManager):
        # 在这里...
        # 1. 向容器注册你的服务工厂
        # container.register("my_service", _create_my_service)
        
        # 2. 向钩子管理器注册你的钩子实现
        # hook_manager.add_implementation("collect_runtimes", provide_my_runtime)
    ```

通过这个系统，Hevno 的世界可以像乐高积木一样被无限组合和扩展。我们期待看到您创造的精彩插件！


## `core_memoria` 插件文档

### 1. 简介：赋予世界记忆与反思的能力

`core_memoria` 是 Hevno 引擎中的一个核心插件，其使命是为您的 AI 世界提供一个强大、持久且可查询的记忆系统。它不仅仅是一个日志记录器，更是一个能让 AI 代理和世界本身从历史中学习、演化和反思的动态知识库。

通过 `core_memoria`，您可以轻松实现：
*   **短期记忆**：为 LLM 提供最近发生的事件，确保对话和行为的连贯性。
*   **长期反思**：自动将一系列零散事件**综合**成更高层次的“里程碑”或“章节总结”。
*   **情境感知**：根据标签或层级检索相关的历史记忆，让 AI 能够将新旧信息联系起来。
*   **角色心路历程**：为每个角色或主题维护独立的“记忆回廊”，追踪他们的成长与变化。

`core_memoria` 将离散的事件流，编织成一张富有深度和因果关系的智慧之网，是构建真正动态、可交互 AI 世界的关键。

### 2. 核心概念：世界状态中的“记忆宫殿”

遵循 Hevno“状态先行”的哲学，所有记忆的最终真相都驻留在持久化的 `world_state` 中一个名为 `memoria` 的结构里。您可以将 `world.memoria` 想象成一个可扩展的“记忆宫殿”。

#### 2.1 记忆回廊 (Memory Stream)

“记忆宫殿” (`world.memoria`) 是一个字典，它的每一个键都代表一个独立的“记忆回廊”（Stream）。这允许您为不同的实体或主题（如主线故事、特定角色的思想、某个组织的历史）分别记录记忆。

```json
// world.memoria 的结构
"world": {
  "memoria": {
    "__global_sequence__": 12, // 内部使用的全局序列号
    "main_story": { /* ... 主线故事的 MemoryStream 对象 ... */ },
    "character_thoughts_humphrey": { /* ... 汉弗莱爵士心路历程的 MemoryStream 对象 ... */ }
  }
}
```

#### 2.2 记忆条目 (Memory Entry)

每个“记忆回廊”中都包含一个按时间顺序排列的 `entries` 列表，列表中的每一项都是一个结构化的“记忆条目”。

```json
// 一个 MemoryEntry 对象的示例
{
  "id": "a9b1c2d3-...",
  "sequence_id": 5, // 全局唯一的、严格递增的因果序列号
  "level": "event",
  "tags": ["combat", "goblin"],
  "content": "玩家在森林入口遭遇并击败了三只哥布林。"
}
```

*   `sequence_id`：**这至关重要**。它是一个在**所有**记忆流中都单调递增的整数，精确地记录了事件在游戏世界内的**因果顺序**。它不受现实时间影响，确保了读档和回滚的确定性。
*   `level`: 记忆的层级，如 `"event"`, `"dialogue"`, `"milestone"`, `"thought"`。用于分层检索。
*   `tags`: 一个关键词列表，用于实现强大的相关性检索。
*   `content`: 记忆的文本内容。

### 3. 使用指南：运行时 (Runtimes)

`core_memoria` 插件提供了一套简洁、强大的运行时（积木块），让您可以轻松地与记忆系统交互，而无需编写复杂的代码。

#### 3.1 `memoria.add`：烙印新记忆

这是将一个新事件转化为持久记忆的核心指令。

*   **功能**：向指定的记忆流中添加一条新的条目。
*   **配置参数**：
    *   `stream` (必需): `string` - 要添加到的记忆流的名称。
    *   `content` (必需): `any` - 记忆的内容。宏求值后会被转换为字符串。
    *   `level` (可选): `string` - 该条目的层级，默认为 `"event"`。
    *   `tags` (可选): `List[string]` - 与该条目关联的标签列表。

*   **示例**：
    ```json
    {
      "id": "player_enters_cave",
      "run": [{
        "runtime": "memoria.add",
        "config": {
          "stream": "main_story",
          "level": "exploration_event",
          "tags": ["dungeon", "cave", "danger"],
          "content": "{{ f'玩家 {world.player_name} 小心地进入了那个散发着恶臭的洞穴。' }}"
        }
      }]
    }
    ```

#### 3.2 `memoria.query`：检索历史片段

这个运行时允许您根据多种条件，以声明式的方式从记忆流中检索信息。

*   **功能**：查询一个记忆流并返回一个符合条件的记忆条目列表。
*   **配置参数**：
    *   `stream` (必需): `string` - 要查询的记忆流的名称。
    *   `latest` (可选): `int` - 只返回最新的 N 条记忆。
    *   `levels` (可选): `List[string]` - 只返回 `level` 在此列表中的条目。
    *   `tags` (可选): `List[string]` - 返回至少包含**一个**指定标签的条目。
    *   `order` (可选): `"ascending"` 或 `"descending"` - 返回结果的排序顺序，基于 `sequence_id`。默认为 `"ascending"`。

*   **示例：为 LLM 获取最近的 3 个事件作为短期记忆**
    ```json
    {
      "id": "gather_short_term_memory",
      "run": [{
        "runtime": "memoria.query",
        "config": {
          "stream": "main_story",
          "latest": 3,
          "order": "ascending"
        }
      }]
    }
    // 指令执行后，pipe.output 将会是一个包含最多3个记忆条目对象的列表
    ```

#### 3.3 `memoria.aggregate`：呈现记忆文本

这个运行时是一个便利工具，用于将 `memoria.query` 返回的结构化列表，格式化为一段单一、可读的文本。

*   **功能**：将一个记忆条目列表聚合成一个字符串。
*   **配置参数**：
    *   `entries` (必需): `List[dict]` - 一个记忆条目对象的列表，通常直接来自上一步的 `pipe.output`。
    *   `template` (可选): `string` - 一个格式化字符串，用于处理列表中的每一个条目。您可以使用 `{content}`, `{level}`, `{tags}`, `{sequence_id}` 等占位符。默认为 `"{content}"`。
    *   `joiner` (可选): `string` - 用于连接所有格式化后部分的字符串。默认为 `"\n\n"`。

*   **示例：将查询结果格式化为 LLM 的背景提要**
    ```json
    {
      "id": "format_memory_for_llm",
      "depends_on": ["gather_short_term_memory"],
      "run": [{
        "runtime": "memoria.aggregate",
        "config": {
          "entries": "{{ nodes.gather_short_term_memory.output }}",
          "template": "- {content} (Tags: {tags})",
          "joiner": "\\n"
        }
      }]
    }
    // 指令执行后，pipe.output 将是一段格式化好的文本，例如：
    // - 玩家进入了洞穴 (Tags: dungeon, cave)
    // - 玩家点燃了火把 (Tags: light, safety)
    ```
> **【未来规划】**
> `memoria.aggregate` 的功能（将列表格式化为字符串）非常通用。在未来的版本中，我们计划推出一个更强大的、系统级的 `system.format` 或 `system.join` 运行时来处理所有类似的格式化任务。届时，`memoria.aggregate` 将被视为一个便利的别名，但我们鼓励用户迁移到更通用的 `system` 运行时，以保持图逻辑的清晰和一致。

### 4. 自动化功能：记忆的自动综合

`core_memoria` 最强大的功能之一是它能够自动进行“记忆综合”——即在后台调用 LLM，将一系列零散的事件总结成一个更高层次的“里程碑”或“章节概要”。

这个过程是**完全异步和非阻塞的**，不会影响主图的执行性能。

#### 4.1 如何配置

您可以通过修改 `world.memoria` 中特定流的 `config` 对象来启用和配置此功能。这可以在图的任何地方，使用 `system.execute` 或 `system.set_world_var` 来完成。

```json
// 使用 system.execute 在游戏开始时配置 main_story 流
{
  "id": "setup_memory_synthesis",
  "run": [{
    "runtime": "system.execute",
    "config": {
      "code": "{{
        # 确保 memoria 和 main_story 流存在
        if 'memoria' not in world: world.memoria = {}
        if 'main_story' not in world.memoria: world.memoria.main_story = {}
        if 'config' not in world.memoria.main_story: world.memoria.main_story.config = {}

        # 定义自动综合的行为
        world.memoria.main_story.config.auto_synthesis = {
            'enabled': True,
            'trigger_count': 10,  // 每发生 10 次事件
            'level': 'milestone', // 就生成一个“里程碑”级别的总结
            'model': 'gemini/gemini-1.5-flash',
            'prompt': '''
As a master storyteller, synthesize the following sequence of events into a single, cohesive paragraph that captures the key developments and overall tone.

Events:
{events_text}
'''
        }
      }}"
    }
  }]
}
```

#### 4.2 工作流程

1.  当 `memoria.add` 被调用时，它会为该流的内部计数器加一。
2.  如果计数器达到了 `trigger_count`，`memoria.add` 会将最近的 N 条事件连同您的配置（`model`, `prompt`）一起，打包成一个后台任务。
3.  主图执行继续，**不受任何影响**。
4.  在后台，任务管理器会执行该任务：调用 LLM，生成总结。
5.  任务完成后，它会将生成的总结作为一个**待处理事件**放入一个特殊的队列中。
6.  在**下一次**图执行开始之前，引擎会自动检查该队列，并将所有已完成的总结作为新的记忆条目，原子性地添加到对应的记忆流中。

这种设计确保了系统的响应速度和状态的一致性。

### 5. 高级用法：通过宏直接访问

对于需要高度定制化逻辑的开发者，`world.memoria` 的完整数据结构对宏是完全透明的。您可以随时使用 `system.execute` 来编写任意 Python 代码，进行标准运行时无法完成的复杂查询和分析。

```json
// 示例：计算“汉弗莱”的总结中，“背叛”一词在过去24小时内的出现频率
{
  "runtime": "system.execute",
  "config": {
    "code": "{{
      # ... 复杂的、定制化的 Python 逻辑 ...
    }}"
  }
}
```

这种灵活性确保了 `core_memoria` 既是一个易于上手的工具，也是一个功能没有上限的强大平台。