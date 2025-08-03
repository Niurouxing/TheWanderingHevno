# Directory: backend

### __init__.py
```

```

### container.py
```
# backend/container.py

import logging
from typing import Dict, Any, Callable


from backend.core.contracts import Container as ContainerInterface


logger = logging.getLogger(__name__)


class Container(ContainerInterface):

    """一个简单的、通用的依赖注入容器。"""
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}
        self._instances: Dict[str, Any] = {}
        # 注意：此处日志可能还未完全配置，但可以安全调用
        # logger.info("DI Container initialized.")

    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        """
        注册一个服务工厂。

        :param name: 服务的唯一名称。
        :param factory: 一个创建服务实例的函数 (可以无参，或接收 container 实例)。
        :param singleton: 如果为 True，服务只会被创建一次（单例）。
        """
        if name in self._factories:
            logger.warning(f"Overwriting service registration for '{name}'")
        self._factories[name] = factory
        self._singletons[name] = singleton

    def resolve(self, name: str) -> Any:
        """
        解析（获取）一个服务实例。

        如果服务是单例且已被创建，则返回现有实例。
        否则，调用其工厂函数创建新实例。
        """
        if name in self._instances and self._singletons.get(name, True):
            return self._instances[name]

        if name not in self._factories:
            raise ValueError(f"Service '{name}' not found in container.")

        factory = self._factories[name]
        
        try:
            # 尝试将容器本身作为依赖注入到工厂中
            instance = factory(self)
        except TypeError:
            # 如果工厂不接受参数，则直接调用
            instance = factory()

        logger.debug(f"Resolved service '{name}'. Singleton: {self._singletons.get(name, True)}")

        if self._singletons.get(name, True):
            self._instances[name] = instance
        
        return instance
```

### README.md
```

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

> **注意**: 这些哲学描述的是由 `core-engine` 插件实现的**图执行模型**，与后端代码的组织方式（插件架构）是两个不同但互补的概念。

#### 1.2.1 哲学一：以运行时为中心，指令式地构建行为

> **"Behavior is a sequence of instructions."**

我们摒弃了将所有配置混杂在一起的模式，转而采用一种更清晰、更强大的**指令式**设计。在 Hevno 中：

*   **极简的节点 (`GenericNode`)**: 节点本身只是一个容器。
*   **行为由指令驱动**: 节点的具体行为由其 `run` 字段中一个**有序的指令列表**所定义。
*   **原子指令 (`RuntimeInstruction`)**: 每个指令都包含一个 `runtime`（一个可执行的功能单元）和它自己独立的 `config`（配置）。这确保了逻辑的清晰和数据的隔离。
*   **强大的节点内管道**: 引擎会严格按照指令列表的顺序执行。后一个指令的宏，可以访问到前一个指令执行后产生的最新状态。

**Hevno 的指令式设计:**
```json
// 一个先设置世界状态，再调用 LLM 的复杂节点
{
  "id": "advanced_llm",
  "run": [
    {
      "runtime": "system.set_world_var",
      "config": {
        "variable_name": "character_mood",
        "value": "happy"
      }
    },
    {
      "runtime": "llm.default",
      "config": {
        "prompt": "{{ f'根据角色愉悦的心情 `({world.character_mood})`，生成一句问候。' }}"
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
  "run": [{ "runtime": "system.set_world_var", "config": { "variable_name": "theme", "value": "fantasy" }}]
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
    *   **解耦**: `core-engine` 插件不需要知道 `LLMService` 是如何被创建的，它只需要知道去容器里找一个名为 `"llm_service"` 的服务即可。
    *   **可配置性**: 我们可以轻松地替换实现。例如，在测试环境中，可以注册一个 `MockLLMService` 工厂来代替真实的 `LLMService` 工厂，而使用服务的代码无需任何改动。
    *   **懒加载**: 服务只在第一次被请求时才会被创建，避免了不必要的启动开销。

**示例：`LLMService` 的生命周期**
```python
# 1. 在 core-llm/__init__.py 中，插件注册了一个工厂
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
    1.  **触发 (Trigger)**: 一个插件（发布者）在某个关键执行点，会通过 `hook_manager` 触发一个命名的事件（钩子），并传递相关数据。例如，`core-engine` 在需要所有运行时的时候，会触发 `"collect_runtimes"` 钩子。
    2.  **实现 (Implementation)**: 其他插件（订阅者）可以向 `hook_manager` 注册一个异步函数，以响应该钩子。
    3.  **执行 (Execution)**: `hook_manager` 负责调用所有已注册的实现函数，并根据钩子类型（如 `filter`）聚合它们的返回值。

*   **钩子类型**:
    *   **通知 (`trigger`)**: “我刚刚做完了这件事，通知大家一下。” 所有实现并发执行，返回值被忽略。
    *   **过滤 (`filter`)**: “我有一份数据，谁想在上面添加或修改一些东西？” 所有实现按优先级顺序链式执行，后一个实现会接收前一个修改过的数据。非常适合用于收集信息。

**示例：`core-engine` 如何从所有插件收集运行时和 API 路由**
```python
# 在 core-engine/__init__.py 中...
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
# 在 core-llm/__init__.py 中...
async def provide_runtime(runtimes: dict) -> dict:
    runtimes["llm.default"] = LLMRuntime # LLM 插件响应
    return runtimes

# 在 core-api/__init__.py 中...
async def provide_own_routers(routers: list) -> list:
    routers.append(sandbox_router) # API 插件响应
    return routers

# 注册钩子实现
def register_plugin(container: Container, hook_manager: HookManager):
    hook_manager.add_implementation("collect_runtimes", provide_runtime)
    hook_manager.add_implementation("collect_api_routers", provide_own_routers)
```
通过这种方式，`core-engine` 和 `app.py` 根本不需要知道 `core-llm` 或 `core-api` 插件的存在，但依然能获取它们提供的功能，实现了彻底的解耦。

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
    *   监听此钩子的插件（如 `core-engine` 和 `core-api`）现在可以安全地从容器中解析依赖，并执行需要 `async` 的初始化任务，例如从其他插件收集并填充自己的注册表（如 `RuntimeRegistry`）。
4.  **API 路由收集**: `lifespan` 触发 `"collect_api_routers"` 钩子，收集所有插件提供的 FastAPI `APIRouter` 实例，并挂载到主 `app` 上。
5.  **启动完成**: 触发 `"app_startup_complete"` 钩子，应用正式就绪，开始接受请求。


## 3. 图与宏系统定义

本章节将深入探讨您作为“世界创造者”与 Hevno 引擎交互的核心——**图定义**。这部分内容主要由 `core-engine` 插件实现，但其使用方式对所有插件都是通用的。

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
    *   **用途**: 将 `system.input` 的结果传给 `llm.default`。
    *   **示例**:
        ```json
        "run": [
          { "runtime": "system.input", "config": { "value": "a cat" } },
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
      "runtime": "system.input",
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
```

### app.py
```
# backend/app.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.loader import PluginLoader
from backend.core.tasks import BackgroundTaskManager # 【新增】导入新组件

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    container = Container()
    hook_manager = HookManager()

    # 1. 注册平台核心服务
    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)
    
    #  创建并注册后台任务管理器
    task_manager = BackgroundTaskManager(container)
    container.register("task_manager", lambda: task_manager, singleton=True)

    # 2. 加载插件（插件此时仅注册工厂和同步钩子）
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()
    
    logger = logging.getLogger(__name__)
    logger.info("--- FastAPI 应用组装 ---")

    # 3. 将核心服务附加到 app.state，以便依赖注入函数可以访问
    app.state.container = container

    # 4. 触发异步服务初始化钩子
    logger.info("正在为异步初始化触发 'services_post_register' 钩子...")
    await hook_manager.trigger('services_post_register', container=container)
    logger.info("异步服务初始化完成。")

    # 启动后台工作者
    # 这个操作应该在所有服务都注册和初始化之后进行
    task_manager.start()

    # 5. 平台核心负责收集并装配 API 路由
    logger.info("正在从所有插件收集 API 路由...")
    routers_to_add: list[APIRouter] = await hook_manager.filter("collect_api_routers", [])
    
    if routers_to_add:
        logger.info(f"已收集到 {len(routers_to_add)} 个路由。正在添加到应用中...")
        for router in routers_to_add:
            app.include_router(router)
            logger.debug(f"已添加路由: prefix='{router.prefix}', tags={router.tags}")
    else:
        logger.warning("未从插件中收集到任何 API 路由。")
    
    # 6. 触发最终启动完成钩子
    await hook_manager.trigger('app_startup_complete', app=app, container=container)
    
    logger.info("--- Hevno 引擎已就绪 ---")
    yield
    # --- 关闭阶段 ---
    logger.info("--- Hevno 引擎正在关闭 ---")
    
    # 【新增】优雅地停止后台任务管理器
    await task_manager.stop()

    await hook_manager.trigger('app_shutdown', app=app)


def create_app() -> FastAPI:
    """应用工厂函数"""
    app = FastAPI(
        title="Hevno Engine (Plugin Architecture)",
        version="1.2.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
```

### main.py
```
# backend/main.py

import uvicorn
import os
from dotenv import load_dotenv
load_dotenv()

from backend.app import create_app

# 调用工厂函数来获取完全配置好的应用实例
app = create_app()

@app.get("/")
def read_root():
    return {"message": "Hevno Engine (Plugin Architecture) is running!"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        reload_dirs=["backend", "plugins"]
    )
```

### core/hooks.py
```
# backend/core/hooks.py
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Awaitable, TypeVar, Optional
from backend.core.contracts import HookManager as HookManagerInterface

logger = logging.getLogger(__name__)

# 定义可被过滤的数据类型变量
T = TypeVar('T')

# 定义钩子函数的通用签名
HookCallable = Callable[..., Awaitable[Any]]

@dataclass(order=True)
class HookImplementation:
    """封装一个钩子实现及其元数据。"""
    priority: int
    func: HookCallable = field(compare=False)
    plugin_name: str = field(compare=False, default="<unknown>")

class HookManager(HookManagerInterface):
    """
    一个中心化的服务，负责发现、注册和调度所有钩子实现。
    它的设计是完全通用的，不与任何特定的钩子绑定。
    """
    def __init__(self):
        self._hooks: Dict[str, List[HookImplementation]] = defaultdict(list)
        logger.info("HookManager initialized.")

    def add_implementation(
        self,
        hook_name: str,
        implementation: HookCallable,
        priority: int = 10,
        plugin_name: str = "<core>"
    ):
        """向管理器注册一个钩子实现。"""
        if not asyncio.iscoroutinefunction(implementation):
            raise TypeError(f"Hook implementation for '{hook_name}' must be an async function.")

        hook_impl = HookImplementation(priority=priority, func=implementation, plugin_name=plugin_name)
        self._hooks[hook_name].append(hook_impl)
        self._hooks[hook_name].sort() # 保持列表按优先级排序（从小到大）
        logger.debug(f"Registered hook '{hook_name}' from plugin '{plugin_name}' with priority {priority}.")

    async def trigger(self, hook_name: str, **kwargs: Any) -> None:
        """触发一个“通知型”钩子。并发执行，忽略返回值。"""
        if hook_name not in self._hooks:
            return

        implementations = self._hooks[hook_name]
        tasks = [impl.func(**kwargs) for impl in implementations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                impl = implementations[i]
                logger.error(
                    f"Error in NOTIFICATION hook '{hook_name}' from plugin '{impl.plugin_name}': {result}",
                    exc_info=result
                )

    async def filter(self, hook_name: str, data: T, **kwargs: Any) -> T:
        """
        触发一个“过滤型”钩子，形成处理链。
        非常适合用于收集数据。
        """
        if hook_name not in self._hooks:
            return data

        current_data = data
        # 按优先级顺序执行
        for impl in self._hooks[hook_name]:
            try:
                # 每个钩子实现都会接收上一个实现返回的数据
                current_data = await impl.func(current_data, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in FILTER hook '{hook_name}' from plugin '{impl.plugin_name}'. Skipping. Error: {e}",
                    exc_info=e
                )
        
        return current_data

    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]:
        """
        触发一个“决策型”钩子。按优先级从高到低执行，并返回第一个非 None 的结果。
        """
        if hook_name not in self._hooks:
            return None

        # self._hooks is sorted low-to-high priority, so iterate in reverse.
        for impl in reversed(self._hooks[hook_name]):
            try:
                result = await impl.func(**kwargs)
                if result is not None:
                    logger.debug(
                        f"DECIDE hook '{hook_name}' was resolved by plugin "
                        f"'{impl.plugin_name}' with priority {impl.priority}."
                    )
                    return result
            except Exception as e:
                logger.error(
                    f"Error in DECIDE hook '{hook_name}' from plugin '{impl.plugin_name}'. Skipping. Error: {e}",
                    exc_info=e
                )
        return None
```

### core/tasks.py
```
# backend/core/tasks.py

import asyncio
import logging
from typing import Callable, Coroutine, Any, List

# 从核心契约中导入 Container 接口
from backend.core.contracts import Container, BackgroundTaskManager as BackgroundTaskManagerInterface

logger = logging.getLogger(__name__)

class BackgroundTaskManager(BackgroundTaskManagerInterface):
    """一个简单的、通用的后台任务管理器。"""
    def __init__(self, container: Container, max_workers: int = 3):
        self._container = container
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._max_workers = max_workers
        self._is_running = False

    def start(self):
        """启动工作者协程。"""
        if self._is_running:
            logger.warning("BackgroundTaskManager is already running.")
            return
            
        logger.info(f"正在启动 {self._max_workers} 个后台工作者...")
        for i in range(self._max_workers):
            worker_task = asyncio.create_task(self._worker(f"后台工作者-{i}"))
            self._workers.append(worker_task)
        self._is_running = True

    async def stop(self):
        """优雅地停止所有工作者。"""
        if not self._is_running:
            return
            
        logger.info("正在停止后台工作者...")
        # 等待队列中的所有任务被处理完毕
        await self._queue.join()
        
        # 取消所有工作者协程
        for worker in self._workers:
            worker.cancel()
            
        # 等待所有工作者协程完全停止
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._is_running = False
        logger.info("所有后台工作者已安全停止。")

    def submit_task(self, coro_func: Callable[..., Coroutine], *args: Any, **kwargs: Any):
        """
        向队列提交一个任务。
        
        :param coro_func: 要在后台执行的协程函数。
        :param args, kwargs: 传递给协程函数的参数。
        """
        if not self._is_running:
            logger.error("无法提交任务：后台任务管理器尚未启动。")
            return
            
        # 我们将协程函数本身和它的参数一起放入队列
        self._queue.put_nowait((coro_func, args, kwargs))
        logger.debug(f"任务 '{coro_func.__name__}' 已提交到后台队列。")

    async def _worker(self, name: str):
        """
        工作者协程，它会持续从队列中获取并执行任务。
        """
        logger.info(f"后台工作者 '{name}' 已启动。")
        while True:
            try:
                # 从队列中阻塞式地获取任务
                coro_func, args, kwargs = await self._queue.get()
                
                logger.debug(f"工作者 '{name}' 获取到任务: {coro_func.__name__}")
                try:
                    # 【关键】执行协程函数。
                    # 我们将容器实例作为第一个参数注入，以便后台任务能解析它需要的任何服务。
                    await coro_func(self._container, *args, **kwargs)
                except Exception:
                    logger.exception(f"工作者 '{name}' 在执行任务 '{coro_func.__name__}' 时遇到错误。")
                finally:
                    # 标记任务完成，以便 queue.join() 可以正确工作
                    self._queue.task_done()
            
            except asyncio.CancelledError:
                logger.info(f"后台工作者 '{name}' 正在关闭。")
                break
```

### core/__init__.py
```

```

### core/loader.py
```
# backend/core/loader.py

import json
import logging
import importlib
import importlib.resources
import traceback
from typing import List, Dict

# 导入类型提示，而不是实现
from backend.core.contracts import Container, HookManager, PluginRegisterFunc

logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self, container: Container, hook_manager: HookManager):
        self._container = container
        self._hook_manager = hook_manager

    def load_plugins(self):
        """执行插件加载的全过程：发现、排序、注册。"""
        # 在日志系统配置前使用 print
        print("\n--- Hevno 插件系统：开始加载 ---")
        
        # 阶段一：发现
        all_plugins = self._discover_plugins()
        if not all_plugins:
            print("警告：在 'plugins' 目录中未发现任何插件。")
            print("--- Hevno 插件系统：加载完成 ---\n")
            return

        # 阶段二：排序 (根据 manifest 中的 priority)
        sorted_plugins = sorted(all_plugins, key=lambda p: (p['manifest'].get('priority', 100), p['name']))
        
        print("插件加载顺序已确定：")
        for i, p_info in enumerate(sorted_plugins):
            print(f"  {i+1}. {p_info['name']} (优先级: {p_info['manifest'].get('priority', 100)})")

        # 阶段三：注册
        self._register_plugins(sorted_plugins)
        
        logger.info("所有已发现的插件均已加载并注册完毕。")
        print("--- Hevno 插件系统：加载完成 ---\n")

    def _discover_plugins(self) -> List[Dict]:
        """扫描 'plugins' 包，读取所有子包中的 manifest.json 文件。"""
        discovered = []
        try:
            # 使用现代的 importlib.resources 来安全地访问包数据
            plugins_package_path = importlib.resources.files('plugins')
            
            for plugin_path in plugins_package_path.iterdir():
                if not plugin_path.is_dir() or plugin_path.name.startswith(('__', '.')):
                    continue

                manifest_path = plugin_path / "manifest.json"
                if not manifest_path.is_file():
                    continue
                
                try:
                    manifest_content = manifest_path.read_text(encoding='utf-8')
                    manifest = json.loads(manifest_content)
                    # 构造 Python 导入路径
                    import_path = f"plugins.{plugin_path.name}"
                    
                    plugin_info = {
                        "name": manifest.get('name', plugin_path.name),
                        "manifest": manifest,
                        "import_path": import_path
                    }
                    discovered.append(plugin_info)
                except Exception as e:
                    print(f"警告：无法解析插件 '{plugin_path.name}' 的 manifest.json: {e}")
                    pass
        
        except (ModuleNotFoundError, FileNotFoundError):
            print("信息：'plugins' 目录不存在或为空，跳过插件加载。")
            pass
            
        return discovered
    
    def _register_plugins(self, plugins: List[Dict]):
        """按顺序导入并调用每个插件的注册函数。"""
        for plugin_info in plugins:
            plugin_name = plugin_info['name']
            import_path = plugin_info['import_path']
            
            try:
                plugin_module = importlib.import_module(import_path)
                
                if not hasattr(plugin_module, "register_plugin"):
                    print(f"警告：插件 '{plugin_name}' 未定义 'register_plugin' 函数，已跳过。")
                    continue
                
                register_func: PluginRegisterFunc = getattr(plugin_module, "register_plugin")
                # 将核心服务注入到插件的注册函数中
                register_func(self._container, self._hook_manager)

            except Exception as e:
                print("\n" + "="*80)
                print(f"!!! 致命错误：加载插件 '{plugin_name}' ({import_path}) 失败 !!!")
                print("="*80)
                traceback.print_exc()
                print("="*80)
                raise RuntimeError(f"无法加载插件 {plugin_name}，应用启动中止。") from e
```

### core/contracts.py
```
# backend/core/contracts.py

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, TypeVar # 增加 Coroutine
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator
from abc import ABC, abstractmethod

# --- 1. 核心服务接口与类型别名 (用于类型提示) ---

# 定义一个泛型，常用于 filter 钩子
T = TypeVar('T')

# 插件注册函数的标准签名
PluginRegisterFunc = Callable[['Container', 'HookManager'], None]

# 为核心服务定义接口，插件不应直接导入实现，而应依赖这些接口
class Container(ABC):
    @abstractmethod
    def register(self, name: str, factory: Callable, singleton: bool = True) -> None: raise NotImplementedError
    @abstractmethod
    def resolve(self, name: str) -> Any: raise NotImplementedError

class HookManager(ABC):
    @abstractmethod
    def add_implementation(self, hook_name: str, implementation: Callable, priority: int = 10, plugin_name: str = "<unknown>"): raise NotImplementedError
    @abstractmethod
    async def trigger(self, hook_name: str, **kwargs: Any) -> None: raise NotImplementedError
    @abstractmethod
    async def filter(self, hook_name: str, data: T, **kwargs: Any) -> T: raise NotImplementedError
    @abstractmethod
    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]: raise NotImplementedError
# --- 2. 核心持久化状态模型 (从旧 core/models.py 和 core/contracts.py 合并) ---

class RuntimeInstruction(BaseModel):
    runtime: str
    config: Dict[str, Any] = Field(default_factory=dict)

class GenericNode(BaseModel):
    id: str
    run: List[RuntimeInstruction]
    depends_on: Optional[List[str]] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphDefinition(BaseModel):
    nodes: List[GenericNode]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v

class StateSnapshot(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sandbox_id: UUID
    graph_collection: GraphCollection
    world_state: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_snapshot_id: Optional[UUID] = None
    triggering_input: Dict[str, Any] = Field(default_factory=dict)
    run_output: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(frozen=True)

class Sandbox(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    head_snapshot_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- 3. 核心运行时上下文模型 (从旧 core/contracts.py 迁移) ---

class SharedContext(BaseModel):
    world_state: Dict[str, Any]
    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    services: Any # 通常是一个 DotAccessibleDict 包装的容器
    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    shared: SharedContext
    initial_snapshot: StateSnapshot
    hook_manager: HookManager
    model_config = {"arbitrary_types_allowed": True}


# --- 4. 系统事件契约 (用于钩子, 从旧 core/contracts.py 迁移) ---

class NodeContext(BaseModel):
    node: GenericNode
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

class EngineStepStartContext(BaseModel):
    initial_snapshot: StateSnapshot
    triggering_input: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)

class EngineStepEndContext(BaseModel):
    final_snapshot: StateSnapshot
    model_config = ConfigDict(arbitrary_types_allowed=True)

class NodeExecutionStartContext(NodeContext): pass
class NodeExecutionSuccessContext(NodeContext):
    result: Dict[str, Any]
class NodeExecutionErrorContext(NodeContext):
    exception: Exception

class BeforeConfigEvaluationContext(NodeContext):
    instruction_config: Dict[str, Any]
class AfterMacroEvaluationContext(NodeContext):
    evaluated_config: Dict[str, Any]

class BeforeSnapshotCreateContext(BaseModel):
    snapshot_data: Dict[str, Any]
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ResolveNodeDependenciesContext(BaseModel):
    node: GenericNode
    auto_inferred_deps: Set[str]


# --- 5. 核心服务接口契约 ---
# 这些是插件应该依赖的抽象接口，而不是具体实现类。

class ExecutionEngineInterface(ABC):
    @abstractmethod
    async def step(self, initial_snapshot: 'StateSnapshot', triggering_input: Dict[str, Any] = None) -> 'StateSnapshot':
        raise NotImplementedError

class SnapshotStoreInterface(ABC):
    @abstractmethod
    def save(self, snapshot: 'StateSnapshot') -> None: raise NotImplementedError
    @abstractmethod
    def get(self, snapshot_id: UUID) -> Optional['StateSnapshot']: raise NotImplementedError
    @abstractmethod
    def find_by_sandbox(self, sandbox_id: UUID) -> List['StateSnapshot']: raise NotImplementedError
    # Adding a clear method for testing purposes
    @abstractmethod
    def clear(self) -> None: raise NotImplementedError

class AuditorInterface(ABC):
    @abstractmethod
    async def generate_full_report(self) -> Dict[str, Any]: raise NotImplementedError
    @abstractmethod
    def set_reporters(self, reporters: List['Reportable']) -> None: raise NotImplementedError

class Reportable(ABC): # 如果还没定义成抽象类，现在定义
    @property
    @abstractmethod
    def report_key(self) -> str: pass
    
    @property
    def is_static(self) -> bool: return True
    
    @abstractmethod
    async def generate_report(self) -> Any: pass

class BackgroundTaskManager(ABC):
    @abstractmethod
    def start(self) -> None: raise NotImplementedError
    @abstractmethod
    async def stop(self) -> None: raise NotImplementedError
    @abstractmethod
    def submit_task(self, coro_func: Callable[..., Coroutine], *args: Any, **kwargs: Any) -> None: raise NotImplementedError
```

# Directory: plugins

### __init__.py
```

```

### core_llm/service.py
```
# plugins/core_llm/service.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, Optional, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    RetryCallState, # 导入 RetryCallState
)

# --- 从本插件内部导入组件 ---
from .manager import KeyPoolManager, KeyInfo
from .models import (
    LLMResponse,
    LLMError,
    LLMErrorType,
    LLMResponseStatus,
    LLMRequestFailedError,
)
from .registry import ProviderRegistry

logger = logging.getLogger(__name__)


def is_retryable_llm_error(retry_state: RetryCallState) -> bool:
    """
    一个 tenacity 重试条件函数。
    【终极修复】它接收一个 RetryCallState 对象，我们需要从中提取真正的异常。
    """
    # 从 retry_state 中获取导致失败的异常
    exception = retry_state.outcome.exception()

    if not exception:
        return False # 如果没有异常，就不重试

    return (
        isinstance(exception, LLMRequestFailedError) and
        exception.last_error is not None and
        exception.last_error.is_retryable
    )


class LLMService:
    """
    LLM 网关的核心服务，负责协调所有组件并执行请求。
    实现了带有密钥轮换、状态管理和指数退避的健壮重试逻辑。
    """
    def __init__(
        self,
        key_manager: KeyPoolManager,
        provider_registry: ProviderRegistry,
        max_retries: int = 3
    ):
        self.key_manager = key_manager
        self.provider_registry = provider_registry
        self.max_retries = max_retries
        self.last_known_error: Optional[LLMError] = None

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        向指定的 LLM 发起请求，并处理重试逻辑。
        """
        self.last_known_error = None
        try:
            provider_name, actual_model_name = self._parse_model_name(model_name)
        except ValueError as e:
            return self._create_failure_response(
                model_name=model_name,
                error=LLMError(
                    error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                    message=str(e),
                    is_retryable=False,
                ),
            )

        def log_before_sleep(retry_state: RetryCallState):
            """在 tenacity 每次重试前调用的日志记录函数。"""
            exc = retry_state.outcome.exception()
            if exc and isinstance(exc, LLMRequestFailedError) and exc.last_error:
                error_type = exc.last_error.error_type.value
            else:
                error_type = "unknown"
            
            logger.warning(
                f"LLM request for {model_name} failed with a retryable error ({error_type}). "
                f"Waiting {retry_state.next_action.sleep:.2f}s before attempt {retry_state.attempt_number + 1}."
            )
        
        retry_decorator = retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=is_retryable_llm_error,
            reraise=True,
            before_sleep=log_before_sleep
        )

        wrapped_attempt = retry_decorator(self._attempt_request)
        try:
            return await wrapped_attempt(provider_name, actual_model_name, prompt, **kwargs)
        
        except LLMRequestFailedError as e:
            final_message = (
                f"LLM request for model '{model_name}' failed permanently after {self.max_retries} attempt(s)."
            )
            # exc_info=False 因为我们正在从原始异常链中引发一个新的、更清晰的异常
            logger.error(final_message, exc_info=False)
            raise LLMRequestFailedError(final_message, last_error=self.last_known_error) from e
        
        except Exception as e:
            logger.critical(f"An unexpected non-LLM error occurred in LLMService: {e}", exc_info=True)
            raise

    async def _attempt_request(
        self,
        provider_name: str,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        执行单次 LLM 请求尝试。
        """
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found.")

        try:
            async with self.key_manager.acquire_key(provider_name) as key_info:
                response = await provider.generate(
                    prompt=prompt, model_name=model_name, api_key=key_info.key_string, **kwargs
                )
                
                if response.status in [LLMResponseStatus.ERROR, LLMResponseStatus.FILTERED] and response.error_details:
                    self.last_known_error = response.error_details
                    await self._handle_error(provider_name, key_info, response.error_details)
                    
                    if response.error_details.is_retryable:
                        raise LLMRequestFailedError("Provider returned a retryable error response.", last_error=response.error_details)

                return response
        
        except Exception as e:
            if isinstance(e, LLMRequestFailedError):
                raise e

            llm_error = provider.translate_error(e)
            self.last_known_error = llm_error
            
            error_message = f"Request attempt failed due to an exception: {llm_error.message}"
            raise LLMRequestFailedError(error_message, last_error=llm_error) from e

    async def _handle_error(self, provider_name: str, key_info: KeyInfo, error: LLMError):
        """根据错误类型更新密钥池中密钥的状态。"""
        if error.error_type == LLMErrorType.AUTHENTICATION_ERROR:
            logger.warning(f"Authentication error with key for '{provider_name}'. Banning key.")
            await self.key_manager.mark_as_banned(provider_name, key_info.key_string)
        elif error.error_type == LLMErrorType.RATE_LIMIT_ERROR:
            cooldown = error.retry_after_seconds or 60
            logger.info(f"Rate limit hit for key on '{provider_name}'. Cooling down for {cooldown}s.")
            self.key_manager.mark_as_rate_limited(provider_name, key_info.key_string, cooldown)

    def _parse_model_name(self, model_name: str) -> tuple[str, str]:
        """将 'provider/model_id' 格式的字符串解析为元组。"""
        parts = model_name.split('/', 1)
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"Invalid model name format: '{model_name}'. Expected 'provider/model_id'.")
        return parts[0], parts[1]
    
    def _create_failure_response(self, model_name: str, error: LLMError) -> LLMResponse:
        """创建一个标准的错误响应对象。"""
        return LLMResponse(status=LLMResponseStatus.ERROR, model_name=model_name, error_details=error)


class MockLLMService:
    """
    一个 LLMService 的模拟实现，用于调试和测试。
    它不进行任何网络调用，而是立即返回一个可预测的假响应。
    """
    def __init__(self, *args, **kwargs):
        logger.info("--- MockLLMService Initialized: Real LLM calls are disabled. ---")

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        await asyncio.sleep(0.05)
        mock_content = f"[MOCK RESPONSE for {model_name}] - Prompt received: '{prompt[:150]}...'"
        
        return LLMResponse(
            status=LLMResponseStatus.SUCCESS,
            content=mock_content,
            model_name=model_name,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 15, "total_tokens": len(prompt.split()) + 15}
        )
```

### core_llm/models.py
```
# plugins/core_llm/models.py

from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


# --- Enums for Status and Error Types ---

class LLMResponseStatus(str, Enum):
    """定义 LLM 响应的标准化状态。"""
    SUCCESS = "success"
    FILTERED = "filtered"
    ERROR = "error"


class LLMErrorType(str, Enum):
    """定义标准化的 LLM 错误类型，用于驱动重试和故障转移逻辑。"""
    AUTHENTICATION_ERROR = "authentication_error"  # 密钥无效或权限不足
    RATE_LIMIT_ERROR = "rate_limit_error"          # 达到速率限制
    PROVIDER_ERROR = "provider_error"              # 服务商侧 5xx 或其他服务器错误
    NETWORK_ERROR = "network_error"                # 网络连接问题
    INVALID_REQUEST_ERROR = "invalid_request_error"  # 请求格式错误 (4xx)
    UNKNOWN_ERROR = "unknown_error"                # 未知或未分类的错误


# --- Core Data Models ---

class LLMError(BaseModel):
    """
    一个标准化的错误对象，用于封装来自任何提供商的错误信息。
    """
    error_type: LLMErrorType = Field(
        ...,
        description="错误的标准化类别。"
    )
    message: str = Field(
        ...,
        description="可读的错误信息。"
    )
    is_retryable: bool = Field(
        ...,
        description="此错误是否适合重试（例如，网络错误或某些服务端错误）。"
    )
    retry_after_seconds: Optional[int] = Field(
        default=None,
        description="如果提供商明确告知，需要等待多少秒后才能重试。"
    )
    provider_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="原始的、特定于提供商的错误细节，用于调试。"
    )


class LLMResponse(BaseModel):
    """
    一个标准化的响应对象，用于封装来自任何提供商的成功、过滤或错误结果。
    """
    status: LLMResponseStatus = Field(
        ...,
        description="响应的总体状态。"
    )
    content: Optional[str] = Field(
        default=None,
        description="LLM 生成的文本内容。仅在 status 为 'success' 时保证存在。"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="实际用于生成此响应的模型名称。"
    )
    usage: Optional[Dict[str, int]] = Field(
        default=None,
        description="Token 使用情况统计，例如 {'prompt_tokens': 10, 'completion_tokens': 200}。"
    )
    error_details: Optional[LLMError] = Field(
        default=None,
        description="如果 status 为 'error'，则包含此字段以提供详细的错误信息。"
    )
    
    # 可以在这里添加一个验证器，确保在status为error时，error_details不为空
    # 但为了保持模型的简单性，我们暂时将此逻辑留给上层服务处理。


# --- Custom Exception ---

class LLMRequestFailedError(Exception):
    """
    在所有重试和故障转移策略都用尽后，由 LLMService 抛出的最终异常。
    """
    def __init__(self, message: str, last_error: Optional[LLMError] = None):
        """
        :param message: 对失败的总体描述。
        :param last_error: 导致最终失败的最后一个标准化错误对象。
        """
        super().__init__(message)
        self.last_error = last_error

    def __str__(self):
        if self.last_error:
            return (
                f"{super().__str__()}\n"  # <--- super().__str__() 会返回我们传入的 message
                f"Last known error ({self.last_error.error_type.value}): {self.last_error.message}"
            )
        return super().__str__()
```

### core_llm/registry.py
```
# plugins/core_llm/registry.py

from typing import Dict, Type, Optional, Callable
from pydantic import BaseModel
from .providers.base import LLMProvider
import logging

logger = logging.getLogger(__name__)

class ProviderInfo(BaseModel):
    provider_class: Type[LLMProvider]
    key_env_var: str

class ProviderRegistry:
    """
    负责注册和查找 LLMProvider 实例及其元数据。
    """
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._provider_info: Dict[str, ProviderInfo] = {}

    def register(self, name: str, key_env_var: str) -> Callable[[Type[LLMProvider]], Type[LLMProvider]]:
        def decorator(provider_class: Type[LLMProvider]) -> Type[LLMProvider]:
            if name in self._provider_info:
                logger.warning(f"Overwriting LLM provider registration for '{name}'.")
            self._provider_info[name] = ProviderInfo(provider_class=provider_class, key_env_var=key_env_var)
            logger.info(f"LLM Provider '{name}' discovered (keys from '{key_env_var}').")
            return provider_class
        return decorator
    
    def get_provider_info(self, name: str) -> Optional[ProviderInfo]:
        return self._provider_info.get(name)

    def instantiate_all(self):
        """实例化所有已注册的 Provider。"""
        for name, info in self._provider_info.items():
            if name not in self._providers:
                self._providers[name] = info.provider_class()
    
    def get(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name)
    
    def get_all_provider_info(self) -> Dict[str, ProviderInfo]:
        return self._provider_info

provider_registry = ProviderRegistry()
```

### core_llm/__init__.py
```
# plugins/core_llm/__init__.py 

import logging
import os
import pkgutil 
import importlib
from typing import List

# 从平台核心导入接口和类型
from backend.core.contracts import Container, HookManager

# 导入本插件内部的组件
from .service import LLMService, MockLLMService
from .manager import KeyPoolManager, CredentialManager
from .registry import provider_registry
from .runtime import LLMRuntime
from .reporters import LLMProviderReporter

logger = logging.getLogger(__name__)

# --- 插件内部的辅助函数 ---
def _load_plugin_modules(directories: List[str]):
    """
    一个内聚于本插件的辅助函数，用于动态加载其子模块（如此处的 providers）。
    """
    logger.debug(f"Core-LLM: Dynamically loading sub-modules from: {directories}")
    for package_name in directories:
        try:
            package = importlib.import_module(package_name)
            
            for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
                try:
                    importlib.import_module(module_name)
                    logger.debug(f"  - Loaded sub-module: {module_name}")
                except Exception as e:
                    logger.error(f"  - Failed to load sub-module '{module_name}': {e}")
        except ImportError as e:
            logger.warning(f"Core-LLM: Could not import package '{package_name}'. Skipping. Error: {e}")


# --- 动态加载所有 provider ---
# 现在调用我们自己插件内部的辅助函数
_load_plugin_modules(["plugins.core_llm.providers"])


# --- 服务工厂 (Service Factories) ---
def _create_llm_service(container: Container) -> LLMService | MockLLMService:
    """这个工厂函数封装了创建 LLMService 的复杂逻辑。"""
    is_debug_mode = os.getenv("HEVNO_LLM_DEBUG_MODE", "false").lower() == "true"
    if is_debug_mode:
        logger.warning("LLM Gateway is in MOCK/DEBUG mode.")
        return MockLLMService()

    # 实例化所有已通过装饰器注册的 provider
    provider_registry.instantiate_all()
    
    cred_manager = CredentialManager()
    key_manager = KeyPoolManager(credential_manager=cred_manager)
    
    for name, info in provider_registry.get_all_provider_info().items():
        key_manager.register_provider(name, info.key_env_var)

    return LLMService(
        key_manager=key_manager,
        provider_registry=provider_registry,
        max_retries=3
    )

# --- 钩子实现 (Hook Implementations) ---
async def provide_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的 'llm.default' 运行时。"""
    if "llm.default" not in runtimes:
        runtimes["llm.default"] = LLMRuntime
        logger.debug("Provided 'llm.default' runtime to the engine.")
    return runtimes

async def provide_reporter(reporters: list) -> list:
    """钩子实现：向审计员提供本插件的报告器。"""
    reporters.append(LLMProviderReporter())
    logger.debug("Provided 'LLMProviderReporter' to the auditor.")
    return reporters

# --- 主注册函数 (Main Registration Function) ---
def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-llm 插件的注册入口，由平台加载器调用。"""
    logger.info("--> 正在注册 [core-llm] 插件...")

    # 1. 注册服务到 DI 容器
    #    'llm_service' 是单例，它的创建逻辑被封装在工厂函数中。
    container.register("llm_service", _create_llm_service)
    logger.debug("服务 'llm_service' 已注册。")

    # 2. 注册钩子实现
    #    通过 'collect_runtimes' 钩子，将我们的运行时提供给 core_engine。
    hook_manager.add_implementation(
        "collect_runtimes", 
        provide_runtime, 
        plugin_name="core-llm"
    )
    #    通过 'collect_reporters' 钩子，将我们的报告器提供给 core_api。
    hook_manager.add_implementation(
        "collect_reporters",
        provide_reporter,
        plugin_name="core-llm"
    )
    logger.debug("钩子实现 'collect_runtimes' 和 'collect_reporters' 已注册。")
    
    logger.info("插件 [core-llm] 注册成功。")
```

### core_llm/runtime.py
```
# plugins/core_llm/runtime.py

from typing import Dict, Any

from backend.core.contracts import ExecutionContext
from plugins.core_engine.interfaces import RuntimeInterface
from .models import LLMResponse, LLMRequestFailedError

# --- 核心修改: 移除 @runtime_registry 装饰器 ---
class LLMRuntime(RuntimeInterface):
    """
    一个轻量级的运行时，它通过 Hevno LLM Gateway 发起 LLM 调用。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        model_name = config.get("model")
        prompt = config.get("prompt")
        
        if not model_name:
            raise ValueError("LLMRuntime requires a 'model' field in its config (e.g., 'gemini/gemini-1.5-flash').")
        if not prompt:
            raise ValueError("LLMRuntime requires a 'prompt' field in its config.")

        llm_params = {k: v for k, v in config.items() if k not in ["model", "prompt"]}

        llm_service = context.shared.services.llm_service

        try:
            response: LLMResponse = await llm_service.request(
                model_name=model_name,
                prompt=prompt,
                **llm_params
            )
            
            if response.error_details:
                return {
                    "error": response.error_details.message,
                    "error_type": response.error_details.error_type.value,
                    "details": response.error_details.model_dump()
                }

            return {
                "llm_output": response.content,
                "usage": response.usage,
                "model_name": response.model_name
            }

        except LLMRequestFailedError as e:
            return {
                "error": str(e),
                "details": e.last_error.model_dump() if e.last_error else None
            }
```

### core_llm/manifest.json
```
{
    "name": "core-llm",
    "version": "1.0.0",
    "description": "Provides the LLM Gateway, including multi-provider support, key management, and retry logic.",
    "author": "Hevno Team",
    "priority": 20,
    "dependencies": ["core-engine"] 
}
```

### core_llm/reporters.py
```
# plugins/core_llm/reporters.py
from typing import Any
from backend.core.contracts import Reportable 
from .registry import provider_registry


class LLMProviderReporter(Reportable):
    
    @property
    def report_key(self) -> str:
        return "llm_providers"
    
    async def generate_report(self) -> Any:
        manifest = []
        all_info = provider_registry.get_all_provider_info()
        for name, info in all_info.items():
            provider_class = info.provider_class
            manifest.append({
                "name": name,
                # 同样，假设 LLMProvider 基类增加了 supported_models 属性
                "supported_models": getattr(provider_class, 'supported_models', [])
            })
        return sorted(manifest, key=lambda x: x['name'])
```

### core_llm/manager.py
```
# plugins/core_llm/manager.py

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, AsyncIterator


# --- Enums and Data Classes for Key State Management ---

class KeyStatus(str, Enum):
    """定义 API 密钥的健康状态。"""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    BANNED = "banned"


@dataclass
class KeyInfo:
    """存储单个 API 密钥及其状态信息。"""
    key_string: str
    status: KeyStatus = KeyStatus.AVAILABLE
    rate_limit_until: float = 0.0  # Unix timestamp until which the key is rate-limited

    def is_available(self) -> bool:
        """检查密钥当前是否可用。"""
        if self.status == KeyStatus.BANNED:
            return False
        if self.status == KeyStatus.RATE_LIMITED:
            if time.time() < self.rate_limit_until:
                return False
            # 如果限速时间已过，自动恢复为可用
            self.status = KeyStatus.AVAILABLE
            self.rate_limit_until = 0.0
        return self.status == KeyStatus.AVAILABLE


# --- Core Manager Components ---

class CredentialManager:
    """负责从环境变量中安全地加载和解析密钥。"""

    def load_keys_from_env(self, env_variable: str) -> List[str]:
        """
        从指定的环境变量中加载 API 密钥。
        密钥应以逗号分隔。

        :param env_variable: 环境变量的名称 (e.g., 'GEMINI_API_KEYS').
        :return: 一个包含 API 密钥字符串的列表。
        """
        keys_str = os.getenv(env_variable)
        if not keys_str:
            print(f"Warning: Environment variable '{env_variable}' not set. No keys loaded.")
            return []
        
        # 按逗号分割，并去除每个密钥前后的空白字符
        keys = [key.strip() for key in keys_str.split(',') if key.strip()]
        if not keys:
            print(f"Warning: Environment variable '{env_variable}' is set but contains no valid keys.")
        return keys


class ProviderKeyPool:
    """
    管理特定提供商（如 'gemini'）的一组 API 密钥。
    内置并发控制和密钥选择逻辑。
    """
    def __init__(self, provider_name: str, keys: List[str]):
        if not keys:
            raise ValueError(f"Cannot initialize ProviderKeyPool for '{provider_name}' with an empty key list.")
        
        self.provider_name = provider_name
        self._keys: List[KeyInfo] = [KeyInfo(key_string=k) for k in keys]
        
        # 使用 Semaphore 控制对该提供商的并发请求数量，初始值等于可用密钥数
        self._semaphore = asyncio.Semaphore(len(self._keys))

    def _get_next_available_key(self) -> Optional[KeyInfo]:
        """循环查找下一个可用的密钥。"""
        # 简单的轮询策略
        for key_info in self._keys:
            if key_info.is_available():
                return key_info
        return None

    @asynccontextmanager
    async def acquire_key(self) -> AsyncIterator[KeyInfo]:
        """
        一个安全的异步上下文管理器，用于获取和释放密钥。
        这是与该池交互的主要方式。

        :yields: 一个可用的 KeyInfo 对象。
        :raises asyncio.TimeoutError: 如果在指定时间内无法获取密钥。
        :raises RuntimeError: 如果池中已无任何可用密钥。
        """
        # 1. 获取信号量，这会阻塞直到有空闲的“插槽”
        await self._semaphore.acquire()

        try:
            # 2. 从池中选择一个当前可用的密钥
            key_info = self._get_next_available_key()
            if not key_info:
                # 这种情况理论上不应该发生，因为信号量应该反映可用密钥数
                # 但作为防御性编程，我们处理它
                raise RuntimeError(f"No available keys in pool '{self.provider_name}' despite acquiring semaphore.")
            
            # 3. 将密钥提供给调用者
            yield key_info
        finally:
            # 4. 无论发生什么，都释放信号量
            self._semaphore.release()

    def mark_as_rate_limited(self, key_string: str, duration_seconds: int = 60):
        """标记一个密钥为被限速状态。"""
        for key in self._keys:
            if key.key_string == key_string:
                key.status = KeyStatus.RATE_LIMITED
                key.rate_limit_until = time.time() + duration_seconds
                print(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' marked as rate-limited for {duration_seconds}s.")
                break

    async def mark_as_banned(self, key_string: str):
        """永久性地标记一个密钥为被禁用，并减少并发信号量。"""
        for key in self._keys:
            if key.key_string == key_string and key.status != KeyStatus.BANNED:
                key.status = KeyStatus.BANNED
                # 关键一步：永久性地减少一个并发“插槽”
                # 我们通过尝试获取然后不释放来实现
                # 注意：这假设信号量初始值与密钥数相同
                await self._semaphore.acquire()
                print(f"Key for '{self.provider_name}' ending with '...{key_string[-4:]}' permanently banned. Concurrency reduced.")
                break


class KeyPoolManager:
    """
    顶层管理器，聚合了所有提供商的密钥池。
    这是上层服务（LLMService）与之交互的唯一入口。
    """
    def __init__(self, credential_manager: CredentialManager):
        self._pools: Dict[str, ProviderKeyPool] = {}
        self._cred_manager = credential_manager

    def register_provider(self, provider_name: str, env_variable: str):
        """

        从环境变量加载密钥，并为提供商创建一个密钥池。
        :param provider_name: 提供商的名称 (e.g., 'gemini').
        :param env_variable: 包含该提供商密钥的环境变量。
        """
        keys = self._cred_manager.load_keys_from_env(env_variable)
        if keys:
            self._pools[provider_name] = ProviderKeyPool(provider_name, keys)
            print(f"Registered provider '{provider_name}' with {len(keys)} keys from '{env_variable}'.")

    def get_pool(self, provider_name: str) -> Optional[ProviderKeyPool]:
        """获取指定提供商的密钥池。"""
        return self._pools.get(provider_name)

    # 为了方便上层服务调用，我们将核心方法直接暴露在这里
    
    @asynccontextmanager
    async def acquire_key(self, provider_name: str) -> AsyncIterator[KeyInfo]:
        """
        从指定提供商的池中获取一个密钥。
        """
        pool = self.get_pool(provider_name)
        if not pool:
            raise ValueError(f"No key pool registered for provider '{provider_name}'.")
        
        async with pool.acquire_key() as key_info:
            yield key_info

    def mark_as_rate_limited(self, provider_name: str, key_string: str, duration_seconds: int = 60):
        pool = self.get_pool(provider_name)
        if pool:
            pool.mark_as_rate_limited(key_string, duration_seconds)

    async def mark_as_banned(self, provider_name: str, key_string: str):
        pool = self.get_pool(provider_name)
        if pool:
            await pool.mark_as_banned(key_string)
```

### core_memoria/tasks.py
```
# plugins/core_memoria/tasks.py
import logging
from typing import List, Dict, Any

from backend.core.contracts import (
    Container, 
    Sandbox, 
    StateSnapshot,
    SnapshotStoreInterface,
    BackgroundTaskManager
)
from .models import MemoryEntry, MemoryStream, Memoria, AutoSynthesisConfig
from plugins.core_llm.models import LLMResponse, LLMError, LLMResponseStatus,LLMRequestFailedError


logger = logging.getLogger(__name__)

async def run_synthesis_task(
    container: Container,
    sandbox_id: str,
    stream_name: str,
    synthesis_config: Dict[str, Any],
    entries_to_summarize_dicts: List[Dict[str, Any]]
):
    """
    一个后台任务，负责调用 LLM 生成总结，并创建一个新的状态快照。
    """
    logger.info(f"后台任务启动：为沙盒 {sandbox_id} 的流 '{stream_name}' 生成总结。")
    
    try:
        # --- 1. 解析服务和数据 ---
        llm_service: LLMService = container.resolve("llm_service")
        sandbox_store: Dict = container.resolve("sandbox_store")
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")

        config = AutoSynthesisConfig.model_validate(synthesis_config)
        entries_to_summarize = [MemoryEntry.model_validate(d) for d in entries_to_summarize_dicts]

        # --- 2. 调用 LLM ---
        events_text = "\n".join([f"- {entry.content}" for entry in entries_to_summarize])
        prompt = config.prompt.format(events_text=events_text)

        response: LLMResponse = await llm_service.request(model_name=config.model, prompt=prompt)

        if response.status != "success" or not response.content:
            logger.error(f"LLM 总结失败 for sandbox {sandbox_id}: {response.error_details.message if response.error_details else 'No content'}")
            return

        summary_content = response.content.strip()
        logger.info(f"LLM 成功生成总结 for sandbox {sandbox_id} a stream '{stream_name}'.")

        # --- 3. 更新世界状态（通过创建新快照）---
        # 这是关键部分，它以不可变的方式更新世界
        sandbox: Sandbox = sandbox_store.get(sandbox_id)
        if not sandbox or not sandbox.head_snapshot_id:
            logger.error(f"在后台任务中找不到沙盒 {sandbox_id} 或其头快照。")
            return

        head_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
        if not head_snapshot:
            logger.error(f"数据不一致：找不到沙盒 {sandbox_id} 的头快照 {sandbox.head_snapshot_id}。")
            return
        
        # 创建一个新的、可变的 world_state 副本
        new_world_state = head_snapshot.world_state.copy()
        memoria_data = new_world_state.get("memoria", {})
        
        memoria = Memoria.model_validate(memoria_data)
        stream = memoria.get_stream(stream_name)
        if not stream:
            # 这理论上不应该发生，因为触发任务时流必然存在
            logger.warning(f"在后台任务中，流 '{stream_name}' 在 world.memoria 中消失了。")
            return

        stream.synthesis_trigger_counter = 0

        # 创建并添加新的总结条目
        summary_entry = MemoryEntry(
            sequence_id=memoria.get_next_sequence_id(),
            level=config.level,
            tags=["synthesis", "auto-generated"],
            content=summary_content
        )
        stream.entries.append(summary_entry)
        memoria.set_stream(stream_name, stream)

        # 创建一个全新的快照
        new_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            graph_collection=head_snapshot.graph_collection,
            world_state=memoria.model_dump(),
            parent_snapshot_id=head_snapshot.id,
            triggering_input={"_system_event": "memoria_synthesis", "stream": stream_name}
        )
        
        # 保存新快照并更新沙盒的头指针
        snapshot_store.save(new_snapshot)
        sandbox.head_snapshot_id = new_snapshot.id
        logger.info(f"为沙盒 {sandbox_id} 创建了新的头快照 {new_snapshot.id}，包含新总结。")

    except LLMRequestFailedError as e:
        logger.error(f"后台 LLM 请求在多次重试后失败: {e}", exc_info=False)
    except Exception as e:
        logger.exception(f"在执行 memoria 综合任务时发生未预料的错误: {e}")
```

### core_memoria/models.py
```
# plugins/core_memoria/models.py
from __future__ import annotations
import logging
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, RootModel, ConfigDict

logger = logging.getLogger(__name__)

# --- Core Data Models for Memoria Structure ---

class MemoryEntry(BaseModel):
    """一个单独的、结构化的记忆条目。"""
    id: UUID = Field(default_factory=uuid4)
    sequence_id: int = Field(..., description="在所有流中唯一的、单调递增的因果序列号。")
    level: str = Field(default="event", description="记忆的层级，如 'event', 'summary', 'milestone'。")
    tags: List[str] = Field(default_factory=list, description="用于快速过滤和检索的标签。")
    content: str = Field(..., description="记忆条目的文本内容。")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AutoSynthesisConfig(BaseModel):
    """自动综合（大总结）的行为配置。"""
    enabled: bool = Field(default=False)
    trigger_count: int = Field(default=10, gt=0, description="触发综合所需的条目数量。")
    level: str = Field(default="summary", description="综合后产生的新条目的层级。")
    model: str = Field(default="gemini/gemini-1.5-flash", description="用于执行综合的 LLM 模型。")
    prompt: str = Field(
        default="The following is a series of events. Please provide a concise summary.\n\nEvents:\n{events_text}",
        description="用于综合的 LLM 提示模板。必须包含 '{events_text}' 占位符。"
    )


class MemoryStreamConfig(BaseModel):
    """每个记忆流的独立配置。"""
    auto_synthesis: AutoSynthesisConfig = Field(default_factory=AutoSynthesisConfig)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryStream(BaseModel):
    """一个独立的记忆回廊，包含它自己的配置和条目列表。"""
    config: MemoryStreamConfig = Field(default_factory=MemoryStreamConfig)
    entries: List[MemoryEntry] = Field(default_factory=list)
    
    synthesis_trigger_counter: int = Field(
        default=0, 
        description="Internal counter for auto-synthesis trigger. This is part of the persisted state."
    )
class Memoria(RootModel[Dict[str, Any]]):
    """
    代表 world.memoria 的顶层结构。
    它是一个字典，键是流名称，值是 MemoryStream 对象。
    还包含一个全局序列号，以确保因果关系的唯一性。
    """
    root: Dict[str, Any] = Field(default_factory=lambda: {"__global_sequence__": 0})
    
    def get_stream(self, stream_name: str) -> Optional[MemoryStream]:
        """安全地获取一个 MemoryStream 的 Pydantic 模型实例。"""
        stream_data = self.root.get(stream_name)
        if isinstance(stream_data, dict):
            return MemoryStream.model_validate(stream_data)
        return None

    def set_stream(self, stream_name: str, stream_model: MemoryStream):
        """将一个 MemoryStream 模型实例写回到根字典中。"""
        self.root[stream_name] = stream_model.model_dump(exclude_defaults=True)

    def get_next_sequence_id(self) -> int:
        """获取并递增全局序列号，确保原子性。"""
        current_seq = self.root.get("__global_sequence__", 0)
        next_seq = current_seq + 1
        self.root["__global_sequence__"] = next_seq
        return next_seq
```

### core_memoria/runtimes.py
```
# plugins/core_memoria/runtimes.py

import logging
from typing import Dict, Any, List

from backend.core.contracts import ExecutionContext, BackgroundTaskManager
from plugins.core_engine.interfaces import RuntimeInterface

from .models import Memoria, MemoryEntry
from .tasks import run_synthesis_task

logger = logging.getLogger(__name__)


class MemoriaAddRuntime(RuntimeInterface):
    """
    向指定的记忆流中添加一条新的记忆条目。
    如果满足条件，会自动触发一个后台任务来执行记忆综合。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        stream_name = config.get("stream")
        content = config.get("content")
        if not stream_name or not content:
            raise ValueError("MemoriaAddRuntime requires 'stream' and 'content' in its config.")
        
        level = config.get("level", "event")
        tags = config.get("tags", [])
        
        memoria_data = context.shared.world_state.setdefault("memoria", {"__global_sequence__": 0})
        memoria = Memoria.model_validate(memoria_data)
        
        # 获取或创建流
        stream = memoria.get_stream(stream_name)
        if stream is None:
            from .models import MemoryStream
            stream = MemoryStream()

        # 创建新条目
        new_entry = MemoryEntry(
            sequence_id=memoria.get_next_sequence_id(),
            level=level,
            tags=tags,
            content=str(content)
        )
        stream.entries.append(new_entry)
        
        # 【修复】使用新的公共字段名
        stream.synthesis_trigger_counter += 1
        
        # 将更新后的流写回
        memoria.set_stream(stream_name, stream)
        context.shared.world_state["memoria"] = memoria.model_dump()
        
        # 检查是否需要触发后台综合任务
        synth_config = stream.config.auto_synthesis
        # 【修复】使用新的公共字段名
        if synth_config.enabled and stream.synthesis_trigger_counter >= synth_config.trigger_count:
            logger.info(f"流 '{stream_name}' 满足综合条件，正在提交后台任务。")
            
            task_manager: BackgroundTaskManager = context.shared.services.task_manager
            
            entries_to_summarize = stream.entries[-synth_config.trigger_count:]
            
            task_manager.submit_task(
                run_synthesis_task,
                sandbox_id=context.initial_snapshot.sandbox_id,
                stream_name=stream_name,
                synthesis_config=synth_config.model_dump(),
                entries_to_summarize_dicts=[e.model_dump() for e in entries_to_summarize]
            )
            memoria.set_stream(stream_name, stream)
            context.shared.world_state["memoria"] = memoria.model_dump()

        return {"output": new_entry.model_dump()}


class MemoriaQueryRuntime(RuntimeInterface):
    """
    根据声明式条件从一个记忆流中检索条目。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        stream_name = config.get("stream")
        if not stream_name:
            raise ValueError("MemoriaQueryRuntime requires a 'stream' name in its config.")

        memoria_data = context.shared.world_state.get("memoria", {})
        memoria = Memoria.model_validate(memoria_data)
        stream = memoria.get_stream(stream_name)
        
        if not stream:
            return {"output": []} # 如果流不存在，返回空列表

        # --- 过滤逻辑 ---
        results = stream.entries
        
        # 按 levels 过滤
        levels_to_get = config.get("levels")
        if isinstance(levels_to_get, list):
            results = [entry for entry in results if entry.level in levels_to_get]

        # 按 tags 过滤
        tags_to_get = config.get("tags")
        if isinstance(tags_to_get, list):
            tags_set = set(tags_to_get)
            results = [entry for entry in results if tags_set.intersection(entry.tags)]

        # 获取最新的 N 条
        latest_n = config.get("latest")
        if isinstance(latest_n, int):
            # 先按 sequence_id 排序确保顺序正确
            results.sort(key=lambda e: e.sequence_id)
            results = results[-latest_n:]
            
        # 按顺序返回
        order = config.get("order", "ascending")
        reverse = (order == "descending")
        results.sort(key=lambda e: e.sequence_id, reverse=reverse)

        return {"output": [entry.model_dump() for entry in results]}


class MemoriaAggregateRuntime(RuntimeInterface):
    """
    将一批记忆条目（通常来自 query 的输出）聚合成一段格式化的文本。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        entries_data = config.get("entries")
        template = config.get("template", "{content}")
        joiner = config.get("joiner", "\n\n")

        if not isinstance(entries_data, list):
            raise TypeError("MemoriaAggregateRuntime 'entries' field must be a list of memory entry objects.")
        
        formatted_parts = []
        for entry_dict in entries_data:
            # 简单的模板替换
            part = template.format(
                id=entry_dict.get('id', ''),
                sequence_id=entry_dict.get('sequence_id', ''),
                level=entry_dict.get('level', ''),
                tags=', '.join(entry_dict.get('tags', [])),
                content=entry_dict.get('content', '')
            )
            formatted_parts.append(part)
        
        return {"output": joiner.join(formatted_parts)}
```

### core_memoria/__init__.py
```
# plugins/core_memoria/__init__.py

import logging
from backend.core.contracts import Container, HookManager

from .runtimes import MemoriaAddRuntime, MemoriaQueryRuntime, MemoriaAggregateRuntime

logger = logging.getLogger(__name__)

# --- 钩子实现 (Hook Implementation) ---
async def provide_memoria_runtimes(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的所有运行时。"""
    
    memoria_runtimes = {
        "memoria.add": MemoriaAddRuntime,
        "memoria.query": MemoriaQueryRuntime,
        "memoria.aggregate": MemoriaAggregateRuntime,
    }
    
    for name, runtime_class in memoria_runtimes.items():
        if name not in runtimes:
            runtimes[name] = runtime_class
            logger.debug(f"Provided '{name}' runtime to the engine.")
            
    return runtimes

# --- 主注册函数 (Main Registration Function) ---
def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-memoria 插件的注册入口，由平台加载器调用。"""
    logger.info("--> 正在注册 [core-memoria] 插件...")

    # 本插件只提供运行时，它通过钩子与 core-engine 通信。
    hook_manager.add_implementation(
        "collect_runtimes", 
        provide_memoria_runtimes, 
        plugin_name="core-memoria"
    )
    logger.debug("钩子实现 'collect_runtimes' 已注册。")

    logger.info("插件 [core-memoria] 注册成功。")
```

### core_memoria/manifest.json
```
{
    "name": "core-memoria",
    "version": "1.0.0",
    "description": "Provides a dynamic memory system for storing, synthesizing, and querying events, enabling short-term memory and long-term reflection for AI agents.",
    "author": "Hevno Team",
    "priority": 40,
    "dependencies": ["core-engine", "core-llm"]
}
```

### core_api/__init__.py
```
# plugins/core_api/__init__.py

import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager, Reportable
from .auditor import Auditor
from .base_router import router as base_router
from .sandbox_router import router as sandbox_router

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_auditor() -> Auditor:
    """工厂：只创建 Auditor 的空实例。它的内容将在之后被异步填充。"""
    return Auditor([])

# --- 钩子实现 ---
async def populate_auditor(container: Container):
    """钩子实现：监听启动事件，异步地收集报告器并填充 Auditor。"""
    logger.debug("Async task: Populating auditor with reporters...")
    hook_manager = container.resolve("hook_manager")
    auditor: Auditor = container.resolve("auditor")
    
    reporters_list: List[Reportable] = await hook_manager.filter("collect_reporters", [])
    
    auditor.set_reporters(reporters_list)
    logger.info(f"Auditor populated with {len(reporters_list)} reporter(s).")

async def provide_own_routers(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的路由添加到收集中。"""
    routers.append(base_router)
    routers.append(sandbox_router)
    logger.debug("Provided own routers (base, sandbox) to the application.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-api] 插件...")

    # 1. 注册服务（仅创建空实例）
    container.register("auditor", _create_auditor, singleton=True)
    logger.debug("服务 'auditor' 已注册 (initially empty)。")

    # 2. 注册异步填充钩子
    hook_manager.add_implementation(
        "services_post_register",
        populate_auditor,
        plugin_name="core-api"
    )

    # 3. 【关键】注册路由【提供者】钩子
    #    它现在和其他插件一样，只是一个提供者。
    hook_manager.add_implementation(
        "collect_api_routers", 
        provide_own_routers, 
        priority=100, # 较高的 priority 意味着后执行
        plugin_name="core-api"
    )
    logger.debug("钩子实现 'collect_api_routers' 和 'services_post_register' 已注册。")

    logger.info("插件 [core-api] 注册成功。")
```

### core_api/sandbox_router.py
```
# plugins/core_api/sandbox_router.py

import io
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

# 从平台核心契约导入数据模型和接口
from backend.core.contracts import (
    Sandbox, 
    StateSnapshot, 
    GraphCollection,
    ExecutionEngineInterface,
    SnapshotStoreInterface
)

# 从本插件的依赖注入文件中导入 "getters"
from .dependencies import get_sandbox_store, get_snapshot_store, get_engine

# 【关键】从依赖插件 core_persistence 导入其服务和模型
from plugins.core_persistence.service import PersistenceService
from plugins.core_persistence.models import PackageManifest, PackageType
from plugins.core_persistence.dependencies import get_persistence_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sandboxes", 
    tags=["Sandboxes"]
)

# --- Request/Response Models ---

class CreateSandboxRequest(BaseModel):
    name: str = Field(..., description="The human-readable name for the sandbox.")
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = Field(default_factory=dict)

# --- Sandbox Lifecycle API ---

@router.post("", response_model=Sandbox, status_code=201, summary="Create a new Sandbox")
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
):
    """
    创建一个新的沙盒，并为其生成一个初始（创世）快照。
    这是与一个新世界交互的起点。
    """
    sandbox = Sandbox(name=request_body.name)
    if sandbox.id in sandbox_store:
        raise HTTPException(status_code=409, detail=f"Sandbox with ID {sandbox.id} already exists.")
    
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request_body.graph_collection,
        world_state=request_body.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    
    logger.info(f"Created new sandbox '{sandbox.name}' ({sandbox.id}).")
    return sandbox

@router.post("/{sandbox_id}/step", response_model=StateSnapshot, summary="Execute a step")
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store),
    engine: ExecutionEngineInterface = Depends(get_engine)
):
    """在沙盒的最新状态上执行一步计算，生成一个新的状态快照。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    if not sandbox.head_snapshot_id:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state to step from.")
        
    latest_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
    if not latest_snapshot:
        logger.error(f"Data inconsistency for sandbox {sandbox_id}: head snapshot '{sandbox.head_snapshot_id}' not found.")
        raise HTTPException(status_code=500, detail=f"Data inconsistency: head snapshot not found.")
    
    new_snapshot = await engine.step(latest_snapshot, user_input)
    
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    
    return new_snapshot

@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot], summary="Get history")
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
):
    """获取一个沙盒的所有历史快照，按时间顺序排列。"""
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
        
    # 如果存在，则继续执行原逻辑
    return snapshot_store.find_by_sandbox(sandbox_id)

@router.put("/{sandbox_id}/revert", status_code=200, summary="Revert to a snapshot")
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
):
    """将沙盒的状态回滚到指定的历史快照。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    target_snapshot = snapshot_store.get(snapshot_id)
    if not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Target snapshot not found or does not belong to this sandbox.")
    
    sandbox.head_snapshot_id = snapshot_id
    logger.info(f"Reverted sandbox '{sandbox.name}' ({sandbox.id}) to snapshot {snapshot_id}.")
    return {"message": f"Sandbox '{sandbox.name}' successfully reverted to snapshot {snapshot_id}"}


# --- Sandbox Import/Export API ---

@router.get("/{sandbox_id}/export", response_class=StreamingResponse, summary="Export a Sandbox")
async def export_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store),
    persistence_service: PersistenceService = Depends(get_persistence_service)
):
    """将一个沙盒及其完整历史导出为一个 .hevno.zip 包文件。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    # 1. 准备清单和数据文件
    manifest = PackageManifest(
        package_type=PackageType.SANDBOX_ARCHIVE,
        entry_point="sandbox.json",
        metadata={"sandbox_name": sandbox.name}
    )
    data_files: Dict[str, BaseModel] = {"sandbox.json": sandbox}
    for snap in snapshots:
        data_files[f"snapshots/{snap.id}.json"] = snap

    # 2. 调用 persistence_service 进行打包
    try:
        zip_bytes = persistence_service.export_package(manifest, data_files)
    except Exception as e:
        logger.error(f"Failed to create package for sandbox {sandbox_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create package: {e}")

    # 3. 返回文件流
    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox.id}.hevno.zip"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/import", response_model=Sandbox, summary="Import a Sandbox")
async def import_sandbox(
    file: UploadFile = File(..., description="A .hevno.zip package file."),
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store),
    persistence_service: PersistenceService = Depends(get_persistence_service)
) -> Sandbox:
    """从一个 .hevno.zip 文件导入一个沙盒及其完整历史。"""
    if not file.filename or not file.filename.endswith(".hevno.zip"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .hevno.zip file.")

    zip_bytes = await file.read()
    
    # 1. 调用 persistence_service 解包
    try:
        manifest, data_files = persistence_service.import_package(zip_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid package: {e}")

    if manifest.package_type != PackageType.SANDBOX_ARCHIVE:
        raise HTTPException(status_code=400, detail=f"Invalid package type. Expected '{PackageType.SANDBOX_ARCHIVE.value}'.")
    
    # 【未来扩展】在这里可以检查 manifest.required_plugins

    # 2. 处理解包后的数据
    try:
        sandbox_data_str = data_files.get(manifest.entry_point)
        if not sandbox_data_str:
            raise ValueError(f"Entry point file '{manifest.entry_point}' not found in package.")
        
        # 恢复沙盒对象
        new_sandbox = Sandbox.model_validate_json(sandbox_data_str)
        if new_sandbox.id in sandbox_store:
            raise HTTPException(status_code=409, detail=f"Conflict: A sandbox with ID '{new_sandbox.id}' already exists.")

        # 恢复所有快照对象
        recovered_snapshots = []
        for filename, content_str in data_files.items():
            if filename.startswith("snapshots/"):
                snapshot = StateSnapshot.model_validate_json(content_str)
                if snapshot.sandbox_id != new_sandbox.id:
                    raise ValueError(f"Snapshot {snapshot.id} does not belong to the imported sandbox {new_sandbox.id}.")
                recovered_snapshots.append(snapshot)
        
        if not recovered_snapshots:
            raise ValueError("No snapshots found in the package.")

        # 3. 如果所有数据都有效，则原子性地保存到存储中
        for snapshot in recovered_snapshots:
            snapshot_store.save(snapshot)
        sandbox_store[new_sandbox.id] = new_sandbox
        
        logger.info(f"Successfully imported sandbox '{new_sandbox.name}' ({new_sandbox.id}).")
        return new_sandbox

    except (ValidationError, ValueError) as e:
        logger.warning(f"Failed to process package data for file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process package data: {str(e)}")
```

### core_api/manifest.json
```
{
    "name": "core-api",
    "version": "1.0.0",
    "description": "Provides the core RESTful API endpoints and the system reporting auditor.",
    "author": "Hevno Team",
    "priority": 100
}
```

### core_api/auditor.py
```
# plugins/core_api/auditor.py

import asyncio
from backend.core.contracts import Reportable
from typing import Any, Dict, List


class Auditor:
    """
    审阅官服务。负责从注册的 Reportable 实例中收集报告并聚合。
    """
    def __init__(self, reporters: List[Reportable]):
        self._reporters = reporters
        self._static_report_cache: Dict[str, Any] | None = None

    def set_reporters(self, reporters: List[Reportable]):
        """允许在创建后设置/替换报告器列表。"""
        self._reporters = reporters
        self._static_report_cache = None

    async def generate_full_report(self) -> Dict[str, Any]:
        """生成完整的系统报告。"""
        full_report = {}

        # 1. 处理静态报告 (带缓存)
        if self._static_report_cache is None:
            self._static_report_cache = await self._generate_static_reports()
        full_report.update(self._static_report_cache)

        # 2. 处理动态报告 (实时生成)
        dynamic_reports = await self._generate_dynamic_reports()
        full_report.update(dynamic_reports)

        return full_report

    async def _generate_reports_by_type(self, static: bool) -> Dict[str, Any]:
        """根据报告类型（静态/动态）生成报告。"""
        reports = {}
        reportables_to_run = [r for r in self._reporters if r.is_static is static]
        if not reportables_to_run:
            return {}

        tasks = [r.generate_report() for r in reportables_to_run]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r, result in zip(reportables_to_run, results):
            if isinstance(result, Exception):
                reports[r.report_key] = {"error": f"Failed to generate report: {result}"}
            else:
                reports[r.report_key] = result
        return reports

    async def _generate_static_reports(self) -> Dict[str, Any]:
        return await self._generate_reports_by_type(static=True)

    async def _generate_dynamic_reports(self) -> Dict[str, Any]:
        return await self._generate_reports_by_type(static=False)
```

### core_api/base_router.py
```
# plugins/core_api/base_router.py

from fastapi import APIRouter, Depends
from .dependencies import get_auditor
from .auditor import Auditor

router = APIRouter(prefix="/api", tags=["System"])

@router.get("/system/report")
async def get_system_report(auditor: Auditor = Depends(get_auditor)):
    """获取完整的系统状态和元数据报告。"""
    return await auditor.generate_full_report()
```

### core_api/dependencies.py
```
# plugins/core_api/dependencies.py

from typing import Dict, Any, List
from uuid import UUID
from fastapi import Request

# 只从 backend.core.contracts 导入数据模型和接口
from backend.core.contracts import (
    Sandbox, 
    StateSnapshot,
    ExecutionEngineInterface, 
    SnapshotStoreInterface,
    AuditorInterface
)

# 每个依赖注入函数现在只做一件事：从容器中解析服务。
# 类型提示使用我们新定义的接口。

def get_engine(request: Request) -> ExecutionEngineInterface:
    return request.app.state.container.resolve("execution_engine")

def get_snapshot_store(request: Request) -> SnapshotStoreInterface:
    return request.app.state.container.resolve("snapshot_store")

def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    # 对于简单的字典存储，可以直接用 Dict
    return request.app.state.container.resolve("sandbox_store")

def get_auditor(request: Request) -> AuditorInterface:
    return request.app.state.container.resolve("auditor")
```

### core_logging/logging_config.yaml
```
version: 1

disable_existing_loggers: false

# 定义格式化器
formatters:
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  detailed:
    format: '[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s'

# 定义处理器 (输出到哪里)
handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: simple
    stream: ext://sys.stdout

#   file:
#     class: logging.handlers.RotatingFileHandler
#     level: DEBUG
#     formatter: detailed
#     filename: app.log
#     maxBytes: 10485760 # 10MB
#     backupCount: 5
#     encoding: utf8

# 根日志记录器配置
root:
  level: INFO # 默认级别
  handlers: [console] #, file] # 默认使用控制台处理器

# 可以为特定模块设置不同级别
loggers:
  uvicorn:
    level: INFO
  fastapi:
    level: INFO
```

### core_logging/__init__.py
```
# plugins/core_logging/__init__.py
import os
import yaml
import logging
import logging.config
from pathlib import Path

from backend.core.contracts import Container, HookManager

PLUGIN_DIR = Path(__file__).parent

def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-logging 插件的注册入口。"""
    # 统一的入口消息
    print("--> 正在注册 [core-logging] 插件...")
    
    config_path = PLUGIN_DIR / "logging_config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        logging_config = yaml.safe_load(f)
    
    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level and env_log_level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level_override = env_log_level.upper()
        logging_config['root']['level'] = log_level_override

    logging.config.dictConfig(logging_config)
    
    logger = logging.getLogger(__name__)
    
    # 统一的成功消息
    logger.info("插件 [core-logging] 注册成功。")
```

### core_logging/manifest.json
```
{
    "name": "core-logging",
    "version": "1.0.0",
    "description": "Provides centralized, configurable logging for the Hevno platform.",
    "author": "Hevno Team",
    "priority": -100
}
```

### core_persistence/service.py
```
# plugins/core_persistence/service.py

import io
import json
import zipfile
import logging
from pathlib import Path
from typing import Type, TypeVar, Tuple, Dict, Any, List
from pydantic import BaseModel, ValidationError

from .models import PackageManifest, AssetType, FILE_EXTENSIONS

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class PersistenceService:
    """
    处理所有文件系统和包导入/导出操作的核心服务。
    """
    def __init__(self, assets_base_dir: str):
        self.assets_base_dir = Path(assets_base_dir)
        self.assets_base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PersistenceService initialized. Assets directory: {self.assets_base_dir.resolve()}")

    def _get_asset_path(self, asset_type: AssetType, asset_name: str) -> Path:
        """根据资产类型和名称构造标准化的文件路径。"""
        extension = FILE_EXTENSIONS[asset_type]
        # 简单的安全措施，防止路径遍历
        safe_name = Path(asset_name).name 
        return self.assets_base_dir / asset_type.value / f"{safe_name}{extension}"

    def save_asset(self, asset_model: T, asset_type: AssetType, asset_name: str) -> Path:
        """将 Pydantic 模型保存为格式化的 JSON 文件。"""
        file_path = self._get_asset_path(asset_type, asset_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        json_content = asset_model.model_dump_json(indent=2)
        file_path.write_text(json_content, encoding='utf-8')
        return file_path

    def load_asset(self, asset_type: AssetType, asset_name: str, model_class: Type[T]) -> T:
        """从文件加载并验证 Pydantic 模型。"""
        file_path = self._get_asset_path(asset_type, asset_name)
        if not file_path.exists():
            raise FileNotFoundError(f"Asset '{asset_name}' of type '{asset_type.value}' not found.")
        
        json_content = file_path.read_text(encoding='utf-8')
        try:
            return model_class.model_validate_json(json_content)
        except ValidationError as e:
            raise ValueError(f"Failed to validate asset '{asset_name}': {e}") from e

    def list_assets(self, asset_type: AssetType) -> List[str]:
        """列出指定类型的所有资产名称。"""
        asset_dir = self.assets_base_dir / asset_type.value
        if not asset_dir.exists():
            return []
        
        extension = FILE_EXTENSIONS[asset_type]
        
        asset_names = [
            p.name.removesuffix(extension) 
            for p in asset_dir.glob(f"*{extension}")
        ]
        return sorted(asset_names)

    def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel]) -> bytes:
        """在内存中创建一个 .hevno.zip 包并返回其字节流。"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', manifest.model_dump_json(indent=2))
            for filename, model_instance in data_files.items():
                file_content = model_instance.model_dump_json(indent=2)
                zf.writestr(f'data/{filename}', file_content)
        
        return zip_buffer.getvalue()

    def import_package(self, zip_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str]]:
        """解压包，读取清单和所有数据文件（作为原始字符串）。"""
        zip_buffer = io.BytesIO(zip_bytes)
        data_files: Dict[str, str] = {}
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            try:
                manifest_content = zf.read('manifest.json').decode('utf-8')
                manifest = PackageManifest.model_validate_json(manifest_content)
            except KeyError:
                raise ValueError("Package is missing 'manifest.json'.")
            except (ValidationError, json.JSONDecodeError) as e:
                raise ValueError(f"Invalid 'manifest.json': {e}") from e

            for item in zf.infolist():
                if item.filename.startswith('data/') and not item.is_dir():
                    relative_path = item.filename.split('data/', 1)[1]
                    data_files[relative_path] = zf.read(item).decode('utf-8')
        
        return manifest, data_files
```

### core_persistence/models.py
```
# plugins/core_persistence/models.py

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# --- 文件约定 ---
class AssetType(str, Enum):
    GRAPH = "graph"
    CODEX = "codex"
    SANDBOX = "sandbox"

FILE_EXTENSIONS = {
    AssetType.GRAPH: ".graph.hevno.json",
    AssetType.CODEX: ".codex.hevno.json",
}

# --- 插件占位符模型 ---
class PluginRequirement(BaseModel):
    name: str = Field(..., description="Plugin identifier, e.g., 'hevno-dice-roller'")
    source_url: str = Field(..., description="Plugin source, e.g., 'https://github.com/user/repo'")
    version: str = Field(..., description="Compatible version or Git ref")

# --- 包清单模型 ---
class PackageType(str, Enum):
    SANDBOX_ARCHIVE = "sandbox_archive"
    GRAPH_COLLECTION = "graph_collection"
    CODEX_COLLECTION = "codex_collection"

class PackageManifest(BaseModel):
    format_version: str = Field(default="1.0")
    package_type: PackageType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_point: str
    required_plugins: List[PluginRequirement] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### core_persistence/__init__.py
```
# plugins/core_persistence/__init__.py
import os
import logging

from backend.core.contracts import Container, HookManager
from .service import PersistenceService
from .api import router as persistence_router

logger = logging.getLogger(__name__)

def _create_persistence_service() -> PersistenceService:
    """服务工厂：创建 PersistenceService 实例。"""
    assets_dir = os.getenv("HEVNO_ASSETS_DIR", "assets")
    return PersistenceService(assets_base_dir=assets_dir)

async def provide_router(routers: list) -> list:
    """钩子实现：提供本插件的 API 路由。"""
    routers.append(persistence_router)
    return routers

def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core_persistence 插件的注册入口。"""
    # 统一的入口消息
    logger.info("--> 正在注册 [core-persistence] 插件...")
    
    # 注册服务
    container.register("persistence_service", _create_persistence_service)
    logger.debug("服务 'persistence_service' 已注册。")
    
    # 注册钩子
    hook_manager.add_implementation("collect_api_routers", provide_router, plugin_name="core_persistence")
    logger.debug("钩子实现 'collect_api_routers' 已注册。")
    
    # 统一的成功消息
    logger.info("插件 [core-persistence] 注册成功。")
```

### core_persistence/api.py
```
# plugins/core_persistence/api.py

import logging
from typing import List
from fastapi import APIRouter, Depends

# 从本插件内部导入所需的组件
from .service import PersistenceService
from .models import AssetType
from .dependencies import get_persistence_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/persistence", 
    tags=["Core-Persistence"]
)

@router.get("/assets/{asset_type}", response_model=List[str])
async def list_assets_by_type(
    asset_type: AssetType,
    service: PersistenceService = Depends(get_persistence_service)
):
    """
    列出指定类型的所有已保存资产的名称。
    例如，要列出所有图，可以请求 GET /api/persistence/assets/graph
    """
    try:
        return service.list_assets(asset_type)
    except Exception as e:
        logger.error(f"Failed to list assets of type '{asset_type.value}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while listing assets.")

# 注意：通用的 /package/import 端点被移除了，因为导入总是与特定资源（如沙盒）相关。
# 直接在特定资源的 API 中处理导入逻辑更符合 RESTful 原则。
```

### core_persistence/manifest.json
```
{
    "name": "core-persistence",
    "version": "1.0.0",
    "description": "Provides file system persistence, asset management, and package import/export.",
    "author": "Hevno Team",
    "priority": 10
}
```

### core_persistence/dependencies.py
```
# plugins/core_persistence/dependencies.py (新文件)

from fastapi import Request
from .service import PersistenceService

def get_persistence_service(request: Request) -> PersistenceService:
    """FastAPI 依赖注入函数，用于从容器中获取 PersistenceService。"""
    return request.app.state.container.resolve("persistence_service")
```

### core_codex/invoke_runtime.py
```
# plugins/core_codex/invoke_runtime.py

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Set

from pydantic import ValidationError

# 从 core_engine 插件导入接口和组件
from plugins.core_engine.interfaces import RuntimeInterface
from plugins.core_engine.evaluation import evaluate_data, build_evaluation_context
from plugins.core_engine.utils import DotAccessibleDict

# 从平台核心导入数据契约
from backend.core.contracts import ExecutionContext

# 从本插件内部导入模型
from .models import CodexCollection, ActivatedEntry, TriggerMode

logger = logging.getLogger(__name__)


class InvokeRuntime(RuntimeInterface):
    """
    codex.invoke 运行时的实现。
    """
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs
    ) -> Dict[str, Any]:
        # --- 0. 准备工作 ---
        from_sources = config.get("from", [])
        if not from_sources:
            return {"output": ""}

        recursion_enabled = config.get("recursion_enabled", False)
        debug_mode = config.get("debug", False)
        lock = context.shared.global_write_lock

        codices_data = context.shared.world_state.get("codices", {})
        try:
            codex_collection = CodexCollection.model_validate(codices_data).root
        except ValidationError as e:
            raise ValueError(f"Invalid codex structure in world.codices: {e}")

        # --- 1. 阶段一：选择与过滤 (Structural Evaluation) ---
        initial_pool: List[ActivatedEntry] = []
        rejected_entries_trace = []
        initial_activation_trace = []
        
        # 宏求值的上下文只需要创建一次
        structural_eval_context = build_evaluation_context(context)

        for source_config in from_sources:
            codex_name = source_config.get("codex")
            if not codex_name: 
                continue
            
            codex_model = codex_collection.get(codex_name)
            if not codex_model:
                logger.warning(f"Codex '{codex_name}' referenced in invoke config not found in world.codices.")
                continue

            source_text_macro = source_config.get("source", "")
            source_text = await evaluate_data(source_text_macro, structural_eval_context, lock) if source_text_macro else ""

            for entry in codex_model.entries:
                is_enabled = await evaluate_data(entry.is_enabled, structural_eval_context, lock)
                if not is_enabled:
                    if debug_mode:
                        rejected_entries_trace.append({"id": entry.id, "reason": "is_enabled macro returned false"})
                    continue

                keywords = await evaluate_data(entry.keywords, structural_eval_context, lock)
                priority = await evaluate_data(entry.priority, structural_eval_context, lock)

                matched_keywords = []
                is_activated = False
                if entry.trigger_mode == TriggerMode.ALWAYS_ON:
                    is_activated = True
                elif entry.trigger_mode == TriggerMode.ON_KEYWORD and source_text and keywords:
                    for keyword in keywords:
                        # 确保 keyword 是字符串以进行正则匹配
                        if re.search(re.escape(str(keyword)), str(source_text), re.IGNORECASE):
                            matched_keywords.append(keyword)
                    if matched_keywords:
                        is_activated = True
                
                if is_activated:
                    activated = ActivatedEntry(
                        entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                        priority_val=int(priority), keywords_val=keywords, is_enabled_val=bool(is_enabled),
                        source_text=str(source_text), matched_keywords=matched_keywords
                    )
                    initial_pool.append(activated)
                    if debug_mode:
                        initial_activation_trace.append({
                            "id": entry.id, "priority": int(priority),
                            "reason": entry.trigger_mode.value,
                            "matched_keywords": matched_keywords
                        })
        
        # --- 2. 阶段二：渲染与注入 (Content Evaluation) ---
        final_text_parts = []
        rendered_entry_ids: Set[str] = set()
        rendering_pool = sorted(initial_pool, key=lambda x: x.priority_val, reverse=True)
        
        # Debugging trace lists
        evaluation_log = []
        recursive_activations = []

        # 确定最大递归深度
        max_depth = max((act.codex_config.recursion_depth for act in rendering_pool), default=3) if rendering_pool else 3

        recursion_level = 0
        while rendering_pool and (not recursion_enabled or recursion_level < max_depth):
            
            rendering_pool.sort(key=lambda x: x.priority_val, reverse=True)
            entry_to_render = rendering_pool.pop(0)

            if entry_to_render.entry_model.id in rendered_entry_ids:
                continue
            
            # 为内容求值创建上下文，包含特殊的 'trigger' 对象
            content_eval_context = build_evaluation_context(context)
            content_eval_context['trigger'] = DotAccessibleDict({
                "source_text": entry_to_render.source_text,
                "matched_keywords": entry_to_render.matched_keywords
            })

            rendered_content = str(await evaluate_data(entry_to_render.entry_model.content, content_eval_context, lock))
            
            final_text_parts.append(rendered_content)
            rendered_entry_ids.add(entry_to_render.entry_model.id)
            if debug_mode:
                evaluation_log.append({"id": entry_to_render.entry_model.id, "status": "rendered", "level": recursion_level})
            
            if recursion_enabled:
                recursion_level += 1
                new_source_text = rendered_content
                
                # 遍历所有法典，寻找可被新内容递归触发的条目
                for codex_name, codex_model in codex_collection.items():
                    for entry in codex_model.entries:
                        # 跳过已处理或已在队列中的条目
                        if entry.id in rendered_entry_ids or any(p.entry_model.id == entry.id for p in rendering_pool):
                            continue
                        
                        # 递归只对关键词模式有效
                        if entry.trigger_mode == TriggerMode.ON_KEYWORD:
                            is_enabled = await evaluate_data(entry.is_enabled, structural_eval_context, lock)
                            if not is_enabled: 
                                continue

                            keywords = await evaluate_data(entry.keywords, structural_eval_context, lock)
                            new_matched_keywords = [kw for kw in keywords if re.search(re.escape(str(kw)), new_source_text, re.IGNORECASE)]
                            
                            if new_matched_keywords:
                                priority = await evaluate_data(entry.priority, structural_eval_context, lock)
                                activated = ActivatedEntry(
                                    entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                                    priority_val=int(priority), keywords_val=keywords, is_enabled_val=is_enabled,
                                    source_text=new_source_text, matched_keywords=new_matched_keywords
                                )
                                rendering_pool.append(activated)
                                if debug_mode:
                                    recursive_activations.append({
                                        "id": entry.id, "priority": int(priority), "level": recursion_level,
                                        "reason": "recursive_keyword_match", "triggered_by": entry_to_render.entry_model.id
                                    })
        
        # --- 3. 构造输出 ---
        final_text = "\n\n".join(final_text_parts)
        
        if debug_mode:
            trace_data = {
                "initial_activation": initial_activation_trace,
                "recursive_activations": recursive_activations,
                "evaluation_log": evaluation_log,
                "rejected_entries": rejected_entries_trace,
            }
            return { "output": { "final_text": final_text, "trace": trace_data } }
        
        return {"output": final_text}
```

### core_codex/models.py
```
# plugins/core_codex/models.py
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator

class TriggerMode(str, Enum):
    ALWAYS_ON = "always_on"
    ON_KEYWORD = "on_keyword"

class CodexEntry(BaseModel):
    """定义单个知识条目的结构。"""
    id: str
    content: str  # [Macro]
    is_enabled: Any = Field(default=True)  # [Macro] bool or str
    trigger_mode: TriggerMode = Field(default=TriggerMode.ALWAYS_ON)
    keywords: Any = Field(default_factory=list)  # [Macro] List[str] or str
    priority: Any = Field(default=0)  # [Macro] int or str
    
    model_config = ConfigDict(extra='forbid') # 确保没有多余字段

class CodexConfig(BaseModel):
    """定义单个法典级别的配置。"""
    recursion_depth: int = Field(default=3, ge=0, description="此法典参与递归时的最大深度。")
    
    model_config = ConfigDict(extra='forbid')

class Codex(BaseModel):
    """定义一个完整的法典。"""
    description: Optional[str] = None
    config: CodexConfig = Field(default_factory=CodexConfig)
    entries: List[CodexEntry]
    metadata: Dict[str, Any] = Field(default_factory=dict) 

    model_config = ConfigDict(extra='forbid')

class CodexCollection(RootModel[Dict[str, Codex]]):
    """
    代表 world.codices 的顶层结构。
    模型本身是一个 `Dict[str, Codex]`。
    """
    pass

# 用于运行时内部处理的数据结构
class ActivatedEntry(BaseModel):
    entry_model: CodexEntry
    codex_name: str
    codex_config: CodexConfig
    
    # 结构性宏求值后的结果
    priority_val: int
    keywords_val: List[str]
    is_enabled_val: bool
    
    # 触发信息
    source_text: str
    matched_keywords: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
```

### core_codex/__init__.py
```
# plugins/core_codex/__init__.py
import logging
from backend.core.contracts import Container, HookManager

from .invoke_runtime import InvokeRuntime

logger = logging.getLogger(__name__)

# --- 钩子实现 ---
async def register_codex_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的 'codex.invoke' 运行时。"""
    runtimes["codex.invoke"] = InvokeRuntime 
    logger.debug("Runtime 'codex.invoke' provided to runtime registry.")
    return runtimes

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-codex] 插件...")

    # 本插件只提供运行时，不注册服务。
    # 它通过钩子与 core-engine 通信。
    hook_manager.add_implementation(
        "collect_runtimes", 
        register_codex_runtime, 
        plugin_name="core-codex"
    )
    logger.debug("钩子实现 'collect_runtimes' 已注册。")

    logger.info("插件 [core-codex] 注册成功。")
```

### core_codex/manifest.json
```
{
    "name": "core-codex",
    "version": "1.0.0",
    "description": "Provides the Codex knowledge base system and the 'codex.invoke' runtime.",
    "author": "Hevno Team",
    "priority": 30,
    "dependencies": ["core-engine"]
}
```

### core_engine/interfaces.py
```
# plugins/core_engine/interfaces.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# 从平台核心导入共享的数据契约
from backend.core.contracts import ExecutionContext

class SubGraphRunner(ABC):
    """定义执行子图能力的抽象接口。"""
    @abstractmethod
    async def execute_graph(
        self,
        graph_name: str,
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

class RuntimeInterface(ABC):
    """定义所有运行时必须实现的接口。"""
    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        subgraph_runner: Optional[SubGraphRunner] = None,
        pipeline_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass
```

### core_engine/models.py
```
# plugins/core_engine/models.py
from pydantic import BaseModel, Field, RootModel, field_validator
from typing import List, Dict, Any, Optional # <-- 导入 Optional

class RuntimeInstruction(BaseModel):
    """
    一个运行时指令，封装了运行时名称及其隔离的配置。
    这是节点执行逻辑的基本单元。
    """
    runtime: str
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="该运行时专属的、隔离的配置字典。"
    )

class GenericNode(BaseModel):
    """
    节点模型，现在以一个有序的运行时指令列表为核心。
    """
    id: str
    run: List[RuntimeInstruction] = Field(
        ...,
        description="定义节点执行逻辑的有序指令列表。"
    )
    depends_on: Optional[List[str]] = Field(
        default=None,
        description="一个可选的列表，用于明确声明此节点在执行前必须等待的其他节点的ID。用于处理无法通过宏自动推断的隐式依赖。"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphDefinition(BaseModel):
    """图定义，包含一个节点列表。"""
    nodes: List[GenericNode]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    """
    整个配置文件的顶层模型。
    使用 RootModel，模型本身就是一个 `Dict[str, GraphDefinition]`。
    """
    
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        """验证器，确保存在一个 'main' 图作为入口点。"""
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v
```

### core_engine/registry.py
```
# plugins/core_engine/registry.py

from typing import Dict, Type, Callable
import logging

# --- 核心修改: 导入路径本地化 ---
from .interfaces import RuntimeInterface

logger = logging.getLogger(__name__)

class RuntimeRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    # --- 核心修改: 这是一个常规方法，不再是装饰器工厂 ---
    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        """
        向注册表注册一个运行时类。
        """
        if name in self._registry:
            logger.warning(f"Overwriting runtime registration for '{name}'.")
        self._registry[name] = runtime_class
        logger.debug(f"Runtime '{name}' registered to the registry.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        """
        获取一个运行时的【新实例】。
        """
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime '{name}' not found in registry.")
        return runtime_class()


```

### core_engine/evaluation.py
```
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

from .utils import DotAccessibleDict
from backend.core.contracts import ExecutionContext

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
```

### core_engine/__init__.py
```
# plugins/core_engine/__init__.py

import logging
from typing import Dict, Type

from backend.core.contracts import Container, HookManager
from .engine import ExecutionEngine
from .registry import RuntimeRegistry
from .state import SnapshotStore
from .interfaces import RuntimeInterface
from .runtimes.base_runtimes import InputRuntime, SetWorldVariableRuntime
from .runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime

logger = logging.getLogger(__name__)

# --- 服务工厂 ---

def _create_runtime_registry() -> RuntimeRegistry:
    """工厂：仅创建 RuntimeRegistry 的【空】实例，并注册内置运行时。"""
    registry = RuntimeRegistry()
    logger.debug("RuntimeRegistry instance created.")

    base_runtimes: Dict[str, Type[RuntimeInterface]] = {
        "system.input": InputRuntime,
        "system.set_world_var": SetWorldVariableRuntime,
        "system.execute": ExecuteRuntime,
        "system.call": CallRuntime,
        "system.map": MapRuntime,
    }
    for name, runtime_class in base_runtimes.items():
        registry.register(name, runtime_class)
    logger.info(f"Registered {len(base_runtimes)} built-in system runtimes.")
    return registry

def _create_execution_engine(container: Container) -> ExecutionEngine:
    """工厂：创建执行引擎，并注入其所有依赖。"""
    logger.debug("Creating ExecutionEngine instance...")
    return ExecutionEngine(
        registry=container.resolve("runtime_registry"),
        container=container,
        hook_manager=container.resolve("hook_manager")
    )

# --- 钩子实现 ---
async def populate_runtime_registry(container: Container):
    """
    【新】钩子实现：监听应用启动事件，【异步地】收集并填充运行时注册表。
    """
    logger.debug("Async task: Populating runtime registry from other plugins...")
    hook_manager = container.resolve("hook_manager")
    registry = container.resolve("runtime_registry")

    external_runtimes: Dict[str, Type[RuntimeInterface]] = await hook_manager.filter("collect_runtimes", {})
    
    if not external_runtimes:
        logger.info("No external runtimes discovered from other plugins.")
        return

    logger.info(f"Discovered {len(external_runtimes)} external runtime(s): {list(external_runtimes.keys())}")
    for name, runtime_class in external_runtimes.items():
        registry.register(name, runtime_class)

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-engine] 插件...")

    container.register("snapshot_store", lambda: SnapshotStore(), singleton=True)
    container.register("sandbox_store", lambda: {}, singleton=True)
    
    # 注册工厂，它只做同步部分
    container.register("runtime_registry", _create_runtime_registry, singleton=True)
    container.register("execution_engine", _create_execution_engine, singleton=True)
    
    # 【新】注册一个监听器，它将在应用启动的异步阶段被调用
    hook_manager.add_implementation(
        "services_post_register", 
        populate_runtime_registry, 
        plugin_name="core-engine"
    )

    logger.info("插件 [core-engine] 注册成功。")
```

### core_engine/engine.py
```
# plugins/core_engine/engine.py 

import asyncio
import logging
from enum import Enum, auto
from fastapi import Request
from typing import Dict, Any, Set, List, Optional
from collections import defaultdict
import traceback

from backend.core.contracts import (
    GraphCollection, GraphDefinition, GenericNode, Container,
    ExecutionContext,
    EngineStepStartContext, EngineStepEndContext,
    BeforeConfigEvaluationContext, AfterMacroEvaluationContext,
    NodeExecutionStartContext, NodeExecutionSuccessContext, NodeExecutionErrorContext,
    HookManager, SnapshotStoreInterface
)
from .dependency_parser import build_dependency_graph_async
from .registry import RuntimeRegistry
from .evaluation import build_evaluation_context, evaluate_data
from .state import (
    create_main_execution_context, 
    create_sub_execution_context, 
    create_next_snapshot
)
from .interfaces import RuntimeInterface, SubGraphRunner

logger = logging.getLogger(__name__)

class NodeState(Enum):
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    SKIPPED = auto()

class GraphRun:
    def __init__(self, context: ExecutionContext, graph_def: GraphDefinition):
        self.context = context
        self.graph_def = graph_def
        if not self.graph_def:
            raise ValueError("GraphRun must be initialized with a valid GraphDefinition.")
        self.node_map: Dict[str, GenericNode] = {n.id: n for n in self.graph_def.nodes}
        self.node_states: Dict[str, NodeState] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.subscribers: Dict[str, Set[str]] = {}

    @classmethod
    async def create(cls, context: ExecutionContext, graph_def: GraphDefinition) -> "GraphRun":
        run = cls(context, graph_def)
        run.dependencies = await build_dependency_graph_async(
            [node.model_dump() for node in run.graph_def.nodes],
            context.hook_manager
        )
        run.subscribers = run._build_subscribers()
        run._detect_cycles()
        run._initialize_node_states()
        return run

    def _build_subscribers(self) -> Dict[str, Set[str]]:
        subscribers = defaultdict(set)
        for node_id, deps in self.dependencies.items():
            for dep_id in deps:
                subscribers[dep_id].add(node_id)
        return subscribers

    def _detect_cycles(self):
        path = set()
        visited = set()
        def visit(node_id):
            path.add(node_id)
            visited.add(node_id)
            for neighbour in self.dependencies.get(node_id, set()):
                if neighbour in path:
                    raise ValueError(f"Cycle detected involving node {neighbour}")
                if neighbour not in visited:
                    visit(neighbour)
            path.remove(node_id)
        for node_id in self.node_map:
            if node_id not in visited:
                visit(node_id)

    def _initialize_node_states(self):
        for node_id in self.node_map:
            if not self.dependencies.get(node_id):
                self.node_states[node_id] = NodeState.READY
            else:
                self.node_states[node_id] = NodeState.PENDING

    def get_node(self, node_id: str) -> GenericNode:
        return self.node_map[node_id]
    def get_node_state(self, node_id: str) -> NodeState:
        return self.node_states.get(node_id)
    def set_node_state(self, node_id: str, state: NodeState):
        self.node_states[node_id] = state
    def get_node_result(self, node_id: str) -> Dict[str, Any]:
        return self.context.node_states.get(node_id)
    def set_node_result(self, node_id: str, result: Dict[str, Any]):
        self.context.node_states[node_id] = result
    def get_nodes_in_state(self, state: NodeState) -> List[str]:
        return [nid for nid, s in self.node_states.items() if s == state]
    def get_dependencies(self, node_id: str) -> Set[str]:
        return self.dependencies.get(node_id, set())
    def get_subscribers(self, node_id: str) -> Set[str]:
        return self.subscribers.get(node_id, set())
    def get_execution_context(self) -> ExecutionContext:
        return self.context
    def get_final_node_states(self) -> Dict[str, Any]:
        return self.context.node_states

class ExecutionEngine(SubGraphRunner):
    def __init__(
        self,
        registry: RuntimeRegistry,
        container: Container,
        hook_manager: HookManager,
        num_workers: int = 5
    ):
        self.registry = registry
        self.container = container
        self.hook_manager = hook_manager
        self.num_workers = num_workers
        
    async def step(self, initial_snapshot, triggering_input: Dict[str, Any] = None):
        if triggering_input is None: triggering_input = {}
        
        await self.hook_manager.trigger(
            "engine_step_start",
            context=EngineStepStartContext(
                initial_snapshot=initial_snapshot,
                triggering_input=triggering_input
            )
        )
        
        context = create_main_execution_context(
            snapshot=initial_snapshot,
            container=self.container,
            run_vars={"triggering_input": triggering_input},
            hook_manager=self.hook_manager
        )

        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def: raise ValueError("'main' 图未找到。")
        
        final_node_states = await self._internal_execute_graph(main_graph_def, context)
        
        next_snapshot = await create_next_snapshot(
            context=context, 
            final_node_states=final_node_states, 
            triggering_input=triggering_input
        )

        # 从容器中解析快照存储服务并保存
        snapshot_store: SnapshotStoreInterface = self.container.resolve("snapshot_store")
        snapshot_store.save(next_snapshot)

        # 发布“快照已提交”事件，这是一个“即发即忘”的通知。
        # 我们将容器实例也传递过去，方便订阅者直接使用，无需再次解析。
        await self.hook_manager.trigger(
            "snapshot_committed", 
            snapshot=next_snapshot,
            container=self.container
        )

        await self.hook_manager.trigger(
            "engine_step_end",
            context=EngineStepEndContext(final_snapshot=next_snapshot)
        )

        return next_snapshot

    async def execute_graph(
        self,
        graph_name: str,
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        graph_collection = parent_context.initial_snapshot.graph_collection.root
        graph_def = graph_collection.get(graph_name)
        if not graph_def:
            raise ValueError(f"Graph '{graph_name}' not found.")
        
        sub_run_context = create_sub_execution_context(parent_context)

        return await self._internal_execute_graph(
            graph_def=graph_def,
            context=sub_run_context,
            inherited_inputs=inherited_inputs
        )

    async def _internal_execute_graph(self, graph_def: GraphDefinition, context: ExecutionContext, inherited_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        run = await GraphRun.create(context=context, graph_def=graph_def)
        task_queue = asyncio.Queue()
        
        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, result)
        
        for node_id in run.get_nodes_in_state(NodeState.PENDING):
            dependencies = run.get_dependencies(node_id)
            if all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in dependencies):
                run.set_node_state(node_id, NodeState.READY)
        
        for node_id in run.get_nodes_in_state(NodeState.READY):
            task_queue.put_nowait(node_id)

        if task_queue.empty() and not any(s == NodeState.SUCCEEDED for s in run.node_states.values()):
            return {}

        workers = [
            asyncio.create_task(self._worker(f"worker-{i}", run, task_queue))
            for i in range(self.num_workers)
        ]
        
        await task_queue.join()

        for w in workers:
            w.cancel()
        
        await asyncio.gather(*workers, return_exceptions=True)
        
        final_states = {
            nid: run.get_node_result(nid)
            for nid, n in run.node_map.items()
            if run.get_node_result(nid) is not None
        }
        return final_states

    async def _worker(self, name: str, run: 'GraphRun', queue: asyncio.Queue):
        while True:
            try:
                node_id = await queue.get()
            except asyncio.CancelledError:
                break

            run.set_node_state(node_id, NodeState.RUNNING)
            try:
                node = run.get_node(node_id)
                context = run.get_execution_context()

                await self.hook_manager.trigger(
                    "node_execution_start",
                    context=NodeExecutionStartContext(node=node, execution_context=context)
                )
                output = await self._execute_node(node, context)
                if isinstance(output, dict) and "error" in output:
                    run.set_node_state(node_id, NodeState.FAILED)

                    await self.hook_manager.trigger(
                        "node_execution_error",
                        context=NodeExecutionErrorContext(
                            node=node,
                            execution_context=context,
                            exception=ValueError(output["error"])
                        )
                    )
                else:
                    run.set_node_state(node_id, NodeState.SUCCEEDED)

                    await self.hook_manager.trigger(
                        "node_execution_success",
                        context=NodeExecutionSuccessContext(
                            node=node,
                            execution_context=context,
                            result=output
                        )
                    )
                run.set_node_result(node_id, output)
            except Exception as e:
                error_message = f"Worker-level error for node {node_id}: {type(e).__name__}: {e}"
                import traceback
                traceback.print_exc()
                run.set_node_state(node_id, NodeState.FAILED)
                run.set_node_result(node_id, {"error": error_message})

                await self.hook_manager.trigger(
                    "node_execution_error",
                    context=NodeExecutionErrorContext(
                        node=node,
                        execution_context=context,
                        exception=e
                    )
                )
            self._process_subscribers(node_id, run, queue)
            queue.task_done()

    def _process_subscribers(self, completed_node_id: str, run: 'GraphRun', queue: asyncio.Queue):
        completed_node_state = run.get_node_state(completed_node_id)
        for sub_id in run.get_subscribers(completed_node_id):
            if run.get_node_state(sub_id) != NodeState.PENDING:
                continue
            if completed_node_state == NodeState.FAILED:
                run.set_node_state(sub_id, NodeState.SKIPPED)
                run.set_node_result(sub_id, {"status": "skipped", "reason": f"Upstream failure of node {completed_node_id}."})
                self._process_subscribers(sub_id, run, queue)
                continue
            dependencies = run.get_dependencies(sub_id)
            is_ready = all(
                (dep_id not in run.node_map) or (run.get_node_state(dep_id) == NodeState.SUCCEEDED)
                for dep_id in dependencies
            )
            if is_ready:
                run.set_node_state(sub_id, NodeState.READY)
                queue.put_nowait(sub_id)

    async def _execute_node(self, node: GenericNode, context: ExecutionContext) -> Dict[str, Any]:
        pipeline_state: Dict[str, Any] = {}
        if not node.run: return {}
        
        lock = context.shared.global_write_lock

        for i, instruction in enumerate(node.run):
            runtime_name = instruction.runtime
            try:
                eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
                
                config_to_process = instruction.config.copy()

                config_to_process = await self.hook_manager.filter(
                    "before_config_evaluation",
                    config_to_process,
                    context=BeforeConfigEvaluationContext(
                        node=node,
                        execution_context=context,
                        instruction_config=config_to_process
                    )
                )

                runtime_instance: RuntimeInterface = self.registry.get_runtime(runtime_name)
                
                templates = {}
                template_fields = getattr(runtime_instance, 'template_fields', [])
                for field in template_fields:
                    if field in config_to_process:
                        templates[field] = config_to_process.pop(field)

                processed_config = await evaluate_data(config_to_process, eval_context, lock)

                processed_config = await self.hook_manager.filter(
                    "after_macro_evaluation",
                    processed_config,
                    context=AfterMacroEvaluationContext(
                        node=node,
                        execution_context=context,
                        evaluated_config=processed_config
                    )
                )

                if templates:
                    processed_config.update(templates)

                output = await runtime_instance.execute(
                    config=processed_config,
                    context=context,
                    subgraph_runner=self,
                    pipeline_state=pipeline_state
                )
                
                if not isinstance(output, dict):
                    error_message = f"Runtime '{runtime_name}' did not return a dictionary. Got: {type(output).__name__}"
                    return {"error": error_message, "failed_step": i, "runtime": runtime_name}
                pipeline_state.update(output)
            except Exception as e:
                import traceback
                traceback.print_exc()
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {type(e).__name__}: {e}"
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}
        return pipeline_state

def get_engine(request: Request) -> ExecutionEngine:
    return request.app.state.engine

```

### core_engine/utils.py
```
# plugins/core_engine/utils.py

from typing import Any, Dict
from backend.core.contracts import Container

class DotAccessibleDict:
    """
    一个【递归】代理类，它包装一个字典，并允许通过点符号进行属性访问。
    【关键修正】所有读取和写入操作都会直接作用于原始的底层字典。
    """
    def __init__(self, data: Dict[str, Any]):
        # 不再使用 object.__setattr__，而是直接存储引用。
        # Pydantic的BaseModel等复杂对象可能需要它，但我们这里用于简单字典，
        # 直接存储引用更清晰。
        self._data = data

    @classmethod
    def _wrap(cls, value: Any) -> Any:
        """递归包装值。如果值是字典，包装它；如果是列表，递归包装其内容。"""
        if isinstance(value, dict):
            return cls(value)
        if isinstance(value, list):
            # 列表本身不被包装，但其内容需要递归检查
            return [cls._wrap(item) for item in value]
        return value

    def __contains__(self, key: str) -> bool:
        """
        当执行 `key in obj` 时调用。
        直接代理到底层字典的 `in` 操作。
        """
        return key in self._data

    def __getattr__(self, name: str) -> Any:
        """
        当访问 obj.key 时调用。
        【核心修正】如果 'name' 不是 _data 的键，则检查它是否是 _data 的一个可调用方法 (如 .get, .keys)。
        """
        if name.startswith('__'):  # 避免代理魔术方法
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            
        try:
            # 优先检查底层字典中是否存在该键
            value = self._data[name]
            return self._wrap(value)
        except KeyError:
            # 如果键不存在，检查底层字典是否有一个同名的方法
            underlying_attr = getattr(self._data, name, None)
            if callable(underlying_attr):
                return underlying_attr  # 返回该方法本身，以便可以被调用
            
            # 如果都不是，则抛出异常
            raise AttributeError(f"'{type(self).__name__}' object has no attribute or method '{name}'")

    def __setattr__(self, name: str, value: Any):
        """当执行 obj.key = value 时调用。"""
        # --- 核心修正 ---
        # 如果 name 是 `_data`，就设置实例属性，否则直接修改底层字典。
        if name == '_data':
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __delattr__(self, name: str):
        """当执行 del obj.key 时调用。"""
        try:
            del self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # 保持辅助方法不变
    def __repr__(self) -> str:
        return f"DotAccessibleDict({self._data})"
    
    def __getitem__(self, key):
        return self._wrap(self._data[key])
    
    def __setitem__(self, key, value):
        self._data[key] = value

class ServiceResolverProxy:
    """
    一个代理类，它包装一个 DI 容器，使其表现得像一个字典。
    这使得宏系统可以通过 `services.service_name` 语法懒加载并访问容器中的服务。
    """
    def __init__(self, container: Container):
        """
        :param container: 要代理的 DI 容器实例。
        """
        self._container = container
        # 创建一个简单的缓存，避免对同一个单例服务重复调用 resolve
        self._cache: dict = {}

    def __getitem__(self, name: str):
        """
        这是核心魔法所在。当代码执行 `proxy['service_name']` 时，此方法被调用。
        """
        # 1. 检查缓存中是否已有该服务实例
        if name in self._cache:
            return self._cache[name]
        
        # 2. 如果不在缓存中，调用容器的 resolve 方法来创建或获取服务
        #    如果服务不存在，container.resolve 会抛出 ValueError，这是我们期望的行为。
        service_instance = self._container.resolve(name)
        
        # 3. 将解析出的服务实例存入缓存
        self._cache[name] = service_instance
        
        # 4. 返回服务实例
        return service_instance

    def get(self, key: str, default=None):
        """
        实现 .get() 方法，使其行为与标准字典一致。
        这对于某些工具（包括 DotAccessibleDict 的某些行为）来说很有用。
        """
        try:
            return self.__getitem__(key)
        except (ValueError, KeyError):
            # 如果 resolve 失败（服务未注册），则返回默认值
            return default

    def keys(self):
        """
        (可选) 实现 .keys() 方法。
        这可以让调试时（如 `list(services.keys())`）看到所有可用的服务。
        """
        # 直接返回容器中所有已注册工厂的名称
        return self._container._factories.keys()
    
    def __contains__(self, key: str) -> bool:
        """实现 `in` 操作符，例如 `if 'llm_service' in services:`"""
        return key in self._container._factories
```

### core_engine/manifest.json
```
{
    "name": "core-engine",
    "version": "1.0.0",
    "description": "Provides the graph parsing, scheduling, and execution engine.",
    "author": "Hevno Team",
    "priority": 50
}
```

### core_engine/dependency_parser.py
```
# plugins/core_engine/dependency_parser.py
import re
from typing import Set, Dict, Any, List
import asyncio


from backend.core.contracts import HookManager, ResolveNodeDependenciesContext, GenericNode


NODE_DEP_REGEX = re.compile(r'nodes\.([a-zA-Z0-9_]+)')

def extract_dependencies_from_string(s: str) -> Set[str]:
    if not isinstance(s, str):
        return set()
    if '{{' in s and '}}' in s and 'nodes.' in s:
        return set(NODE_DEP_REGEX.findall(s))
    return set()

def extract_dependencies_from_value(value: Any) -> Set[str]:
    deps = set()
    if isinstance(value, str):
        deps.update(extract_dependencies_from_string(value))
    elif isinstance(value, list):
        for item in value:
            deps.update(extract_dependencies_from_value(item))
    elif isinstance(value, dict):
        for k, v in value.items():
            deps.update(extract_dependencies_from_value(k))
            deps.update(extract_dependencies_from_value(v))
    return deps

async def build_dependency_graph_async(
    nodes: List[Dict[str, Any]],
    hook_manager: HookManager
) -> Dict[str, Set[str]]:
    dependency_map: Dict[str, Set[str]] = {}
    
    # 将所有节点字典预先转换为 Pydantic 模型实例，以便在钩子中使用
    node_map: Dict[str, GenericNode] = {node_dict['id']: GenericNode.model_validate(node_dict) for node_dict in nodes}

    for node_dict in nodes:
        node_id = node_dict['id']
        
        # 【核心修复】通过 node_id 从 node_map 中获取对应的模型实例
        node_instance = node_map[node_id]
        
        auto_inferred_deps = set()
        for instruction in node_dict.get('run', []):
            instruction_config = instruction.get('config', {})
            dependencies = extract_dependencies_from_value(instruction_config)
            auto_inferred_deps.update(dependencies)
    
        explicit_deps = set(node_dict.get('depends_on') or [])

        # 现在可以安全地调用 hook_manager 了
        custom_deps = await hook_manager.decide(
            "resolve_node_dependencies",
            context=ResolveNodeDependenciesContext(
                node=node_instance,
                auto_inferred_deps=auto_inferred_deps.union(explicit_deps)
            )
        )
        
        if custom_deps is not None:
            # 如果插件做出了决策，就使用插件的结果
            all_dependencies = custom_deps
        else:
            # 否则，使用默认逻辑
            all_dependencies = auto_inferred_deps.union(explicit_deps)
        
        dependency_map[node_id] = all_dependencies
    
    return dependency_map
```

### core_engine/state.py
```
# plugins/core_engine/state.py

from __future__ import annotations
import asyncio
import json
from uuid import UUID
from typing import Dict, Any, List, Optional

from fastapi import Request
from pydantic import ValidationError

from backend.core.contracts import (
    Sandbox, 
    StateSnapshot, 
    ExecutionContext, 
    SharedContext,
    BeforeSnapshotCreateContext,
    GraphCollection,
    HookManager,
    Container
)
from .utils import DotAccessibleDict, ServiceResolverProxy 

# --- Section 1: 状态存储类 (包含逻辑) ---

class SnapshotStore:
    """
    一个简单的内存快照存储。
    它操作从 contracts.py 导入的 StateSnapshot 模型。
    """
    def __init__(self):
        self._store: Dict[UUID, StateSnapshot] = {}

    def save(self, snapshot: StateSnapshot):
        if snapshot.id in self._store:
            pass
        self._store[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> Optional[StateSnapshot]:
        return self._store.get(snapshot_id)

    def find_by_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        return sorted(
            [s for s in self._store.values() if s.sandbox_id == sandbox_id],
            key=lambda s: s.created_at
        )

    def clear(self):
        self._store.clear()


# --- Section 2: 核心上下文与快照的工厂/助手函数 ---

def create_main_execution_context(
    snapshot: StateSnapshot, 
    container: Container,
    hook_manager: HookManager, 
    run_vars: Dict[str, Any] = None
) -> ExecutionContext:
    shared_context = SharedContext(
        world_state=snapshot.world_state.copy(),
        session_info={
            "start_time": snapshot.created_at,
            "turn_count": 0
        },
        global_write_lock=asyncio.Lock(),
        
        # 关键步骤：
        # 1. 创建 ServiceResolverProxy 实例，它包装了我们的容器。
        # 2. 将这个代理实例传递给 DotAccessibleDict。
        #
        # 这样，`services` 字段就是一个 DotAccessibleDict，
        # 当宏执行 `services.llm_service` 时，
        # DotAccessibleDict 会调用 `proxy['llm_service']`，
        # 进而触发 `ServiceResolverProxy` 去调用 `container.resolve('llm_service')`。
        services=DotAccessibleDict(ServiceResolverProxy(container))
    )
    return ExecutionContext(
        shared=shared_context,
        initial_snapshot=snapshot,
        run_vars=run_vars or {},
        hook_manager=hook_manager
    )

def create_sub_execution_context(
    parent_context: ExecutionContext, 
    run_vars: Dict[str, Any] = None
) -> ExecutionContext:
    return ExecutionContext(
        shared=parent_context.shared,
        initial_snapshot=parent_context.initial_snapshot,
        run_vars=run_vars or {},
        hook_manager=parent_context.hook_manager
    )

async def create_next_snapshot(
    context: ExecutionContext,
    final_node_states: Dict[str, Any],
    triggering_input: Dict[str, Any]
) -> StateSnapshot:
    final_world_state = context.shared.world_state
    next_graph_collection = context.initial_snapshot.graph_collection

    if '__graph_collection__' in final_world_state:
        evolved_graph_data = final_world_state.pop('__graph_collection__', None)
        if evolved_graph_data:
            try:
                next_graph_collection = GraphCollection.model_validate(evolved_graph_data)
            except (ValidationError, json.JSONDecodeError) as e:
                print(f"Warning: Failed to parse evolved graph collection from world_state: {e}")

    snapshot_data = {
        "sandbox_id": context.initial_snapshot.sandbox_id,
        "graph_collection": next_graph_collection,
        "world_state": final_world_state,
        "parent_snapshot_id": context.initial_snapshot.id,
        "run_output": final_node_states,
        "triggering_input": triggering_input,
    }

    filtered_snapshot_data = await context.hook_manager.filter(
        "before_snapshot_create",
        snapshot_data,
        context=BeforeSnapshotCreateContext(
            snapshot_data=snapshot_data,
            execution_context=context
        )
    )
    
    return StateSnapshot.model_validate(filtered_snapshot_data)


# --- Section 3: FastAPI 依赖注入函数 ---

def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    return request.app.state.sandbox_store

def get_snapshot_store(request: Request) -> SnapshotStore:
    return request.app.state.snapshot_store


```

### core_engine/tests/test_engine_execution.py
```
# plugins/core_engine/tests/test_engine_execution.py

import pytest
from uuid import uuid4

# 从平台核心契约导入共享的数据模型
from backend.core.contracts import StateSnapshot, GraphCollection

# 从本插件的接口定义导入，测试应依赖于接口而非具体实现
from backend.core.contracts import ExecutionEngineInterface

# 使用 pytest.mark.asyncio 来标记所有异步测试
@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，如线性、并行、错误处理等。"""

    async def test_linear_flow(self, test_engine: ExecutionEngineInterface, linear_collection: GraphCollection):
        """测试一个简单的线性依赖图 A -> B -> C。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert "A" in output and "output" in output["A"]
        assert "B" in output and "llm_output" in output["B"]
        assert "C" in output and "llm_output" in output["C"]
        
        # 验证B的输入来自A
        b_prompt = "The story is: a story about a cat"
        # 【修复】断言B的输出包含了正确的prompt
        assert b_prompt in output["B"]["llm_output"]

        # 验证C的输入来自B
        c_prompt = output['B']['llm_output']
        # 【修复】断言C的输出包含了B的完整输出作为其prompt
        assert c_prompt in output["C"]["llm_output"]


    async def test_parallel_flow(self, test_engine: ExecutionEngineInterface, parallel_collection: GraphCollection):
        """测试一个扇出再扇入的图 (A, B) -> C，验证并行执行和依赖合并。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=parallel_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        assert "source_A" in output
        assert "source_B" in output
        assert "merger" in output

        assert output["merger"]["output"] == "Merged: Value A and Value B"

    async def test_pipeline_within_node(self, test_engine: ExecutionEngineInterface, pipeline_collection: GraphCollection):
        """测试节点内指令管道，后一个指令可以使用前一个指令的输出 (`pipe` 对象)。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 验证第一个指令设置的世界变量
        assert final_snapshot.world_state["main_character"] == "Sir Reginald"

        node_a_result = final_snapshot.run_output["A"]
        
        # 验证第三个指令的 prompt 正确使用了 world 状态和第二个指令的 pipe 输出
        expected_prompt = "Tell a story about Sir Reginald. He just received this message: A secret message"
        # 【修复】改为更健壮的 'in' 检查
        assert expected_prompt in node_a_result["llm_output"]
        
        # 验证第二个指令的输出也被保留在最终结果中
        assert node_a_result["output"] == "A secret message"
        
    async def test_handles_failure_and_skips_downstream(self, test_engine: ExecutionEngineInterface, failing_node_collection: GraphCollection):
        """测试当一个节点失败时，其下游依赖节点会被正确跳过。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        # 验证成功的节点
        assert "error" not in output["A_ok"]
        assert "error" not in output["D_independent"]

        # 验证失败的节点
        assert "error" in output["B_fail"]
        assert "non_existent_variable" in output["B_fail"]["error"]

        # 验证被跳过的节点
        assert "status" in output["C_skip"] and output["C_skip"]["status"] == "skipped"
        assert "reason" in output["C_skip"] and "Upstream failure of node B_fail" in output["C_skip"]["reason"]

    async def test_detects_cycle(self, test_engine: ExecutionEngineInterface, cyclic_collection: GraphCollection):
        """测试引擎能否在执行前检测到图中的依赖环。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        with pytest.raises(ValueError, match="Cycle detected"):
            await test_engine.step(initial_snapshot, {})


    async def test_subgraph_call(self, test_engine: ExecutionEngineInterface, subgraph_call_collection: GraphCollection):
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_collection,
            world_state={"global_setting": "Alpha"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output
        subgraph_result = output["main_caller"]["output"]
        processor_output = subgraph_result["processor"]["output"]
        assert processor_output == "Processed: Hello from main with world state: Alpha"

    async def test_subgraph_failure_propagates_to_caller(self, test_engine, subgraph_with_failure_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=subgraph_with_failure_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output
        caller_result = output["caller"]["output"]
        assert "error" in caller_result["B_fail"]

# ... (The rest of the file remains the same)
@pytest.mark.asyncio
class TestEngineStateManagement:
    """测试与状态管理（世界状态、图演化）相关的引擎功能。"""

    async def test_world_state_persists_and_macros_read_it(self, test_engine: ExecutionEngineInterface, world_vars_collection: GraphCollection):
        """测试 `set_world_var` 能够修改状态，且后续节点能通过宏读取到该状态。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        assert final_snapshot.world_state.get("theme") == "cyberpunk"

        reader_output = final_snapshot.run_output["reader"]["output"]
        assert reader_output.startswith("The theme is: cyberpunk")

    async def test_graph_evolution(self, test_engine: ExecutionEngineInterface, graph_evolution_collection: GraphCollection):
        """测试图本身作为状态可以被逻辑修改（图演化）。"""
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        
        # 第一次执行，图演化节点运行，修改 world.__graph_collection__
        snapshot_after_evolution = await test_engine.step(genesis_snapshot, {})
        
        # 验证新生成的快照中，图的定义已经改变
        new_graph_def = snapshot_after_evolution.graph_collection
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        # 第二次执行，应该在新图上运行
        final_snapshot = await test_engine.step(snapshot_after_evolution, {})
        assert final_snapshot.run_output["new_node"]["output"] == "This is the evolved graph!"

    async def test_execute_runtime_modifies_state(self, test_engine: ExecutionEngineInterface, execute_runtime_collection: GraphCollection):
        """测试 `system.execute` 运行时可以成功执行宏并修改世界状态。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(), 
            graph_collection=execute_runtime_collection,
            world_state={"player_status": "normal"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        assert final_snapshot.world_state["player_status"] == "empowered"

@pytest.mark.asyncio
class TestEngineSubgraphExecution:
    """测试引擎的子图执行功能 (system.call)。"""

    async def test_basic_subgraph_call(self, test_engine: ExecutionEngineInterface, subgraph_call_collection: GraphCollection):
        """测试基本的子图调用，包括输入映射和世界状态访问。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_collection,
            world_state={"global_setting": "Alpha"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output
        
        subgraph_result = output["main_caller"]["output"]
        assert isinstance(subgraph_result, dict)
        
        processor_output = subgraph_result["processor"]["output"]
        expected_str = "Processed: Hello from main with world state: Alpha"
        assert processor_output == expected_str
        
    async def test_nested_subgraph_call(self, test_engine: ExecutionEngineInterface, nested_subgraph_collection: GraphCollection):
        """测试嵌套的子图调用：main -> sub1 -> sub2。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=nested_subgraph_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output

        sub1_result = output["main_caller"]["output"]
        sub2_result = sub1_result["sub1_caller"]["output"]
        final_output = sub2_result["final_processor"]["output"]
        
        assert final_output == "Reached level 2 from: level 0"

    async def test_subgraph_can_modify_world_state(self, test_engine: ExecutionEngineInterface, subgraph_modifies_world_collection: GraphCollection):
        """测试子图可以修改世界状态，且父图中的后续节点可以读取到。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_modifies_world_collection,
            world_state={"counter": 100}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        assert final_snapshot.world_state["counter"] == 110

        reader_output = final_snapshot.run_output["reader"]["output"]
        assert "Final counter: 110" in reader_output

    async def test_subgraph_failure_propagates_to_caller(self, test_engine: ExecutionEngineInterface, subgraph_with_failure_collection: GraphCollection):
        """
        测试子图内部的失败会体现在调用节点的输出中。
        重要：调用节点本身 (`caller`) 应为 SUCCEEDED，因为它成功“执行”并捕获了子图的结果（即使结果是失败）。
        """
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=subgraph_with_failure_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        
        # 1. 调用节点本身没有错误
        assert "error" not in output["caller"]
        
        # 2. 调用节点的输出包含了子图的失败信息
        caller_result = output["caller"]["output"]
        assert "B_fail" in caller_result
        assert "error" in caller_result["B_fail"]
        assert "non_existent" in caller_result["B_fail"]["error"]

        # 3. 依赖于 `caller` 的下游节点会执行，因为它看到 `caller` 是成功的
        assert "downstream_of_fail" in output
        assert "error" not in output.get("downstream_of_fail", {})

@pytest.mark.asyncio
class TestEngineMapExecution:
    """对 system.map 运行时的集成测试。"""
    
    async def test_basic_map(self, test_engine: ExecutionEngineInterface, map_collection_basic: GraphCollection):
        """测试基本的 scatter-gather 功能，不使用 `collect`。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_basic)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        map_result = final_snapshot.run_output["character_processor_map"]["output"]

        assert isinstance(map_result, list) and len(map_result) == 3
        assert "generate_bio" in map_result[0]
        
        aragorn_output = map_result[0]["generate_bio"]["llm_output"]
        legolas_output = map_result[2]["generate_bio"]["llm_output"]
        
        assert "Create a bio for Aragorn" in aragorn_output
        assert "Index: 0" in aragorn_output
        
        assert "Create a bio for Legolas" in legolas_output
        assert "Index: 2" in legolas_output


    async def test_map_with_collect(self, test_engine: ExecutionEngineInterface, map_collection_with_collect: GraphCollection):
        """测试 `collect` 功能，期望输出是一个扁平化的值列表。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_with_collect)
        final_snapshot = await test_engine.step(initial_snapshot, {})

        map_result = final_snapshot.run_output["character_processor_map"]["output"]

        assert isinstance(map_result, list) and len(map_result) == 3
        assert isinstance(map_result[0], str)
        assert map_result[0].startswith("[MOCK RESPONSE") and "Aragorn" in map_result[0]

    async def test_map_handles_concurrent_world_writes(self, test_engine: ExecutionEngineInterface, map_collection_concurrent_write: GraphCollection):
        """验证在 map 中并发写入 world_state 是原子和安全的。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_concurrent_write,
            world_state={"gold": 0}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        # 10个并行任务，每个增加10金币
        expected_gold = 100
        assert final_snapshot.world_state.get("gold") == expected_gold
        assert final_snapshot.run_output["reader"]["output"] == expected_gold

    async def test_map_handles_partial_failures_gracefully(self, test_engine: ExecutionEngineInterface, map_collection_with_failure: GraphCollection):
        """测试当 map 迭代中的某些子图失败时，整体操作不会崩溃，并返回清晰的结果。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_with_failure)
        final_snapshot = await test_engine.step(initial_snapshot, {})

        map_result = final_snapshot.run_output["mapper"]["output"]

        assert len(map_result) == 3
        # 验证成功的项 (Alice, Charlie)
        assert "error" not in map_result[0].get("get_name", {})
        assert "error" not in map_result[2].get("get_name", {})

        # 验证失败的项 (Bob)
        failed_item_result = map_result[1]
        assert "error" in failed_item_result["get_name"]
        assert "AttributeError" in failed_item_result["get_name"]["error"]
```

### core_engine/tests/test_concurrency.py
```
# plugins/core_engine/tests/test_concurrency.py

import pytest
from uuid import uuid4

from backend.core.contracts import StateSnapshot, GraphCollection
from backend.core.contracts import ExecutionEngineInterface

@pytest.mark.asyncio
class TestEngineConcurrency:
    """测试引擎的并发控制和原子锁机制。"""

    # Migrated from test_05_concurrency.py
    async def test_concurrent_writes_are_atomic(
        self, 
        test_engine: ExecutionEngineInterface,
        concurrent_write_collection: GraphCollection
    ):
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=concurrent_write_collection,
            world_state={"counter": 0}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        expected_final_count = 200
        assert final_snapshot.world_state.get("counter") == expected_final_count
        assert final_snapshot.run_output["reader"]["output"] == expected_final_count

    # Migrated from test_06_map_runtime.py
    async def test_map_handles_concurrent_world_writes(
        self,
        test_engine: ExecutionEngineInterface,
        map_collection_concurrent_write: GraphCollection
    ):
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_concurrent_write,
            world_state={"gold": 0}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        expected_gold = 100
        assert final_snapshot.world_state.get("gold") == expected_gold
        assert final_snapshot.run_output["reader"]["output"] == expected_gold
```

### core_engine/tests/conftest.py
```
# plugins/core_engine/tests/conftest.py

import pytest
import pytest_asyncio 
from typing import AsyncGenerator 

# 从平台核心导入
from backend.container import Container
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.engine import ExecutionEngine
from plugins.core_engine.registry import RuntimeRegistry
from plugins.core_engine.state import SnapshotStore
from plugins.core_engine.runtimes.base_runtimes import InputRuntime, SetWorldVariableRuntime
from plugins.core_engine.runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime

# 从其他插件导入，但我们只导入它们的注册函数
from plugins.core_llm import register_plugin as register_llm_plugin
from plugins.core_codex import register_plugin as register_codex_plugin

@pytest.fixture
def hook_manager() -> HookManager:
    """Provides a basic HookManager for unit tests."""
    return HookManager()
```

### core_engine/tests/__init__.py
```

```

### core_engine/tests/test_evaluation.py
```
# plugins/core_engine/tests/test_evaluation.py

import pytest
import asyncio
from uuid import uuid4


from backend.container import Container
from backend.core.contracts import ExecutionContext, StateSnapshot, GraphCollection
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.evaluation import evaluate_expression, evaluate_data, build_evaluation_context
from plugins.core_engine.state import create_main_execution_context
from plugins.core_engine.runtimes.base_runtimes import SetWorldVariableRuntime

# 从依赖插件导入
from plugins.core_llm.service import MockLLMService

@pytest.fixture
def mock_exec_context() -> ExecutionContext:
    """提供一个可复用的、模拟的 ExecutionContext。"""
    container = Container()
    container.register("llm_service", lambda: MockLLMService())
    
    graph_coll = GraphCollection.model_validate({"main": {"nodes": []}})
    snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_coll, world_state={"user_name": "Alice", "hp": 100})
    
    context = create_main_execution_context(
        snapshot=snapshot, 
        container=container,
        hook_manager=HookManager()
    )
    context.node_states = {"node_A": {"output": "Success"}}
    context.run_vars = {"trigger_input": {"message": "Do it!"}}
    return context

@pytest.fixture
def mock_eval_context(mock_exec_context: ExecutionContext) -> dict:
    return build_evaluation_context(mock_exec_context, pipe_vars={"from_pipe": "pipe_data"})

@pytest.fixture
def test_lock() -> asyncio.Lock:
    return asyncio.Lock()

@pytest.mark.asyncio
class TestEvaluationUnit:
    """对宏求值核心 `evaluate_expression` 和 `evaluate_data` 进行单元测试。"""
    
    async def test_context_access(self, mock_eval_context, test_lock):
        code = "f'{nodes.node_A.output}, {world.user_name}, {run.trigger_input.message}, {pipe.from_pipe}'"
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result == "Success, Alice, Do it!, pipe_data"

    async def test_side_effects_on_world_state(self, mock_exec_context: ExecutionContext, test_lock):
        eval_context = build_evaluation_context(mock_exec_context)
        await evaluate_expression("world.hp -= 10", eval_context, test_lock)
        assert mock_exec_context.shared.world_state["hp"] == 90

    async def test_evaluate_data_recursively(self, mock_eval_context, test_lock):
        data = {"direct": "{{ 1 + 2 }}", "nested": ["{{ world.user_name }}"]}
        result = await evaluate_data(data, mock_eval_context, test_lock)
        assert result == {"direct": 3, "nested": ["Alice"]}
```

### core_engine/tests/test_foundations.py
```
# plugins/core_engine/tests/test_foundations.py

import pytest

# 从平台核心导入
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.dependency_parser import build_dependency_graph_async

@pytest.mark.asyncio
class TestDependencyParser:
    """测试依赖解析器，它是引擎的基础功能。"""

    # Migrated from test_01_foundations.py
    async def test_simple_dependency(self, hook_manager: HookManager):
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"runtime": "test", "config": {"value": "{{ nodes.A.output }}"}}]}]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["B"] == {"A"}

    # Migrated from test_01_foundations.py
    async def test_explicit_dependency_with_depends_on(self, hook_manager: HookManager):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ world.some_var }}"}}]}
        ]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["B"] == {"A"}
        
    # Migrated from test_01_foundations.py
    async def test_combined_dependencies(self, hook_manager: HookManager):
        nodes = [
            {"id": "A", "run": []},
            {"id": "B", "run": []},
            {"id": "C", "depends_on": ["A"], "run": [{"runtime": "test", "config": {"value": "{{ nodes.B.output }}"}}]}
        ]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["C"] == {"A", "B"}
```

### core_engine/runtimes/__init__.py
```

```

### core_engine/runtimes/base_runtimes.py
```
# plugins/core_engine/runtimes/base_runtimes.py

import logging
from typing import Dict, Any


from ..interfaces import RuntimeInterface
from backend.core.contracts import ExecutionContext

logger = logging.getLogger(__name__)


class InputRuntime(RuntimeInterface):
    """从 config 中获取 'value'。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value", "")}


class SetWorldVariableRuntime(RuntimeInterface):
    """从 config 中获取变量名和值，并设置一个持久化的世界变量。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        variable_name = config.get("variable_name")
        value_to_set = config.get("value")

        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name' in its config.")
        
        logger.debug(f"Setting world_state['{variable_name}'] to: {value_to_set}")
        context.shared.world_state[variable_name] = value_to_set
        
        return {}
```

### core_engine/runtimes/control_runtimes.py
```
# plugins/core_engine/runtimes/control_runtimes.py

from typing import Dict, Any, List, Optional
import asyncio


from ..interfaces import RuntimeInterface, SubGraphRunner
from ..evaluation import evaluate_data, evaluate_expression, build_evaluation_context
from ..utils import DotAccessibleDict
from backend.core.contracts import ExecutionContext


class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        code_to_execute = config.get("code")

        if not isinstance(code_to_execute, str):
            return {"output": code_to_execute}

        eval_context = build_evaluation_context(context)
        # --- 修正: 从共享上下文中获取并传递锁 ---
        lock = context.shared.global_write_lock
        result = await evaluate_expression(code_to_execute, eval_context, lock)
        return {"output": result}


class CallRuntime(RuntimeInterface):
    """执行一个子图。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("CallRuntime requires a SubGraphRunner.")
            
        graph_name = config.get("graph")
        using_inputs = config.get("using", {})
        
        inherited_inputs = {
            placeholder_name: {"output": value}
            for placeholder_name, value in using_inputs.items()
        }

        # 调用 subgraph_runner，它会负责创建正确的子上下文
        subgraph_results = await subgraph_runner.execute_graph(
            graph_name=graph_name,
            parent_context=context, # 传递当前的上下文
            inherited_inputs=inherited_inputs
        )
        
        return {"output": subgraph_results}


class MapRuntime(RuntimeInterface):
    """并行迭代。"""
    template_fields = ["using", "collect"]

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("MapRuntime requires a SubGraphRunner.")

        list_to_iterate = config.get("list")
        graph_name = config.get("graph")
        using_template = config.get("using", {})
        collect_template = config.get("collect")

        if not isinstance(list_to_iterate, list):
            raise TypeError(f"system.map 'list' field must be a list...")

        tasks = []
        base_eval_context = build_evaluation_context(context)
        lock = context.shared.global_write_lock

        for index, item in enumerate(list_to_iterate):
            # a. 创建包含 `source` 的临时上下文，用于求值 `using`
            using_eval_context = {
                **base_eval_context,
                "source": DotAccessibleDict({"item": item, "index": index})
            }
            
            # b. 求值 `using` 字典 (需要传递锁)
            evaluated_using = await evaluate_data(using_template, using_eval_context, lock)
            inherited_inputs = {
                placeholder: {"output": value}
                for placeholder, value in evaluated_using.items()
            }
            
            # c. 创建子图执行任务
            #    subgraph_runner.execute_graph 会处理子上下文的创建
            task = asyncio.create_task(
                subgraph_runner.execute_graph(
                    graph_name=graph_name,
                    parent_context=context,
                    inherited_inputs=inherited_inputs
                )
            )
            tasks.append(task)
        
        subgraph_results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        
        # d. 聚合阶段
        if collect_template:
            collected_outputs = []
            for result in subgraph_results:
                # `nodes` 指向当前子图的结果
                collect_eval_context = build_evaluation_context(context)
                collect_eval_context["nodes"] = DotAccessibleDict(result)
                
                collected_value = await evaluate_data(collect_template, collect_eval_context, lock)
                collected_outputs.append(collected_value)
            
            return {"output": collected_outputs}
        else:
            return {"output": subgraph_results}
```

### core_codex/tests/__init__.py
```

```

### core_codex/tests/test_codex_runtime.py
```
# plugins/core_codex/tests/test_codex_runtime.py

import pytest
from uuid import uuid4

from backend.core.contracts import StateSnapshot, GraphCollection
from backend.core.contracts import ExecutionEngineInterface

@pytest.mark.asyncio
class TestCodexSystem:
    """对 Hevno Codex 系统的集成测试 (codex.invoke 运行时)。"""


    async def test_basic_invoke_always_on(
        self, test_engine: ExecutionEngineInterface, codex_basic_data: dict
    ):
        graph = GraphCollection.model_validate(codex_basic_data["graph"])
        snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph,
            world_state={"codices": codex_basic_data["codices"]}
        )
        final_snapshot = await test_engine.step(snapshot, {})
        invoke_output = final_snapshot.run_output["invoke_test"]["output"]
        expected_text = "你好，冒险者！\n\n欢迎来到这个奇幻的世界。"
        assert invoke_output == expected_text


    async def test_invoke_recursion_enabled(
        self, test_engine: ExecutionEngineInterface, codex_recursion_data: dict
    ):
        graph = GraphCollection.model_validate(codex_recursion_data["graph"])
        snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph,
            world_state={"codices": codex_recursion_data["codices"]}
        )
        final_snapshot = await test_engine.step(snapshot, {})
        invoke_result = final_snapshot.run_output["recursive_invoke"]["output"]
        final_text = invoke_result["final_text"]
        expected_rendered_order = [
            "这是关于A的信息，它引出B。",
            "B被A触发了，它又引出C。",
            "C被B触发了，这是最终信息。",
            "这是一个总是存在的背景信息。",
        ]
        assert final_text.split("\n\n") == expected_rendered_order
```

### core_persistence/tests/conftest.py
```

```

### core_persistence/tests/test_persistence_api.py
```
# plugins/core_persistence/tests/test_persistence_api.py

import pytest
import io
import json
import zipfile
from uuid import UUID

from fastapi.testclient import TestClient
from backend.core.contracts import GraphCollection, Container, SnapshotStoreInterface

@pytest.mark.e2e
class TestPersistenceAPI:
    """测试与持久化相关的 API 端点。"""


    def test_list_assets_is_empty(self, test_client: TestClient):
        # 这是一个新的、针对 persistence 插件 API 的简单测试
        response = test_client.get("/api/persistence/assets/graph")
        assert response.status_code == 200
        assert response.json() == []

```

### core_persistence/tests/__init__.py
```

```

### core_api/tests/__init__.py
```

```

### core_api/tests/test_api_e2e.py
```
# plugins/core_api/tests/test_api_e2e.py

import pytest
import zipfile
import io
import json
from fastapi.testclient import TestClient
from uuid import uuid4, UUID

# 从平台核心契约导入数据模型
from backend.core.contracts import GraphCollection

@pytest.mark.e2e
class TestApiSandboxLifecycle:
    """测试沙盒从创建、执行、查询到回滚的完整生命周期。"""
    
    def test_full_lifecycle(self, test_client: TestClient, linear_collection: GraphCollection):
        # 1. 创建沙盒
        response = test_client.post(
            "/api/sandboxes",
            json={
                "name": "E2E Test",
                "graph_collection": linear_collection.model_dump(),
                "initial_state": {} 
            }
        )
        assert response.status_code == 201, response.text
        sandbox_data = response.json()
        sandbox_id = sandbox_data["id"]
        genesis_snapshot_id = sandbox_data["head_snapshot_id"]

        # 2. 执行一步
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={"user_message": "test"})
        assert response.status_code == 200, response.text
        step1_snapshot_data = response.json()
        run_output = step1_snapshot_data.get("run_output", {})
        assert "C" in run_output
        assert run_output["C"]["llm_output"].startswith("[MOCK RESPONSE for mock/model]")

        # 3. 获取历史记录
        response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert response.status_code == 200, response.text
        history = response.json()
        assert len(history) == 2

        # 4. 回滚到创世快照
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": genesis_snapshot_id}
        )
        assert response.status_code == 200

@pytest.mark.e2e
class TestSystemReportAPI:
    """测试 /api/system/report 端点"""

    def test_get_system_report(self, test_client: TestClient):
        response = test_client.get("/api/system/report")
        assert response.status_code == 200
        report = response.json()

        # 验证报告中包含了由各插件提供的 key
        assert "llm_providers" in report # from core_llm
        # assert "runtimes" in report # 运行时报告器尚未迁移，但可以加上
        
        # 验证 llm_providers 的内容
        assert isinstance(report["llm_providers"], list)
        gemini_provider_report = next((p for p in report["llm_providers"] if p["name"] == "gemini"), None)
        assert gemini_provider_report is not None

@pytest.mark.e2e
class TestApiErrorHandling:
    """测试 API 在各种错误情况下的响应。"""

    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        response = test_client.post(
            "/api/sandboxes",
            json={"name": "Invalid Graph", "graph_collection": invalid_graph_no_main}
        )
        assert response.status_code == 422
        error_detail = response.json()["detail"][0]
        assert "A 'main' graph must be defined" in error_detail["msg"]

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        nonexistent_id = uuid4()
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        assert response.status_code == 404


@pytest.mark.e2e
class TestSandboxImportExport:
    """专门测试沙盒导入/导出 API 的类。"""

    def test_sandbox_export_import_roundtrip(
        self, test_client: TestClient, linear_collection: GraphCollection
    ):
        """
        测试一个完整的沙盒导出和导入流程（往返测试）。
        """
        # --- 步骤 1 & 2: 创建沙盒，执行一步，然后导出 ---
        create_resp = test_client.post(
            "/api/sandboxes",
            json={"name": "Export-Test-Sandbox", "graph_collection": linear_collection.model_dump()}
        )
        assert create_resp.status_code == 201
        sandbox_id = create_resp.json()["id"]

        step_resp = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        assert step_resp.status_code == 200
        
        export_resp = test_client.get(f"/api/sandboxes/{sandbox_id}/export")
        assert export_resp.status_code == 200
        
        # --- 步骤 3: 验证导出的 ZIP 文件 ---
        zip_bytes = export_resp.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            filenames = zf.namelist()
            assert "manifest.json" in filenames
            assert "data/sandbox.json" in filenames
            assert len([f for f in filenames if f.startswith("data/snapshots/")]) == 2
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["package_type"] == "sandbox_archive"

        # --- 步骤 4: 清理状态，模拟新环境 ---
        container: Container = test_client.app.state.container
        sandbox_store: dict = container.resolve("sandbox_store")
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        sandbox_store.clear()
        snapshot_store.clear()

        # --- 步骤 5: 导入 ZIP 文件 ---
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("imported.hevno.zip", zip_bytes, "application/zip")}
        )
        assert import_resp.status_code == 200
        imported_sandbox = import_resp.json()
        
        # --- 步骤 6: 验证恢复的状态 ---
        assert imported_sandbox["id"] == sandbox_id
        assert imported_sandbox["name"] == "Export-Test-Sandbox"
        assert len(sandbox_store) == 1
        
        history_resp = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert history_resp.status_code == 200
        assert len(history_resp.json()) == 2

    def test_import_invalid_package_type(self, test_client: TestClient):
        """测试导入一个非沙盒类型的包应被拒绝。"""
        manifest = {
            "package_type": "graph_collection", # 错误的类型
            "entry_point": "file.json",
            "format_version": "1.0"
        }
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("data/file.json", "{}")
        
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("wrong_type.hevno.zip", zip_buffer.getvalue(), "application/zip")}
        )
        assert import_resp.status_code == 400
        assert "Invalid package type" in import_resp.json()["detail"]

    def test_import_conflicting_sandbox_id(
        self, test_client: TestClient, linear_collection: GraphCollection
    ):
        """测试当导入的沙盒 ID 已存在时，应返回 409 Conflict。"""
        # 1. 先创建一个沙盒
        create_resp = test_client.post(
            "/api/sandboxes",
            json={"name": "Existing Sandbox", "graph_collection": linear_collection.model_dump()}
        )
        assert create_resp.status_code == 201
        sandbox_id = create_resp.json()["id"]

        # 2. 构造一个具有相同 ID 的导出包
        # (我们手动构造，而不是真的去导出，这样更快)
        sandbox = {"id": sandbox_id, "name": "Duplicate Sandbox", "head_snapshot_id": None}
        manifest = {"package_type": "sandbox_archive", "entry_point": "sandbox.json"}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("data/sandbox.json", json.dumps(sandbox))
            # 为了通过验证，至少需要一个快照
            snapshot = {"id": str(uuid4()), "sandbox_id": sandbox_id, "graph_collection": linear_collection.model_dump()}
            zf.writestr(f"data/snapshots/{snapshot['id']}.json", json.dumps(snapshot))

        # 3. 尝试导入
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("conflict.hevno.zip", zip_buffer.getvalue(), "application/zip")}
        )
        assert import_resp.status_code == 409
        assert "already exists" in import_resp.json()["detail"]
```

### core_memoria/tests/conftest.py
```
# plugins/core_memoria/tests/conftest.py (新文件)

import pytest_asyncio
from typing import AsyncGenerator, Tuple

# 从平台核心导入组件
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.tasks import BackgroundTaskManager

# 从平台核心导入接口
from backend.core.contracts import (
    Container as ContainerInterface,
    HookManager as HookManagerInterface
)

# 从依赖插件导入注册函数和组件
from plugins.core_engine.engine import ExecutionEngine as ExecutionEngineInterface
from plugins.core_engine import register_plugin as register_engine_plugin
from plugins.core_engine.engine import ExecutionEngine # 导入具体实现以进行实例化
from plugins.core_llm import register_plugin as register_llm_plugin

# 从当前插件导入注册函数
from .. import register_plugin as register_memoria_plugin


@pytest_asyncio.fixture
async def memoria_test_engine() -> AsyncGenerator[Tuple[ExecutionEngineInterface, ContainerInterface, HookManagerInterface], None]:
    """
    一个专门为 core-memoria 插件测试定制的 fixture。
    
    它只加载运行 memoria 功能所必需的插件 (core-engine, core-llm, core-memoria)，
    从而提供一个轻量级、隔离的测试环境。
    """
    # 1. 初始化平台核心服务
    container = Container()
    hook_manager = HookManager()
    
    # 手动创建并注册后台任务管理器
    task_manager = BackgroundTaskManager(container, max_workers=2)
    container.register("task_manager", lambda: task_manager, singleton=True)
    container.register("hook_manager", lambda: hook_manager, singleton=True)
    container.register("container", lambda: container, singleton=True)

    # 2. 手动按依赖顺序注册所需插件
    #    这模拟了 PluginLoader 的行为，但范围更小。
    register_engine_plugin(container, hook_manager)
    register_llm_plugin(container, hook_manager)
    register_memoria_plugin(container, hook_manager) # 注册我们自己

    # 3. 手动触发服务初始化钩子
    #    这对于 core-engine 填充其运行时注册表至关重要。
    await hook_manager.trigger('services_post_register', container=container)

    # 4. 从容器中解析出最终配置好的引擎实例
    engine = container.resolve("execution_engine")
    
    # 启动后台任务管理器
    task_manager.start()

    # 5. Yield 元组，供测试使用
    yield engine, container, hook_manager
    
    # 6. 测试结束后，优雅地清理
    await task_manager.stop()
```

### core_memoria/tests/__init__.py
```

```

### core_memoria/tests/test_memoria.py
```
# tests/plugins/test_memoria.py

import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from backend.core.contracts import (
    Sandbox, 
    StateSnapshot, 
    GraphCollection, 
    ExecutionContext, 
    SharedContext, 
    Container, 
    BackgroundTaskManager
)
from plugins.core_memoria.runtimes import MemoriaAddRuntime, MemoriaQueryRuntime
from plugins.core_memoria.tasks import run_synthesis_task
from plugins.core_llm.models import LLMResponse, LLMResponseStatus

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


# --- Fixtures for creating mock contexts ---

@pytest.fixture
def mock_container() -> MagicMock:
    """A mock DI container."""
    container = MagicMock(spec=Container)
    # Configure resolve to return mocks for required services
    container.resolve.side_effect = lambda name: {
        "llm_service": AsyncMock(),
        "sandbox_store": MagicMock(spec=dict), ### <-- FIX 1: Must be a mock, not a real dict.
        "snapshot_store": MagicMock(),
        "task_manager": AsyncMock(spec=BackgroundTaskManager)
    }.get(name)
    return container

@pytest.fixture
def mock_shared_context(mock_container) -> SharedContext:
    """A mock shared context for execution."""
    # Note: This fixture now depends on mock_container so services can be attached.
    shared = SharedContext(
        world_state={},
        session_info={},
        global_write_lock=asyncio.Lock(),
        # The `services` attribute on the real SharedContext is a DotAccessibleDict.
        # For testing, a simple MagicMock is sufficient to attach mocked services.
        services=MagicMock()
    )
    shared.services.task_manager = mock_container.resolve("task_manager")
    return shared

@pytest.fixture
def mock_exec_context(mock_shared_context) -> ExecutionContext: ### <-- FIX 2: Removed mock_container from signature, it's now handled by mock_shared_context
    """A mock full execution context for runtimes."""
    sandbox_id = uuid.uuid4()
    # A minimal valid graph collection
    graph_collection = GraphCollection.model_validate({"main": {"nodes": []}})
    snapshot = StateSnapshot(sandbox_id=sandbox_id, graph_collection=graph_collection)

    return ExecutionContext(
        shared=mock_shared_context,
        initial_snapshot=snapshot,
        hook_manager=AsyncMock()
    )


# --- Test Cases ---

async def test_memoria_add_and_query(mock_exec_context):
    """
    Test Case 1: (Happy Path)
    Verify that adding a memory entry correctly updates the world state,
    and that a subsequent query can retrieve it.
    """
    # --- Arrange ---
    add_runtime = MemoriaAddRuntime()
    query_runtime = MemoriaQueryRuntime()
    
    add_config = {"stream": "events", "content": "The player entered the village."}
    
    # --- Act ---
    add_result = await add_runtime.execute(add_config, mock_exec_context)
    
    # --- Assert ---
    # 1. Assert add_runtime output
    assert "output" in add_result
    assert add_result["output"]["content"] == "The player entered the village."

    # 2. Assert world_state was modified
    world_state = mock_exec_context.shared.world_state
    assert "memoria" in world_state
    assert world_state["memoria"]["events"]["entries"][0]["content"] == "The player entered the village."

    # 3. Assert query_runtime can retrieve the data
    query_config = {"stream": "events"}
    query_result = await query_runtime.execute(query_config, mock_exec_context)
    
    assert "output" in query_result
    assert len(query_result["output"]) == 1
    assert query_result["output"][0]["content"] == "The player entered the village."


async def test_synthesis_task_trigger(mock_exec_context):
    """
    Test Case 2:
    Verify that the background synthesis task is triggered when the count is met.
    """
    # --- Arrange ---
    runtime = MemoriaAddRuntime()
    task_manager_mock = mock_exec_context.shared.services.task_manager

    # Configure world state for auto-synthesis
    mock_exec_context.shared.world_state["memoria"] = {
        "__global_sequence__": 0,
        "story": {
            "config": {
                "auto_synthesis": {
                    "enabled": True,
                    "trigger_count": 2, # Trigger after 2 entries
                }
            },
            "entries": [],
            "synthesis_trigger_counter": 0
        }
    }

    # --- Act & Assert ---
    # First call: should not trigger task
    await runtime.execute({"stream": "story", "content": "Event 1"}, mock_exec_context)
    task_manager_mock.submit_task.assert_not_called()
    assert mock_exec_context.shared.world_state["memoria"]["story"]["synthesis_trigger_counter"] == 1

    # Second call: should trigger task
    await runtime.execute({"stream": "story", "content": "Event 2"}, mock_exec_context)
    
    # Assert task was submitted
    task_manager_mock.submit_task.assert_called_once()
    
    # Assert the arguments passed to submit_task are correct
    call_args, _ = task_manager_mock.submit_task.call_args
    assert call_args[0] == run_synthesis_task # The function itself
    assert call_args[1] == mock_exec_context.initial_snapshot.sandbox_id # sandbox_id
    assert call_args[2] == "story" # stream_name
    assert isinstance(call_args[3], dict) # synthesis_config
    assert len(call_args[4]) == 2 # entries_to_summarize_dicts
    assert call_args[4][0]["content"] == "Event 1"


async def test_run_synthesis_task_success(mock_container):
    """
    Test Case 3: (End-to-End for the task)
    Verify that the background task correctly calls the LLM,
    creates a new snapshot, and updates the sandbox head.
    """
    # --- Arrange ---
    # Setup mock services from the container
    llm_service_mock = mock_container.resolve("llm_service")
    sandbox_store_mock = mock_container.resolve("sandbox_store")
    snapshot_store_mock = mock_container.resolve("snapshot_store")

    # Mock LLM response
    llm_service_mock.request.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="A summary of events.")

    # Setup initial state
    sandbox_id = uuid.uuid4()
    initial_snapshot_id = uuid.uuid4()
    
    initial_snapshot = StateSnapshot(
        id=initial_snapshot_id,
        sandbox_id=sandbox_id,
        graph_collection=GraphCollection.model_validate({"main": {"nodes": []}}),
        world_state={
            "memoria": {
                "__global_sequence__": 2,
                "journal": {
                    "config": {"auto_synthesis": {"enabled": True, "trigger_count": 2}},
                    "entries": [
                        {"id": uuid.uuid4(), "sequence_id": 1, "content": "Entry 1", "level": "event", "tags":[]},
                        {"id": uuid.uuid4(), "sequence_id": 2, "content": "Entry 2", "level": "event", "tags":[]},
                    ],
                    "synthesis_trigger_counter": 2 # Counter is high
                }
            }
        }
    )
    sandbox = Sandbox(id=sandbox_id, name="Test Sandbox", head_snapshot_id=initial_snapshot_id)

    # Populate stores
    snapshot_store_mock.get.return_value = initial_snapshot
    sandbox_store_mock.get.return_value = sandbox

    # Task arguments (as they would be passed from the runtime)
    synthesis_config_dict = {"model": "gemini/gemini-pro", "level": "summary", "prompt": "{events_text}", "enabled": True, "trigger_count": 2}
    entries_to_summarize_dicts = [e.model_dump() for e in initial_snapshot.world_state["memoria"]["journal"]["entries"]]

    # --- Act ---
    await run_synthesis_task(
        mock_container,
        sandbox_id,
        "journal",
        synthesis_config_dict,
        entries_to_summarize_dicts
    )

    # --- Assert ---
    # 1. LLM was called correctly
    llm_service_mock.request.assert_awaited_once_with(
        model_name="gemini/gemini-pro",
        prompt="- Entry 1\n- Entry 2"
    )

    # 2. A new snapshot was saved
    snapshot_store_mock.save.assert_called_once()
    saved_snapshot: StateSnapshot = snapshot_store_mock.save.call_args[0][0]

    # 3. The new snapshot has the correct data
    assert saved_snapshot.id != initial_snapshot_id
    assert saved_snapshot.parent_snapshot_id == initial_snapshot_id
    
    # 4. The world state in the new snapshot contains the summary
    new_memoria = saved_snapshot.world_state["memoria"]
    assert len(new_memoria["journal"]["entries"]) == 3
    summary_entry = new_memoria["journal"]["entries"][-1]
    assert summary_entry["content"] == "A summary of events."
    assert summary_entry["level"] == "summary"
    assert summary_entry["sequence_id"] == 3 # Sequence ID was incremented

    # 5. The sandbox's head was updated to point to the new snapshot
    assert sandbox.head_snapshot_id == saved_snapshot.id
```

### core_llm/providers/__init__.py
```

```

### core_llm/providers/gemini.py
```
# plugins/core_llm/providers/gemini.py

from typing import Any
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from google.generativeai import types as generation_types

# --- 核心修改: 导入路径修正 ---
from .base import LLMProvider
from ..models import (
    LLMResponse,
    LLMError,
    LLMResponseStatus,
    LLMErrorType,
)
from ..registry import provider_registry

@provider_registry.register("gemini", key_env_var="GEMINI_API_KEYS")
class GeminiProvider(LLMProvider):
    """
    针对 Google Gemini API 的 LLMProvider 实现。
    """

    async def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        api_key: str,
        **kwargs: Any
    ) -> LLMResponse:
        """
        使用 Gemini API 生成内容。
        """
        try:
            # 每次调用都独立配置，以支持多密钥轮换
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(model_name)

            # 提取支持的生成配置
            generation_config = {
                "temperature": kwargs.get("temperature"),
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
                "max_output_tokens": kwargs.get("max_tokens"),
            }
            # 清理 None 值
            generation_config = {k: v for k, v in generation_config.items() if v is not None}

            response: generation_types.GenerateContentResponse = await model.generate_content_async(
                contents=prompt,
                generation_config=generation_config
            )

            # 检查是否因安全策略被阻止
            # 这是 Gemini 的“软失败”，不会抛出异常
            if not response.parts:
                if response.prompt_feedback.block_reason:
                    error_message = f"Request blocked due to {response.prompt_feedback.block_reason.name}"
                    return LLMResponse(
                        status=LLMResponseStatus.FILTERED,
                        model_name=model_name,
                        error_details=LLMError(
                            error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                            message=error_message,
                            is_retryable=False # 内容过滤不应重试
                        )
                    )

            # 提取 token 使用情况
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }
            
            return LLMResponse(
                status=LLMResponseStatus.SUCCESS,
                content=response.text,
                model_name=model_name,
                usage=usage
            )

        except generation_types.StopCandidateException as e:
            # 这种情况也属于内容过滤
            return LLMResponse(
                status=LLMResponseStatus.FILTERED,
                model_name=model_name,
                error_details=LLMError(
                    error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                    message=f"Generation stopped due to safety settings: {e}",
                    is_retryable=False,
                )
            )
        # 注意: 其他 google_exceptions 将会在此处被抛出，由上层服务捕获并传递给 translate_error

    def translate_error(self, ex: Exception) -> LLMError:
        """
        将 Google API 的异常转换为标准的 LLMError。
        """
        error_details = {"provider": "gemini", "exception": type(ex).__name__, "message": str(ex)}

        if isinstance(ex, google_exceptions.PermissionDenied):
            return LLMError(
                error_type=LLMErrorType.AUTHENTICATION_ERROR,
                message="Invalid API key or insufficient permissions.",
                is_retryable=False,  # 使用相同密钥重试是无意义的
                provider_details=error_details,
            )
        
        if isinstance(ex, google_exceptions.ResourceExhausted):
            return LLMError(
                error_type=LLMErrorType.RATE_LIMIT_ERROR,
                message="Rate limit exceeded. Please try again later or use a different key.",
                is_retryable=False,  # 对于单个密钥，应立即切换，而不是等待重试
                provider_details=error_details,
            )

        if isinstance(ex, google_exceptions.InvalidArgument):
            return LLMError(
                error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                message=f"Invalid argument provided to the API. Check model name and parameters. Details: {ex}",
                is_retryable=False,
                provider_details=error_details,
            )

        if isinstance(ex, (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)):
            return LLMError(
                error_type=LLMErrorType.PROVIDER_ERROR,
                message="The service is temporarily unavailable or the request timed out. Please try again.",
                is_retryable=True,
                provider_details=error_details,
            )
            
        if isinstance(ex, google_exceptions.GoogleAPICallError):
            return LLMError(
                error_type=LLMErrorType.NETWORK_ERROR,
                message=f"A network-level error occurred while communicating with Google API: {ex}",
                is_retryable=True,
                provider_details=error_details,
            )

        return LLMError(
            error_type=LLMErrorType.UNKNOWN_ERROR,
            message=f"An unknown error occurred with the Gemini provider: {ex}",
            is_retryable=False, # 默认未知错误不可重试，以防造成死循环
            provider_details=error_details,
        )
```

### core_llm/providers/base.py
```
# backend/llm/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..models import LLMResponse, LLMError


class LLMProvider(ABC):
    """
    一个抽象基-类，定义了所有 LLM 提供商适配器的标准接口。
    """

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        api_key: str,
        **kwargs: Any
    ) -> LLMResponse:
        """
        与 LLM 提供商进行交互以生成内容。

        这个方法必须处理所有可能的成功和“软失败”（如内容过滤）场景，
        并将它们封装在标准的 LLMResponse 对象中。
        如果发生无法处理的硬性错误（如网络问题、认证失败），它应该抛出原始异常，
        以便上层服务可以捕获并使用 translate_error 进行处理。

        :param prompt: 发送给模型的提示。
        :param model_name: 要使用的具体模型名称 (e.g., 'gemini-1.5-pro-latest')。
        :param api_key: 用于本次请求的 API 密钥。
        :param kwargs: 其他特定于提供商的参数 (e.g., temperature, max_tokens)。
        :return: 一个标准的 LLMResponse 对象。
        :raises Exception: 任何未被处理的、需要由 translate_error 解析的硬性错误。
        """
        pass

    @abstractmethod
    def translate_error(self, ex: Exception) -> LLMError:
        """
        将特定于提供商的原始异常转换为我们标准化的 LLMError 对象。

        这个方法是解耦的关键，它将具体的 SDK 错误与我们系统的内部错误处理逻辑分离开。

        :param ex: 从 generate 方法捕获的原始异常。
        :return: 一个标准的 LLMError 对象。
        """
        pass
```

### core_llm/tests/__init__.py
```

```

### core_llm/tests/test_llm_gateway.py
```
# plugins/core_llm/tests/test_llm_gateway.py

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# 从本插件内部导入所有需要测试的类和模型
from plugins.core_llm.models import (
    LLMResponse, LLMError, LLMResponseStatus, LLMErrorType, LLMRequestFailedError
)
from plugins.core_llm.manager import CredentialManager, KeyPoolManager
from plugins.core_llm.service import LLMService
from plugins.core_llm.registry import ProviderRegistry, provider_registry as global_provider_registry

# 为了测试的隔离性，我们清除全局注册表
@pytest.fixture(autouse=True)
def isolated_provider_registry():
    backup_providers = global_provider_registry._providers.copy()
    backup_info = global_provider_registry._provider_info.copy()
    global_provider_registry._providers.clear()
    global_provider_registry._provider_info.clear()
    yield
    global_provider_registry._providers = backup_providers
    global_provider_registry._provider_info = backup_info

@pytest.fixture
def credential_manager(monkeypatch) -> CredentialManager:
    monkeypatch.setenv("GEMINI_API_KEYS", "test_key_1, test_key_2")
    return CredentialManager()

@pytest.fixture
def key_pool_manager(credential_manager: CredentialManager) -> KeyPoolManager:
    manager = KeyPoolManager(credential_manager)
    manager.register_provider("gemini", "GEMINI_API_KEYS")
    return manager

# 【修复】这个 fixture 现在只创建 LLMService，不再 mock provider
# 因为我们将在测试函数内部 patch 更高层次的方法
@pytest.fixture
def llm_service(key_pool_manager: KeyPoolManager) -> LLMService:
    # 注册一个空的 provider registry，因为我们不会真的调用它
    return LLMService(
        key_manager=key_pool_manager, 
        provider_registry=ProviderRegistry(), 
        max_retries=2 # 1 initial + 1 retry = 2 total attempts
    )

@pytest.mark.asyncio
class TestLLMServiceIntegration:
    """对 LLMService 的集成测试，测试其重试和故障转移的核心逻辑。"""

    async def test_request_success_on_first_try(self, llm_service: LLMService):
        """测试在第一次尝试就成功时，方法能正确返回。"""
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        
        # 使用 patch 直接模拟 _attempt_request 的行为
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            mock_attempt.return_value = success_response
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            assert response == success_response
            mock_attempt.assert_awaited_once()

    async def test_retry_on_provider_error_and_succeed(self, llm_service: LLMService):
        """
        【修复后】测试当 _attempt_request 第一次失败、第二次成功时，tenacity 是否正确重试。
        """
        retryable_error = LLMRequestFailedError(
            "A retryable error occurred", 
            last_error=LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True)
        )
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")

        # 直接 patch _attempt_request，并让它按顺序产生效果
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            mock_attempt.side_effect = [
                retryable_error,
                success_response
            ]
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            # 验证最终结果是成功的响应
            assert response == success_response
            # 验证 _attempt_request 被调用了两次（1次初始 + 1次重试）
            assert mock_attempt.call_count == 2


    async def test_final_failure_after_all_retries(self, llm_service: LLMService):
        """
        【修复后】测试当 _attempt_request 总是失败时，是否在耗尽重试次数后抛出最终异常。
        """
        retryable_error = LLMRequestFailedError(
            "A persistent retryable error",
            last_error=LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True)
        )
        
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            # 让 mock 的方法总是抛出可重试的异常
            mock_attempt.side_effect = retryable_error
            
            with pytest.raises(LLMRequestFailedError) as exc_info:
                await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            # 验证最终抛出的异常包含了总结性的信息
            assert "failed permanently after 2 attempt(s)" in str(exc_info.value)
            
            # 验证 _attempt_request 被调用了两次（1次初始 + 1次重试）
            assert mock_attempt.call_count == 2
```
