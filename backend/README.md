
# Hevno Engine

**一个为构建复杂、持久、可交互的 AI 世界而生的状态图执行引擎。**

---

## 1. 我们的愿景：从“聊天机器人”到“世界模拟器”

当前的语言模型（LLM）应用，大多停留在“一问一答”的聊天机器人模式，这极大地限制了 LLM 的潜能。我们相信，LLM 的未来在于构建**复杂、持久、可交互的动态世界**。

想象一下：

*   一个能与你玩《是，大臣》策略游戏的 AI，其中每个角色（哈克、汉弗莱、伯纳）都是一个独立的、有自己动机和知识库的 LLM 实例。
*   一个能让你沉浸式体验的互动小说，你的每一个决定都会被记录，并动态地解锁、修改甚至创造新的故事线和世界规则。

这些不再是简单的“提示工程”，而是**状态管理**、**并发控制**和**动态逻辑编排**的复杂工程问题。

**Hevno Engine 的诞生，正是为了解决这个问题。** 它的核心使命是提供一个强大的后端框架，让开发者能够轻松地将离散的 LLM 调用，编织成有记忆、能演化、可回溯的智能代理和交互式世界。我们不是在构建另一个聊天应用，我们是在构建一个**创造世界的引擎**。

## 2. 核心设计哲学

我们的架构选择基于三大核心哲学：

### 2.1 哲学一：拥抱配置，拒绝类型爆炸

> **"Everything is data, behavior is configuration."**

我们摒弃了通过增加新节点“类型”来扩展功能的传统模式。在 Hevno 中：

*   **极简的原子单元**: 系统中只有一个通用的 `GenericNode`。
*   **行为由配置驱动**: 节点的具体行为完全由其 `data` 负载中的 `runtime` 字段指定。一个 `runtime` 是一个可执行的功能单元。通过将多个 `runtime` 放入一个数组，可以构建出强大的**运行时管道（Runtime Pipeline）**。

**旧方式 (我们避免的):**
```json
{"type": "LLMNode", "prompt": "..."}
{"type": "CodeNode", "code": "..."}
```

**Hevno 的方式:**
```json
// 简单 LLM 调用
{
  "id": "simple_llm",
  "data": {
    "runtime": "llm.default", 
    "prompt": "你好，世界！"
  }
}

// 先模板渲染，再调用 LLM 的复杂行为
{
  "id": "advanced_llm",
  "data": {
    "runtime": ["system.template", "llm.default"], 
    "template": "根据角色的心情 '{{ world.character_mood }}'，生成一句问候。"
  }
}
```
这种设计将功能正交分解，提供了无与伦比的灵活性和可组合性。

### 2.2 哲学二：状态先行，计算短暂

> **"State is permanent, execution is ephemeral."**

一个交互式模拟世界的核心恰恰是“状态”。我们构建了一个以状态为核心的架构：

*   **沙盒 (`Sandbox`)**: 代表一个完整的、隔离的交互环境（例如，一局游戏、一个项目）。
*   **不可变快照 (`StateSnapshot`)**: 我们不直接修改状态。每一次交互（如图执行）都会产生一个全新的、完整的状态快照。这包含了当时所有的持久化变量 (`world_state`) 和驱动逻辑的图 (`graph_collection`)。
*   **引擎的角色**: `ExecutionEngine` 本身是无状态的。它的工作是接收一个旧的 `StateSnapshot`，执行计算，然后生成一个新的 `StateSnapshot`。它是一个纯粹的**状态转换函数**。

**执行流程示意：**
```
                                        +---------------------+
                                        |  Execution Engine   |
(Old StateSnapshot) ------------------> | (State Transition)  | ------------------> (New StateSnapshot)
  - world_state                         |                     |                       - world_state (updated)
  - graph_collection                    |     run_graph()     |                       - graph_collection (possibly evolved)
                                        +---------------------+
```

这种架构天然地带来了巨大的好处：
1.  **完美的回溯能力**: “读档”操作变成了简单地将沙盒的指针指向一个历史快照。
2.  **健壮的并发与调试**: 不可变性消除了大量的并发问题，并使得追踪状态变化变得异常简单。
3.  **动态的逻辑演化**: 因为图的定义本身也是状态的一部分，所以图可以被它自己执行的逻辑所修改（例如，一个节点可以执行 `system.set_world_var` 来更新 `world_state` 中存储的图定义），实现世界的“自我进化”。

### 2.3 哲学三：约定优于配置，隐式推断依赖

> **"Be smart, so the user doesn't have to be."**

我们力求为图的创建者提供最流畅的体验，减少样板代码和手动配置。

*   **无边图 (`Edgeless Graph`)**: 在我们的图定义中，你找不到 `edges` 字段。
*   **宏引用即依赖**: 当一个节点在其配置中通过宏 `{{ nodes.A.output }}` 引用了另一个节点 `A` 时，引擎会自动建立一条从 `A` 到当前节点的执行依赖。

这种设计将开发者的精力从繁琐的工程细节中解放出来，让他们能专注于设计智能体的行为逻辑。

---

## 3. 图定义格式与核心概念

### 3.1 顶层结构：图集合 (Graph Collection)

一个完整的工作流定义是一个 JSON 对象，其 `key` 为图的名称，`value` 为图的定义。

-   **约定入口图的名称必须为 `"main"`**。
-   这允许多个可复用的图存在于同一个配置文件中。

**示例:**
```json
{
  "main": {
    "nodes": [
      // ... 主图的节点 ...
    ]
  },
  "process_character_arc": {
    "nodes": [
      // ... 一个可复用子图的节点 ...
    ]
  }
}
```

### 3.2 节点 (Node)

节点是图的基本执行单元。

```json
{
  "id": "unique_node_id_within_graph",
  "data": {
    "runtime": "runtime_name"_or_["runtime_A", "runtime_B"],
    // ... 其他 key-value pairs 作为运行时的配置 ...
  }
}
```

### 3.3 宏模板与依赖推断

引擎使用 **Jinja2** 风格的宏 `{{ ... }}` 来实现动态值和依赖推断。

-   **依赖推断**: 任何形如 `{{ nodes.<node_id>.<...> }}` 的引用都会自动建立从 `<node_id>` 到当前节点的依赖关系。
-   **可用上下文对象**: 在宏模板中，你可以访问以下核心对象：
    *   `nodes`: 一个字典，包含了所有已成功执行的节点的结果。例如: `{{ nodes.get_story_idea.output }}`。
    *   `world`: 一个字典，代表了沙盒的持久化状态，跨执行步骤存在。例如: `{{ world.global_story_setting }}`。
    *   `run`: 一个字典，包含了本次执行的临时变量，执行结束后会被丢弃。例如: `{{ run.trigger_input.user_message }}`。
    *   `session`: 一个字典，包含了关于会话的元信息。例如: `{{ session.start_time }}`。
-   **重要限制**: 用于依赖推断的 `<node_id>` **目前必须是静态的字面量字符串**。动态引用（如 `{{ nodes[world.dynamic_id] }}`）无法在执行前建立依赖图。

---

## 4. 核心运行时详解

### 4.1 `system.call`: 子图调用

`call` 运行时用于实现非迭代式的、单一的子图调用，是代码复用的基础。

#### **调用格式**
```json
{
  "id": "process_main_character",
  "data": {
    "runtime": "system.call",
    "graph": "process_character_arc",
    "using": {
      "character_input": "{{ nodes.main_character_provider.output }}",
      "global_context": "{{ world.story_setting }}"
    }
  }
}
```
-   `graph`: 要调用的子图的名称。
-   `using`: 一个字典，用于将当前图的数据**映射**到子图的**输入占位符**。
    -   在被调用的子图 (`process_character_arc`) 中，任何对未定义节点（如 `character_input`）的引用，都会被视作一个输入占位符。
-   **输出**: `call` 节点的输出就是被调用子图的**完整的最终状态字典**。下游节点可以通过 `{{ nodes.process_main_character.output.internal_summary_node.summary }}` 访问其内部结果。

### 4.2 `system.map`: 并行迭代 (Fan-out / Scatter-Gather)

`map` 运行时是实现并行迭代的核心。它将一个子图并发地应用到输入列表的每个元素上。

#### **调用格式**
```json
{
  "id": "map_all_characters",
  "data": {
    "runtime": "system.map",
    "list": "{{ nodes.data_provider.characters_list }}",
    "graph": "process_character_arc",
    "using": {
      "character_input": "{{ source.item }}",
      "iteration_index": "{{ source.index }}",
      "main_plot_point": "{{ nodes.main_plot_provider.output }}"
    },
    "collect": "{{ nodes.final_summary.output }}"
  }
}
```
-   `list`: 要迭代的列表。
-   `graph` 和 `using`: 与 `call` 类似，但 `using` 内部可以使用一个特殊的 `source` 对象。
-   **`source` 对象**: 这是一个特殊的、**只在 `using` 字段的宏表达式中有效**的对象：
    -   `source.item`: 当前正在迭代的列表元素。
    -   `source.index`: 当前迭代的从0开始的索引。
-   **输出聚合 (`collect`)**:
    -   **如果 `collect` 未提供 (默认)**: `map` 节点的输出是一个**列表**，每个元素是对应子图执行的**完整最终状态**。
    -   **如果 `collect` 已提供**: `map` 节点的输出是一个**扁平列表**，其元素是根据 `collect` 表达式从每个子图实例中提取的值。`collect` 表达式中的 `nodes` 指向其所在子图的内部节点。

---

## 5. API 端点速查

-   `POST /api/sandboxes`
    -   **功能**: 创建一个新沙盒。
    -   **Body**: `{ "graph_collection": { ... }, "initial_state": { ... } }`
-   `POST /api/sandboxes/{sandbox_id}/step`
    -   **功能**: 在沙盒的最新状态上执行一步。
    -   **Body**: `{ "user_input": { ... } }` (内容会注入到 `run.trigger_input`)
-   `GET /api/sandboxes/{sandbox_id}/history`
    -   **功能**: 获取一个沙盒的所有历史快照。
-   `PUT /api/sandboxes/{sandbox_id}/revert`
    -   **功能**: 将沙盒回滚到指定的历史快照。
    -   **Query Param**: `snapshot_id=<uuid>`