
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

参见专门文档


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







# Hevno 宏系统：可编程的配置

欢迎来到 Hevno 宏系统，这是让您的静态图定义变得鲜活、动态和智能的核心引擎。我们摒弃了复杂的模板语言，转而拥抱一种更强大、更直观的理念：

> **在配置中，像写 Python 一样思考。**

宏系统允许您在图定义（JSON 文件）的字符串值中直接嵌入可执行的 Python 代码。它不仅能用于简单的变量替换，更是实现动态逻辑、状态操作和世界演化的瑞士军刀。

## 1. 核心理念：自动化与控制权的完美平衡

Hevno 宏系统的设计哲学，旨在为您提供最流畅的开发体验，同时保留在关键时刻的完全控制权。

### 1.1 唯一的语法：`{{ ... }}`

您只需要记住一种语法。任何被双大括号 `{{ ... }}` 包裹起来的内容，都会被 Hevno 引擎视为一段可执行的 Python 代码。

```json
// 简单求值
{ "value": "{{ 1 + 1 }}" }

// 访问世界状态
{ "prompt": "{{ f'你好，{world.player_name}！' }}" }

// 执行复杂逻辑
{
  "script": "{{
    if world.player.is_tired:
        world.player.energy -= 10
    else:
        world.player.energy += 5
  }}"
}
```

### 1.2 智能的执行模型：预处理与二次执行

#### a) 全局预处理（自动化核心）

**这是您在 95% 的时间里需要了解的全部内容。**

在任何一个节点即将执行其内部的运行时（Runtime）**之前**，引擎会自动**遍历**该节点的整个 `data` 配置。当它遇到一个值为 `{{...}}` 宏格式的字符串时，它会**执行一次**该宏，并用其返回结果**替换**掉原有的宏字符串。这个求值过程是**单遍的**，引擎不会对宏的返回结果进行二次求值

这意味着：
1.  **所见即所得**：当您的运行时（如 `llm.default`）拿到 `prompt` 参数时，它**永远**是最终的、计算好的字符串，而不是一个模板。
2.  **无需模板运行时**：您再也不需要在运行时管道里手动添加 `system.template` 这样的东西了。引擎已经为您自动处理好了一切。
3.  **隐式返回值**: 如果您的代码块最后一行是一个表达式（例如一个数字、一个字符串、一个函数调用），它的结果将成为这个宏的值。否则，其值为 `None`。

#### b) `system.execute` 运行时（高级控制）

这是一个特殊的运行时，只在您需要**执行在运行时中途才生成的代码**时使用。最典型的场景就是执行由 LLM 返回的指令。我们将在高级指南中详细介绍。

## 2. 入门指南 (为所有用户)

## 2.1 访问核心数据：您的世界交互窗口

宏最强大的能力，在于它能访问和操纵 Hevno 引擎在执行图过程中的所有内部状态。您可以把宏想象成一个开在节点配置上的“开发者控制台”，能让您直接与引擎的“记忆”互动。

在 `{{ ... }}` 内部，您可以访问一个包含了**所有可用上下文信息**的全局命名空间。这包括但不限于：

*   **持久化世界状态 (`world`)**: 这是您的沙盒（Sandbox）的长期记忆。所有需要跨越多个执行步骤、长期存在的数据都应存放在这里。您可以读取它，也可以向其中写入新数据或修改现有数据，这些改动将被永久记录在下一个状态快照中。
    *   **用途**: 存储玩家属性（如 `world.player.hp`）、任务进度、世界环境、角色关系等。
    *   **示例 (读取)**: `{{ f"玩家当前生命值：{world.player.hp}" }}`
    *   **示例 (写入)**: `{{ world.quest_log.append('新任务：击败恶龙') }}`

*   **已完成节点的结果 (`nodes`)**: 这是一个字典，包含了所有在当前节点执行之前，已经成功完成的节点所产生的结果。这是实现节点间数据流动的关键。
    *   **用途**: 将一个节点的输出作为另一个节点的输入。
    *   **示例**: `{{ nodes.get_character_name.output.upper() }}`

*   **本次运行的临时数据 (`run`)**: 这是一个临时存储区域，其生命周期仅限于**单次**图的执行。执行结束后，其中的所有数据都会被丢弃。它非常适合存放那些“用完即弃”的中间变量。
    *   **用途**: 存储触发本次运行的外部输入（如用户的聊天消息）、本次运行中途的临时计算结果等。
    *   **示例**: `{{ run.trigger_input.user_message }}`

*   **会话元信息 (`session`)**: 包含了关于整个交互会话的全局信息，例如会话开始的时间、总共执行的回合数等。
    *   **用途**: 用于记录、调试或实现与时间相关的逻辑。
    *   **示例**: `{{ f"当前是第 {session.turn_count} 回合" }}`

**核心原则**:
> 您可以通过宏访问到驱动图执行所需的一切上下文数据。引擎负责将这些数据在正确的时间点注入到宏的执行环境中。

这种设计为您提供了极大的灵活性，让您可以根据需要自由地组合和操纵来自不同层级的数据，以实现复杂的动态行为。随着 Hevno 引擎的演进，可能会有更多专有、便捷的上下文对象被加入，但它们都会遵循这一核心访问模式。

### 2.2 “开箱即用”的工具箱

我们预置了一些标准 Python 模块，您无需 `import` 即可直接使用：`random`, `math`, `datetime`, `json`, `re`。

*   掷一个20面的骰子: `{{ random.randint(1, 20) }}`
*   从列表中随机选一个: `{{ random.choice(['红色', '蓝色', '绿色']) }}`

### 2.3 实用示例

#### 示例1：动态生成 NPC 对话

根据玩家的声望 (`world.player_reputation`)，NPC 会有不同的反应。

```json
{
  "id": "npc_greeting",
  "data": {
    "runtime": "llm.default", // 注意：不再需要 template 运行时
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
```

#### 示例2：处理玩家伤害

```json
{
  "id": "take_damage",
  "data": {
    "script": "{{
      damage_amount = run.trigger_input.damage
      world.player_hp -= damage_amount
      world.battle_log.append(f'玩家受到了 {damage_amount} 点伤害。')
    }}"
  }
}
```
**说明**: 这个节点甚至不需要 `runtime` 字段。在预处理阶段，`script` 里的宏被执行，`world` 状态被修改。之后，由于没有运行时，节点执行就结束了。

## 3. 高级指南 (为开发者)

### 3.1 宏的转义与二次执行

这是宏系统最强大的功能之一，允许您创建能与 LLM 进行深度交互的代理。

**场景**: 您想让 LLM 能够通过返回特定指令来操纵世界状态。

#### **步骤 1: 发送“转义”的指令给 LLM**

您需要向 LLM 发送包含 `{{...}}` 语法的提示，但又不希望它在发送前被引擎执行。诀窍是**在宏内部使用字符串字面量**。

```json
{
  "id": "instruct_llm",
  "data": {
    "runtime": "llm.default",
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
引擎在预处理此节点时，会执行 f-string，生成一个包含 `{{ world.player_hp = 100 }}` **文本**的字符串，然后将其发送给 LLM。

#### **步骤 2: 执行 LLM 返回的指令**

假设上一步的 LLM 返回了字符串 `"{{ world.player_energy = 100 }}"`。这个字符串现在存储在 `nodes.instruct_llm.llm_output` 中。它只是一个普通的字符串，不会自动执行。

要执行它，我们需要在下一个节点使用 `system.execute` 运行时。

```json
{
  "id": "execute_llm_command",
  "data": {
    // 1. 在预处理阶段，这个宏被执行，
    //    'code' 的值变成了字符串 "{{ world.player_energy = 100 }}"
    "code": "{{ nodes.instruct_llm.llm_output }}",
    
    // 2. 在运行时阶段，system.execute 被调用
    "runtime": "system.execute"
  }
}
```
`system.execute` 运行时会接收到 `code` 字段的值，并对其进行**二次求值**，从而真正执行 `world.player_energy = 100`，修改世界状态。

### 3.2 动态定义函数与 `import`

您可以 `import` 任何库，或在 `world` 对象上动态创建函数，以构建可复用的逻辑或实现世界的自我演化。

```json
{
  "id": "teach_world_new_trick",
  "data": {
    "script": "{{
      import numpy as np # 导入外部库

      def calculate_weighted_average(values, weights):
          return np.average(values, weights=weights)

      if 'utils' not in world: world['utils'] = {}
      world.utils.weighted_avg = calculate_weighted_average
    }}"
  }
}
```
在后续节点中，您就可以直接调用 `{{ world.utils.weighted_avg(...) }}`。

### 3.3 宏与依赖推断

*   **自动推断**: 使用 `{{ nodes.some_node_id... }}` 会自动建立依赖关系。`some_node_id` 必须是**静态字面量**。
*   **手动声明**: 对于无法自动推断的动态依赖（如 `nodes[world.var]`），请使用 `depends_on: ["node_A", "node_B"]` 字段来手动声明。

---

## 4. 内部实现概要 (为引擎开发者)

1.  **统一预处理**: `ExecutionEngine._execute_node` 在执行任何运行时之前，会调用 `evaluation.evaluate_data`。此函数递归地查找并执行节点 `data` 中的所有 `{{...}}` 宏。
2.  **`python_executor`**: `evaluation` 模块的核心依赖。它使用 `ast` 模块解析 Python 代码，智能地将最后一个表达式转换为 `_result` 赋值，然后通过 `exec()` 统一执行。这避免了 `eval`/`exec` 的分支，并提供了强大的副作用与返回值能力。
3.  **运行时纯粹性**: 经过预处理后，所有运行时接收到的 `pipeline_state` 和 `step_input` 都是纯粹、已求值的 Python 对象。这极大地简化了运行时的设计和测试。
4.  **`system.execute`**：它是一个标准的运行时。其特殊之处在于，它在自己的实现内部再次调用了 `evaluation.evaluate_expression`，从而实现了可控的“二次求值”循环。