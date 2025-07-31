### models.py
```
# backend/models.py 
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

class GraphDefinition(BaseModel):
    """图定义，包含一个节点列表。"""
    nodes: List[GenericNode]

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

### README.md
```

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

我们的架构选择基于四大核心哲学：

### 2.1 哲学一：以运行时为中心，指令式地构建行为

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

### 2.2 哲学二：状态先行，计算短暂

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

### 2.3 哲学三：约定与配置相结合，智能推断与明确声明并存

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

### 2.4 哲学四：默认安全，并发无忧 (Safe by Default, Concurrently Sound)

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

## 3. 图定义格式与核心概念

### 3.1 顶层结构：图集合 (Graph Collection)

一个完整的工作流定义是一个 JSON 对象，其 `key` 为图的名称，`value` 为图的定义。

-   **约定入口图的名称必须为 `"main"`**。
-   这允许多个可复用的图存在于同一个配置文件中。

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

### 3.2 节点 (Node) 与指令 (Instruction)

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

### 3.3 Hevno 宏系统

`{{ ... }}` 语法允许您在 `config` 的字符串值中嵌入可执行的 Python 代码。引擎会在执行**每一个**指令**之前**，先对该指令的 `config` 进行宏求值。

这使得后一个指令可以访问前一个指令产生的状态。详情参见专门的宏系统文档。

---

## 4. 核心运行时详解

### 4.1 `system.call`: 子图调用

`call` 运行时用于实现非迭代式的、单一的子图调用，是代码复用的基础。

#### **调用格式**
```json
{
  "runtime": "system.call",
  "config": {
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
-   **输出**: `call` 指令的输出就是被调用子图的**完整的最终状态字典**。后续指令可以通过 `{{ pipe.output.internal_summary_node.summary }}` 访问其内部结果（`pipe` 对象代表了上一步的输出）。

### 4.2 `system.map`: 并行迭代 (Fan-out / Scatter-Gather)

`map` 运行时是实现并行迭代的核心。它将一个子图并发地应用到输入列表的每个元素上。

#### **调用格式**
```json
{
  "runtime": "system.map",
  "config": {
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
    -   **如果 `collect` 未提供 (默认)**: `map` 指令的输出是一个**列表**，每个元素是对应子图执行的**完整最终状态**。
    -   **如果 `collect` 已提供**: `map` 指令的输出是一个**扁平列表**，其元素是根据 `collect` 表达式从每个子图实例中提取的值。`collect` 表达式中的 `nodes` 指向其所在子图的内部节点。

---

## 5. API 端点速查

-   `POST /api/sandboxes`
    -   **功能**: 创建一个新沙盒。
    -   **Body**: `{ "graph_collection": { ... }, "initial_state": { ... } }`
-   `POST /api/sandboxes/{sandbox_id}/step`
    -   **功能**: 在沙盒的最新状态上执行一步。
    -   **Body**: `{ ... }` (内容会注入到 `run.trigger_input`)
-   `GET /api/sandboxes/{sandbox_id}/history`
    -   **功能**: 获取一个沙盒的所有历史快照。
-   `PUT /api/sandboxes/{sandbox_id}/revert`
    -   **功能**: 将沙盒回滚到指定的历史快照。
    -   **Query Param**: `snapshot_id=<uuid>`




# Hevno 宏系统：可编程的配置

欢迎来到 Hevno 宏系统，这是让您的静态图定义变得鲜活、动态和智能的核心引擎。我们摒弃了复杂的模板语言，转而拥抱一种更强大、更直观的理念：

> **在配置中，像写 Python 一样思考。**

宏系统允许您在图定义（JSON 文件）的字符串值中直接嵌入可执行的 Python 代码。它不仅能用于简单的变量替换，更是实现动态逻辑、状态操作和世界演化的瑞士军刀。

## 1. 核心理念：逐步求值，精确控制

Hevno 宏系统的设计哲学，旨在为您提供最流畅的开发体验，同时保留在关键时刻的完全控制权。

### 1.1 唯一的语法：`{{ ... }}`

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

### 1.2 智能的执行模型：指令前的即时求值 (Just-in-Time Evaluation)

这是理解宏系统强大能力的关键。宏的求值不是在节点开始时一次性完成的，而是与节点的指令执行紧密相连。

在一个节点内，引擎会严格按照 `run` 列表中的指令顺序执行。在**每一个**指令即将执行其 `runtime` **之前**，引擎会自动**遍历该指令的 `config`**。当它遇到一个值为 `{{...}}` 宏格式的字符串时，它会**执行一次**该宏，并用其返回结果**替换**掉原有的宏字符串。

这意味着：
1.  **所见即所得**：当您的运行时（如 `llm.default`）拿到 `prompt` 参数时，它**永远**是最终的、计算好的字符串。
2.  **节点内状态流动**：一个指令的宏，可以**立即访问**到该节点内**上一个指令**执行后产生的任何状态变化。这是实现复杂节点内逻辑链的关键。
3.  **隐式返回值**: 如果您的代码块最后一行是一个表达式（例如一个数字、一个字符串、一个函数调用），它的结果将成为这个宏的值。否则，其值为 `None`。

## 2. 入门指南 (为所有用户)

### 2.1 访问核心数据：您的世界交互窗口

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

*   **会话元信息 (`session`)**: 包含了关于整个交互会话的全局信息，例如会话开始的时间、总共执行的回合数等。
    *   **用途**: 用于记录、调试或实现与时间相关的逻辑。
    *   **示例**: `"{{ f'当前是第 {session.turn_count} 回合' }}"`

### 2.2 “开箱即用”的工具箱

我们预置了一些标准 Python 模块，您无需 `import` 即可直接使用：`random`, `math`, `datetime`, `json`, `re`。

*   掷一个20面的骰子: `"{{ random.randint(1, 20) }}"`
*   从列表中随机选一个: `"{{ random.choice(['红色', '蓝色', '绿色']) }}"`

### 2.3 实用示例

#### 示例1：动态生成 NPC 对话

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

#### 示例2：在一个节点内完成“计算伤害并更新状态”

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


## 3. 并发安全：引擎的承诺与您的责任

Hevno 引擎天生支持并行节点执行，这意味着没有依赖关系的节点会被同时运行以提升性能。为了让您在享受并行优势的同时，不必担心复杂的数据竞争问题，我们内置了强大的**宏级原子锁 (Macro-level Atomic Lock)** 机制。

### 3.1 引擎的承诺：透明的并发安全

Hevno 引擎的核心承诺是：**为所有基于 Python 基础数据类型（字典、列表、数字、字符串等）的世界状态操作，提供完全透明的、默认开启的并发安全保护。**

这意味着，当您在宏中编写以下代码时，我们保证其结果在任何并行执行下都是正确和可预测的：
*   `world.counter += 1`
*   `world.player['stats']['strength'] -= 5`
*   `world.log.append("New event")`

**工作原理：** 在执行任何一个宏脚本（即 `{{ ... }}` 中的全部内容）之前，引擎会自动获取一个全局写入锁。在宏脚本执行完毕后，锁会自动释放。这保证了**每一个宏脚本的执行都是一个不可分割的原子操作**。您无需做任何事情，即可免费获得这份安全保障。

### 3.2 问题的“完美风暴”：何时会超出引擎的保护范围？

我们的自动化保护机制是有边界的。一个操作**必定会**产生不可预测的并发问题（竞态条件），当且仅当它**同时满足以下所有条件**：

1.  **使用自定义类管理可变状态：** 您在宏中定义了 `class MyObject:` 并在其实例中直接存储可变数据（如 `self.hp = 100`），并将其存入 `world`。
2.  **使用非纯方法修改状态：** 您调用了该实例的一个方法来直接修改其内部状态（如 `my_obj.take_damage(10)`，其内部实现是 `self.hp -= 10`）。
3.  **真正的并行执行：** 您将这个修改操作放在了两个或多个**无依赖关系**的并行节点中。
4.  **操作同一数据实例：** 这些并行节点操作的是**同一个对象实例**（e.g., `world.player_character`）。

这个场景的本质是，您创建了一个引擎无法自动理解其内部工作原理的“黑盒”（您的自定义类），并要求引擎在并行环境下保证其内部操作的原子性。这是一个理论上无法被通用引擎自动解决的问题。

### 3.3 解决方案路径：从推荐模式到自定义运行时

如果您发现自己确实需要实现上述的复杂场景，我们提供了从易到难、从推荐到专业的解决方案路径：

#### **第一层（强烈推荐）：遵循“数据-逻辑分离”设计模式**

这是解决此问题的**首选方案**。它不需要您理解并发的复杂性，只需稍微调整代码组织方式：

*   **状态用字典：** `world.player = {'hp': 100}`
*   **逻辑用函数：** `def take_damage(p, amount): p['hp'] -= amount`
*   **在宏中调用：** `{{ take_damage(world.player, 10) }}`

这种模式能完美地被我们的自动化安全机制所覆盖，是 99% 的用户的最佳选择。

#### **第二层（最终选择）：编写自定义运行时（插件）**

如果您是高级开发者，并且有强烈的理由必须使用自定义类和方法来处理并发状态（例如，与外部系统集成或实现极其复杂的领域模型），那么正确的做法是**将这个责任从宏中移出，封装到一个自定义的运行时中**。

**为什么应该使用自定义运行时？**

*   **明确的控制权：** 在您自己的运行时 `execute` 方法中，您可以直接访问 `ExecutionContext` 并获取全局的 **`asyncio.Lock`**。这让您可以**精确地、手动地**控制加锁的范围，以保护您的自定义对象操作。
*   **清晰的职责划分：**
    *   **宏（Macro）** 的设计目标是**快速、便捷的逻辑编排和数据转换**，它不应该承载复杂的、需要手动管理的并发控制逻辑。
    *   **运行时（Runtime）** 的设计目标是**执行封装好的、具有明确输入和输出的、可重用的功能单元**。处理与特定自定义对象相关的、复杂的原子操作，正是运行时的用武之地。
*   **可测试与可复用：** 将复杂逻辑封装在运行时中，使得该逻辑单元可以被独立测试，并在图定义中被多次复用。


## 4. 高级指南 (为开发者)

### 4.1 宏的转义与 `system.execute`

这是宏系统最强大的功能之一，允许您创建能与 LLM 进行深度交互的代理。

**场景**: 您想让 LLM 能够通过返回特定指令来操纵世界状态。

#### **步骤 1: 发送“转义”的指令给 LLM**

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

#### **步骤 2: 执行 LLM 返回的指令**

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

### 4.2 动态定义函数与 `import`

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

### 4.3 宏与依赖推断

*   **自动推断**: 在任何指令的 `config` 中使用 `{{ nodes.some_node_id... }}` 会自动建立对 `some_node_id` 的依赖。
*   **手动声明**: （未来功能）对于无法自动推断的动态依赖（如 `nodes[world.var]`），可以使用 `depends_on: ["node_A", "node_B"]` 字段来手动声明。

---

## 5. 内部实现概要 (为引擎开发者)

1.  **节点内循环**: `ExecutionEngine._execute_node` 循环遍历节点的 `run` 指令列表。
2.  **指令前求值**: 在每次循环中，它首先调用 `evaluation.evaluate_data` 来处理当前指令的 `config`。
3.  **宏级原子性**: 在 `evaluation.evaluate_expression` 内部，执行任何宏代码之前，会先获取一个在本次图执行期间唯一的 `asyncio.Lock`。宏执行完毕后，锁被释放。这保证了对 `world` 状态的并发修改是安全的。
4.  **运行时纯粹性**: 运行时接收到的 `config` 是纯粹、已求值的 Python 对象。这极大地简化了运行时的设计和测试。
5.  **`system.execute`**：它是一个标准的运行时。其特殊之处在于，它在自己的实现内部再次调用了 `evaluation.evaluate_expression`，从而实现了可控的“二次求值”循环。
```

### main.py
```
# backend/main.py
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, BaseModel
from typing import Dict, Any, List, Optional
from uuid import UUID

# 1. 导入新的模型
from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry
from backend.runtimes.base_runtimes import InputRuntime, LLMRuntime, SetWorldVariableRuntime
from backend.runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime
from backend.core.state_models import Sandbox, SnapshotStore, StateSnapshot

class CreateSandboxRequest(BaseModel):
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None

def setup_application():
    app = FastAPI(
        title="Hevno Backend Engine",
        description="The core execution engine for Hevno project, supporting runtime-centric, sequential node execution.",
        version="0.3.2-map-runtime" # 版本号更新
    )
    
    # 基础运行时
    runtime_registry.register("system.input", InputRuntime)
    runtime_registry.register("llm.default", LLMRuntime)
    runtime_registry.register("system.set_world_var", SetWorldVariableRuntime)
    
    # 控制流运行时
    runtime_registry.register("system.execute", ExecuteRuntime)
    runtime_registry.register("system.call", CallRuntime)
    runtime_registry.register("system.map", MapRuntime)
    
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
sandbox_store: Dict[UUID, Sandbox] = {}
snapshot_store = SnapshotStore()
execution_engine = ExecutionEngine(registry=runtime_registry)

@app.post("/api/sandboxes", response_model=Sandbox)
async def create_sandbox(request: CreateSandboxRequest, name: str):
    sandbox = Sandbox(name=name)
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request.graph_collection,
        world_state=request.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    return sandbox

@app.post("/api/sandboxes/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(sandbox_id: UUID, user_input: Dict[str, Any] = Body(...)):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    latest_snapshot = sandbox.get_latest_snapshot(snapshot_store)
    if not latest_snapshot:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
    new_snapshot = await execution_engine.step(latest_snapshot, user_input)
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    return new_snapshot

@app.get("/api/sandboxes/{sandbox_id}/history", response_model=List[StateSnapshot])
async def get_sandbox_history(sandbox_id: UUID):
    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots and not sandbox_store.get(sandbox_id):
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return snapshots

@app.put("/api/sandboxes/{sandbox_id}/revert")
async def revert_sandbox_to_snapshot(sandbox_id: UUID, snapshot_id: UUID):
    sandbox = sandbox_store.get(sandbox_id)
    target_snapshot = snapshot_store.get(snapshot_id)
    if not sandbox or not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Sandbox or Snapshot not found.")
    sandbox.head_snapshot_id = snapshot_id
    sandbox_store[sandbox.id] = sandbox # 确保更新存储中的沙盒对象
    return {"message": f"Sandbox reverted to snapshot {snapshot_id}"}
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on runtime-centric architecture!"}
```

### core/registry.py
```
# backend/core/registry.py
from typing import Dict, Type
from backend.core.runtime import RuntimeInterface

class RuntimeRegistry:
    def __init__(self):
        # 只存储类，不存储实例
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        if name in self._registry:
            print(f"Warning: Overwriting runtime registration for '{name}'.")
        self._registry[name] = runtime_class
        print(f"Runtime class '{name}' registered.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime '{name}' not found.")
        
        # 总是返回一个新的实例
        return runtime_class()

# 全局单例保持不变
runtime_registry = RuntimeRegistry()
```

### core/evaluation.py
```
# backend/core/evaluation.py
import ast
import asyncio
import re
from typing import Any, Dict, List, Optional   
from functools import partial
from backend.core.utils import DotAccessibleDict
from backend.core.types import ExecutionContext # 显式导入，避免循环引用问题


# 预编译宏的正则表达式，用于快速查找
MACRO_REGEX = re.compile(r"^{{\s*(.+)\s*}}$", re.DOTALL)

# --- 预置的、开箱即用的模块 ---
# 我们在这里定义它们，以便在构建上下文时注入
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
    从 ExecutionContext 和可选的管道变量构建一个扁平的字典，用作宏的执行环境。
    """
    context = {
        **PRE_IMPORTED_MODULES,
        "world": DotAccessibleDict(exec_context.world_state),
        "nodes": DotAccessibleDict(exec_context.node_states),
        "run": DotAccessibleDict(exec_context.run_vars),
        "session": DotAccessibleDict(exec_context.session_info),
        # --- 新增：将内部变量（包括锁）传递给上下文 ---
        "__internal__": exec_context.internal_vars
    }
    if pipe_vars is not None:
        context['pipe'] = DotAccessibleDict(pipe_vars)
        
    return context

# --- 修改 evaluate_expression ---
async def evaluate_expression(code_str: str, context: Dict[str, Any]) -> Any:
    """
    安全地执行一段 Python 代码字符串并返回结果。
    在执行前获取全局写入锁，确保宏的原子性。
    """
    # 1. 从上下文中提取锁
    lock = context.get("__internal__", {}).get("global_write_lock")
    
    # 2. 解析代码 (与之前相同)
    try:
        tree = ast.parse(code_str, mode='exec')
    except SyntaxError as e:
        raise ValueError(f"Macro syntax error: {e}\nCode: {code_str}")

    result_var = "_macro_result"
    
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        assign_node = ast.Assign(
            targets=[ast.Name(id=result_var, ctx=ast.Store())],
            value=tree.body[-1].value
        )
        tree.body[-1] = ast.fix_missing_locations(assign_node)

    # 3. 准备在非阻塞执行器中运行的同步函数
    loop = asyncio.get_running_loop()
    local_scope = {}
    exec_func = partial(exec, compile(tree, filename="<macro>", mode="exec"), context, local_scope)
    
    # 4. 在执行期间持有锁
    if lock:
        async with lock:
            # 锁被持有，现在可以在另一个线程中安全地执行阻塞代码
            await loop.run_in_executor(None, exec_func)
    else:
        # 如果没有锁（例如在测试环境中），直接执行
        await loop.run_in_executor(None, exec_func)
    
    # 5. 返回结果 (与之前相同)
    return local_scope.get(result_var)


async def evaluate_data(data: Any, eval_context: Dict[str, Any]) -> Any:
    """
    递归地遍历一个数据结构 (dict, list)，查找并执行所有宏。
    这是 `_execute_node` 将调用的主入口函数。
    """
    if isinstance(data, str):
        match = MACRO_REGEX.match(data)
        if match:
            code_to_run = match.group(1)
            # 发现宏，执行它并返回结果
            return await evaluate_expression(code_to_run, eval_context)
        # 不是宏，原样返回
        return data
        
    if isinstance(data, dict):
        # 异步地处理字典中的所有值
        # 注意：我们不处理 key，只处理 value
        keys = data.keys()
        values = [evaluate_data(v, eval_context) for v in data.values()]
        evaluated_values = await asyncio.gather(*values)
        return dict(zip(keys, evaluated_values))

    if isinstance(data, list):
        # 异步地处理列表中的所有项
        items = [evaluate_data(item, eval_context) for item in data]
        return await asyncio.gather(*items)

    # 对于其他类型（数字、布尔等），原样返回
    return data
```

### core/__init__.py
```

```

### core/types.py
```
# backend/core/types.py 
from __future__ import annotations
import json 
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone

from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

class ExecutionContext(BaseModel):
    initial_snapshot: StateSnapshot
    node_states: Dict[str, Any] = Field(default_factory=dict)
    world_state: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    
    function_registry: Dict[str, Callable] = Field(default_factory=dict)
    session_info: Dict[str, Any] = Field(default_factory=lambda: {
        "start_time": datetime.now(timezone.utc),
        "conversation_turn": 0,
    })
    
    internal_vars: Dict[str, Any] = Field(default_factory=dict, repr=False)

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_snapshot(cls, snapshot: StateSnapshot, run_vars: Dict[str, Any] = None) -> 'ExecutionContext':
        return cls(
            initial_snapshot=snapshot,
            world_state=snapshot.world_state.copy(),
            run_vars=run_vars or {}
        )

    def to_next_snapshot(
        self,
        final_node_states: Dict[str, Any],
        triggering_input: Dict[str, Any]
    ) -> StateSnapshot:
        current_graphs = self.initial_snapshot.graph_collection
        if '__graph_collection__' in self.world_state:
            try:
                evolved_graph_value = self.world_state['__graph_collection__']
                if isinstance(evolved_graph_value, str):
                    evolved_graph_dict = json.loads(evolved_graph_value)
                else:
                    evolved_graph_dict = evolved_graph_value
                
                evolved_graphs = GraphCollection.model_validate(evolved_graph_dict)
                current_graphs = evolved_graphs
            except (ValidationError, json.JSONDecodeError) as e:
                print(f"Warning: Failed to parse evolved graph collection from world_state: {e}")

        return StateSnapshot(
            sandbox_id=self.initial_snapshot.sandbox_id,
            graph_collection=current_graphs,
            world_state=self.world_state,
            parent_snapshot_id=self.initial_snapshot.id,
            run_output=final_node_states,
            triggering_input=triggering_input
        )
        
ExecutionContext.model_rebuild()
```

### core/runtime.py
```
# backend/core/runtime.py 
from abc import ABC, abstractmethod
from typing import Dict, Any

class RuntimeInterface(ABC):
    """
    定义所有运行时都必须遵守的接口。
    """
    @abstractmethod
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。
        
        :param config: 经过宏求值后的、该运行时专属的配置字典。
        :param kwargs: 其他上下文信息，如 pipeline_state, context, engine。
        """
        pass
```

### core/engine.py
```
# backend/core/engine.py
import asyncio
from enum import Enum, auto
from typing import Dict, Any, Set, List, Optional
from collections import defaultdict

# 导入新的模型和依赖解析器
from backend.models import GraphCollection, GraphDefinition, GenericNode
from backend.core.dependency_parser import build_dependency_graph
from backend.core.registry import RuntimeRegistry
from backend.core.evaluation import build_evaluation_context, evaluate_data
from backend.core.types import ExecutionContext
from backend.core.runtime import RuntimeInterface # 显式导入


class NodeState(Enum):
    """定义节点在执行过程中的所有可能状态。"""
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    SKIPPED = auto()

class GraphRun:
    """管理一次图执行的状态，现在支持任意 GraphDefinition。"""
    def __init__(self, context: ExecutionContext, graph_def: GraphDefinition):
        self.context = context
        self.graph_def = graph_def
        if not self.graph_def:
            raise ValueError("GraphRun must be initialized with a valid GraphDefinition.")
        self.node_map: Dict[str, GenericNode] = {n.id: n for n in self.graph_def.nodes}
        self.node_states: Dict[str, NodeState] = {}
        # 使用新的模型结构进行依赖解析
        self.dependencies: Dict[str, Set[str]] = build_dependency_graph(
            [node.model_dump() for node in self.graph_def.nodes]
        )
        self.subscribers: Dict[str, Set[str]] = self._build_subscribers()
        self._detect_cycles()
        self._initialize_node_states()

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
        return self.dependencies[node_id]
    def get_subscribers(self, node_id: str) -> Set[str]:
        return self.subscribers[node_id]
    def get_execution_context(self) -> ExecutionContext:
        return self.context
    def get_final_node_states(self) -> Dict[str, Any]:
        return self.context.node_states


class ExecutionEngine:
    def __init__(self, registry: RuntimeRegistry, num_workers: int = 5):
        self.registry = registry
        self.num_workers = num_workers

    async def step(self, initial_snapshot, triggering_input: Dict[str, Any] = None):
        if triggering_input is None: triggering_input = {}
        context = ExecutionContext.from_snapshot(initial_snapshot, {"trigger_input": triggering_input})
        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def: raise ValueError("'main' graph not found.")
        
        final_node_states = await self._execute_graph(main_graph_def, context)

        next_snapshot = context.to_next_snapshot(final_node_states, triggering_input)
        print(f"Step complete. New snapshot {next_snapshot.id} created.")
        return next_snapshot

    async def _execute_graph(self, graph_def: GraphDefinition, context: ExecutionContext, inherited_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        run = GraphRun(context, graph_def)
        task_queue = asyncio.Queue()

        if "global_write_lock" not in context.internal_vars:
            context.internal_vars["global_write_lock"] = asyncio.Lock()
            print("Global write lock created for this step.")
        

        # --- 处理继承的输入 ---
        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                # 将占位符节点的状态设置为 SUCCEEDED 并存储其结果
                # 即使 node_id 不在 run.node_map 中，这也能正常工作
                run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, result)

        # --- 确定初始的 READY 节点 ---
        # 扫描所有 PENDING 节点，看它们的依赖是否已经满足（包括被注入的依赖）
        for node_id in run.get_nodes_in_state(NodeState.PENDING):
            dependencies = run.get_dependencies(node_id)
            if all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in dependencies):
                run.set_node_state(node_id, NodeState.READY)

        # 将所有初始状态为 READY 的节点（无论是无依赖还是依赖已满足）放入队列
        for node_id in run.get_nodes_in_state(NodeState.READY):
            await task_queue.put(node_id)
        
        if task_queue.empty() and not any(s in (NodeState.SUCCEEDED, NodeState.RUNNING) for s in run.node_states.values()):
            # 如果队列为空且图中没有任何节点运行或成功，这可能意味着图是空的或无法启动
             if not run.node_map:
                 print("Graph is empty, finishing immediately.")
             else:
                 print("Warning: No nodes could be made ready to run in the graph.")
        
        workers = [asyncio.create_task(self._worker(f"worker-{i}", run, task_queue)) for i in range(self.num_workers)]
        
        await task_queue.join()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        
        # 返回所有已定义节点的最终状态
        final_states = {nid: run.get_node_result(nid) for nid in run.node_map if run.get_node_result(nid) is not None}
        return final_states


    async def _worker(self, name: str, run: 'GraphRun', queue: asyncio.Queue):
        while True:
            try:
                node_id = await queue.get()
                print(f"[{name}] Picked up node: {node_id}")
                node = run.get_node(node_id)
                context = run.get_execution_context()
                run.set_node_state(node_id, NodeState.RUNNING)
                
                try:
                    output = await self._execute_node(node, context)
                    if isinstance(output, dict) and "error" in output:
                        print(f"[{name}] Node {node_id} FAILED (internally): {output['error']}")
                        run.set_node_result(node_id, output)
                        run.set_node_state(node_id, NodeState.FAILED)
                    else:
                        run.set_node_result(node_id, output)
                        run.set_node_state(node_id, NodeState.SUCCEEDED)
                        print(f"[{name}] Node {node_id} SUCCEEDED.")
                    self._process_subscribers(node_id, run, queue)
                except Exception as e:
                    error_message = f"Unexpected error in worker for node {node_id}: {e}"
                    print(f"[{name}] Node {node_id} FAILED (unexpectedly): {error_message}")
                    run.set_node_result(node_id, {"error": error_message})
                    run.set_node_state(node_id, NodeState.FAILED)
                    self._process_subscribers(node_id, run, queue)
                finally:
                    queue.task_done()
            except asyncio.CancelledError:
                print(f"[{name}] shutting down.")
                break
    
    def _process_subscribers(self, completed_node_id: str, run: 'GraphRun', queue: asyncio.Queue):
        completed_node_state = run.get_node_state(completed_node_id)
        for sub_id in run.get_subscribers(completed_node_id):
            if run.get_node_state(sub_id) != NodeState.PENDING: continue
            if completed_node_state == NodeState.FAILED:
                run.set_node_state(sub_id, NodeState.SKIPPED)
                run.set_node_result(sub_id, {"status": "skipped", "reason": f"Upstream failure of node {completed_node_id}."})
                self._process_subscribers(sub_id, run, queue)
                continue
            is_ready = all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in run.get_dependencies(sub_id))
            if is_ready:
                run.set_node_state(sub_id, NodeState.READY)
                queue.put_nowait(sub_id)

    # --- THE CORE REFACTORED METHOD ---
    async def _execute_node(self, node: GenericNode, context: ExecutionContext) -> Dict[str, Any]:
        """
        按顺序执行节点内的运行时指令，在每一步之前进行宏求值。
        """
        node_id = node.id
        print(f"Executing node: {node_id}")

        # pipeline_state 在指令间传递和累积
        pipeline_state: Dict[str, Any] = {}

        if not node.run:
            print(f"Node {node_id} has no run instructions, finishing.")
            return {}

        for i, instruction in enumerate(node.run):
            runtime_name = instruction.runtime
            print(f"  - Step {i+1}/{len(node.run)}: Running runtime '{runtime_name}'")
            
            try:
                # 1. 对当前指令的 config 进行宏求值
                eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
                processed_config = await evaluate_data(instruction.config, eval_context)

                # 2. 获取运行时实例
                runtime: RuntimeInterface = self.registry.get_runtime(runtime_name)
                
                # 3. 执行运行时
                output = await runtime.execute(
                    config=processed_config,
                    pipeline_state=pipeline_state,
                    context=context,
                    node=node,
                    engine=self
                )
                
                if not isinstance(output, dict):
                    error_message = f"Runtime '{runtime_name}' did not return a dictionary. Got: {type(output).__name__}"
                    print(f"  - Error in pipeline: {error_message}")
                    return {"error": error_message, "failed_step": i, "runtime": runtime_name}

                # 4. 更新管道状态，为下一个指令做准备
                pipeline_state.update(output)

            except Exception as e:
                import traceback
                traceback.print_exc()
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {e}"
                print(f"  - Error in pipeline: {error_message}")
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}

        print(f"Node {node_id} pipeline finished successfully.")
        return pipeline_state
```

### core/utils.py
```
# backend/core/utils.py

from typing import Any, Dict, List

class DotAccessibleDict:
    """
    一个【递归】代理类，它包装一个字典，并允许通过点符号进行属性访问。
    所有读取和写入操作都会直接作用于原始的底层字典。
    当访问一个值为字典的属性时，它会自动将该字典也包装成 DotAccessibleDict。
    """
    def __init__(self, data: Dict[str, Any]):
        object.__setattr__(self, "_data", data)

    @classmethod
    def _wrap(cls, value: Any) -> Any:
        """递归包装值。如果值是字典，包装它；如果是列表，递归包装其内容。"""
        if isinstance(value, dict):
            # 如果是字典，返回一个新的代理实例
            return cls(value)
        if isinstance(value, list):
            # 如果是列表，递归处理列表中的每一项
            return [cls._wrap(item) for item in value]
        # 其他类型原样返回
        return value

    def __getattr__(self, name: str) -> Any:
        """当访问 obj.key 时调用。"""
        try:
            # 获取原始值
            value = self._data[name]
            # 在返回值之前，递归地包装它！
            return self._wrap(value)
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        """当执行 obj.key = value 时调用。"""
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
```

### core/state_models.py
```
# backend/core/state_models.py

from __future__ import annotations
from uuid import uuid4, UUID
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

# 导入这个文件所依赖的最基础模型
from backend.models import GraphCollection

# --- 所有相关的模型都住在这里 ---

class StateSnapshot(BaseModel):
    """
    一个不可变的快照，代表 Sandbox 在某个时间点的完整状态。
    """
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
    """
    一个交互式模拟环境的容器。
    它管理着一系列的状态快照。
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    head_snapshot_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_latest_snapshot(self, store: SnapshotStore) -> Optional[StateSnapshot]:
        # 现在 SnapshotStore 和 StateSnapshot 都在同一个作用域，类型提示完美工作
        if self.head_snapshot_id:
            return store.get(self.head_snapshot_id)
        return None

class SnapshotStore:
    """一个简单的内存快照存储。"""
    def __init__(self):
        self._store: Dict[UUID, StateSnapshot] = {}

    def save(self, snapshot: StateSnapshot):
        if snapshot.id in self._store:
            raise ValueError(f"Snapshot with id {snapshot.id} already exists.")
        self._store[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> Optional[StateSnapshot]:
        return self._store.get(snapshot_id)

    def find_by_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        return [s for s in self._store.values() if s.sandbox_id == sandbox_id]

    def clear(self):
        self._store = {}

# --- 在文件末尾重建所有模型 ---
# 这确保了 Pydantic 能够正确处理所有内部引用和向前引用
StateSnapshot.model_rebuild()
Sandbox.model_rebuild()
```

### core/dependency_parser.py
```
# backend/core/dependency_parser.py 
import re
from typing import Set, Dict, Any, List

# 正则表达式，用于匹配 {{...}} 宏内部的 `nodes.node_id` 模式
NODE_DEP_REGEX = re.compile(r'nodes\.([a-zA-Z0-9_]+)')

def extract_dependencies_from_string(s: str) -> Set[str]:
    """从单个字符串中提取所有节点依赖。"""
    if not isinstance(s, str):
        return set()
    # 仅在检测到宏标记时才进行解析，以提高效率并避免误报
    if '{{' in s and '}}' in s and 'nodes.' in s:
        return set(NODE_DEP_REGEX.findall(s))
    return set()

def extract_dependencies_from_value(value: Any) -> Set[str]:
    """递归地从任何值（字符串、列表、字典）中提取依赖。"""
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

def build_dependency_graph(nodes: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    根据节点列表自动构建依赖图。
    会合并从宏中自动推断的依赖和从 `depends_on` 字段中明确声明的依赖。
    """
    dependency_map: Dict[str, Set[str]] = {}

    for node in nodes:
        node_id = node['id']
        
        # 1. 从宏中自动推断依赖 
        auto_inferred_deps = set()
        for instruction in node.get('run', []):
            instruction_config = instruction.get('config', {})
            dependencies = extract_dependencies_from_value(instruction_config)
            auto_inferred_deps.update(dependencies)
        
        # 2. 从 `depends_on` 字段中获取明确的依赖 
        explicit_deps = set(node.get('depends_on') or [])

        # 3. 合并两种依赖
        all_dependencies = auto_inferred_deps.union(explicit_deps)
        
        # 4. 不再过滤掉不存在的节点ID。这对于支持子图的输入占位符至关重要。
        dependency_map[node_id] = all_dependencies
    
    return dependency_map
```

### runtimes/__init__.py
```

```

### runtimes/base_runtimes.py
```
# backend/runtimes/base_runtimes.py
import asyncio 
from backend.core.runtime import RuntimeInterface
from backend.core.types import ExecutionContext
from typing import Dict, Any

class InputRuntime(RuntimeInterface):
    """从 config 中获取 'value'。"""
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value", "")}

class LLMRuntime(RuntimeInterface):
    """从自己的 config 中获取已经渲染好的 prompt。"""
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        rendered_prompt = config.get("prompt")

        # 也可以从管道状态中获取输入，以实现链式调用
        if not rendered_prompt:
            pipeline_state = kwargs.get("pipeline_state", {})
            rendered_prompt = pipeline_state.get("output", "")
        
        if not rendered_prompt:
            raise ValueError("LLMRuntime requires a 'prompt' in its config or an 'output' from the previous step.")

        # 模拟 LLM API 调用延迟
        await asyncio.sleep(0.1)
        
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        return {"llm_output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}

class SetWorldVariableRuntime(RuntimeInterface):
    """从 config 中获取变量名和值，并设置一个持久化的世界变量。"""
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        context: ExecutionContext = kwargs.get("context")
        variable_name = config.get("variable_name")
        value_to_set = config.get("value")

        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name' in its config.")
        
        # 修改的是可变的 ExecutionContext.world_state
        context.world_state[variable_name] = value_to_set
        
        # 这个运行时通常没有自己的输出，只是产生副作用
        return {}
```

### runtimes/control_runtimes.py
```
# backend/runtimes/control_runtimes.py
import asyncio
from typing import Dict, Any, List

from backend.core.runtime import RuntimeInterface
# 导入所有需要的核心组件
from backend.core.evaluation import evaluate_data, evaluate_expression, build_evaluation_context
from backend.core.types import ExecutionContext
from backend.core.engine import ExecutionEngine
from backend.core.utils import DotAccessibleDict


class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        context: ExecutionContext = kwargs.get("context")
        code_to_execute = config.get("code")

        if not isinstance(code_to_execute, str):
            # 如果不是字符串（例如，宏求值后变成了数字或对象），直接返回
            return {"output": code_to_execute}

        # 构建当前的执行上下文
        eval_context = build_evaluation_context(context)
        # 进行二次求值
        result = await evaluate_expression(code_to_execute, eval_context)
        return {"output": result}


class CallRuntime(RuntimeInterface):
    """
    执行一个子图。这是代码复用和逻辑分层的基础。
    """
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        engine: ExecutionEngine = kwargs.get("engine")
        context: ExecutionContext = kwargs.get("context")
        
        if not engine or not context:
            raise ValueError("CallRuntime requires 'engine' and 'context' in kwargs.")
            
        graph_name = config.get("graph")
        if not graph_name:
            raise ValueError("system.call requires a 'graph' name in its config.")
            
        # `using` 字典的值在此刻已经被宏系统求值完毕
        using_inputs = config.get("using", {})
        
        # 1. 找到子图的定义
        graph_collection = context.initial_snapshot.graph_collection.root
        subgraph_def = graph_collection.get(graph_name)
        if not subgraph_def:
            raise ValueError(f"Subgraph '{graph_name}' not found in graph collection.")

        # 2. 准备要注入的 "inherited_inputs"
        # 我们将 `using` 字典转换为标准的节点输出格式
        # e.g., 'character_input' becomes a node with result {'output': ...}
        inherited_inputs = {
            placeholder_name: {"output": value}
            for placeholder_name, value in using_inputs.items()
        }

        # 3. 递归调用执行引擎来运行子图
        print(f"  -> Calling subgraph '{graph_name}' with inputs: {list(inherited_inputs.keys())}")
        subgraph_results = await engine._execute_graph(
            graph_def=subgraph_def,
            context=context, # 传递当前的执行上下文（特别是 world_state）
            inherited_inputs=inherited_inputs
        )
        print(f"  <- Subgraph '{graph_name}' finished.")

        # 4. 将子图的完整结果作为此运行时的输出
        return {"output": subgraph_results}


# --- 新增的 MapRuntime ---
class MapRuntime(RuntimeInterface):
    """
    实现并行迭代 (Fan-out / Scatter-Gather)。
    将一个子图并发地应用到输入列表的每个元素上。
    """
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        # --- 1. 准备阶段 (Preparation) ---
        engine: ExecutionEngine = kwargs.get("engine")
        context: ExecutionContext = kwargs.get("context")
        
        if not engine or not context:
            raise ValueError("MapRuntime requires 'engine' and 'context' in kwargs.")

        list_to_iterate = config.get("list")
        graph_name = config.get("graph")
        using_template = config.get("using", {})
        collect_expression_template = config.get("collect")

        if not isinstance(list_to_iterate, list):
            raise TypeError(f"system.map 'list' field must be a list, but got {type(list_to_iterate).__name__}")
        if not graph_name:
            raise ValueError("system.map requires a 'graph' name in its config.")

        graph_collection = context.initial_snapshot.graph_collection.root
        subgraph_def = graph_collection.get(graph_name)
        if not subgraph_def:
            raise ValueError(f"Subgraph '{graph_name}' for system.map not found in graph collection.")

        # --- 2. 分发/任务创建阶段 (Scatter / Task Creation) ---
        tasks = []
        base_eval_context = build_evaluation_context(context)

        for index, item in enumerate(list_to_iterate):
            # a. 创建包含 `source` 对象的临时上下文，用于求值 `using`
            using_eval_context = {
                **base_eval_context,
                "source": DotAccessibleDict({"item": item, "index": index})
            }
            
            # b. 求值 `using` 字典
            evaluated_using = await evaluate_data(using_template, using_eval_context)
            inherited_inputs = {
                placeholder: {"output": value}
                for placeholder, value in evaluated_using.items()
            }
            
            # c. 创建部分克隆的、隔离的执行上下文
            # 关键：共享 world_state 和 internal_vars (含锁)，但 node_states 是独立的
            iteration_context = ExecutionContext(
                initial_snapshot=context.initial_snapshot,
                world_state=context.world_state,
                internal_vars=context.internal_vars,
                session_info=context.session_info,
            )

            # d. 创建子图执行任务
            task = asyncio.create_task(
                engine._execute_graph(
                    graph_def=subgraph_def,
                    context=iteration_context,
                    inherited_inputs=inherited_inputs
                )
            )
            tasks.append(task)
        
        print(f"  -> Mapping '{graph_name}' across {len(tasks)} items.")

        # --- 3. 执行与等待阶段 (Execution & Wait) ---
        subgraph_results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        print(f"  <- All {len(tasks)} mapped executions finished.")
        
        # --- 4. 聚合阶段 (Gather) ---
        if collect_expression_template:
            # 如果提供了 `collect`，则对每个结果进行二次求值
            collected_outputs = []
            for result in subgraph_results:
                # 为 `collect` 表达式创建局部求值上下文
                # 关键: `nodes` 指向当前子图的结果
                collect_eval_context = build_evaluation_context(context)
                collect_eval_context["nodes"] = DotAccessibleDict(result)
                
                # 求值 collect 表达式
                collected_value = await evaluate_data(collect_expression_template, collect_eval_context)
                collected_outputs.append(collected_value)
            
            return {"output": collected_outputs}
        else:
            # 默认行为：返回每个子图的完整结果列表
            return {"output": subgraph_results}
```
