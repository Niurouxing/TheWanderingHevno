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



---

# Hevno Codex 系统：动态的、可组合的知识引擎

欢迎来到 Hevno 的核心知识管理与文本生成系统——`Codex` 系统。它旨在将传统 LLM 应用中繁琐、静态的 Prompt 工程，转变为一种动态、可组合、且与世界状态深度融合的声明式流程。

**我们的愿景：** 不再手写拼接巨大的 Prompt 字符串，而是像拼装乐高一样，从名为“法典 (Codex)”的知识库中，通过一个名为“唤典 (`system.invoke`)”的强大指令，智能地、动态地构建出所需的一切文本。

---

## 1. 核心概念详解

`Codex` 系统由两大核心部分组成，完美体现了 Hevno“数据与行为分离”的设计哲学：

1.  **知识法典 (The Codex)**: 这是**数据**。它是一个纯粹的 JSON/字典结构，存放在持久化的世界状态 `world.codices` 中。它定义了“有什么”可用的知识，是 `StateSnapshot` 的一部分，因此可以被追踪、回滚，甚至被游戏逻辑动态地修改。
2.  **唤典运行时 (`system.invoke`)**: 这是**行为**。它是一个无状态的运行时，是一个纯粹的状态转换函数。它的工作是接收当前的 `ExecutionContext`（包含 `world`），执行一次短暂的、可预测的计算（即“唤典”过程），然后输出最终组合好的文本。

### 1.1 知识法典 (Codex) 的结构

一个法典集合存放在 `world.codices` 中，它是一个字典，其 `key` 为法典的名称，`value` 为法典对象的定义。

**示例 `world.codices` 结构:**
```json
{
  "world_state": {
    "codices": {
      "persona_rules": { /* ... 法典A ... */ },
      "world_lore": {
        "description": "包含动态的世界背景知识。",
        "config": {
          "recursion_depth": 3
        },
        "entries": [
          {
            "id": "lore_magic_concept",
            "content": "{{ f'魔法是这个世界的核心力量，它源自于 {world.magic_source}。' }}",
            "is_enabled": "{{ world.magic_is_unlocked }}",
            "trigger_mode": "on_keyword",
            "keywords": ["魔法", "法术"],
            "priority": 10
          },
          {
            "id": "lore_king_status",
            "content": "{{ f'国王目前正在 {nodes.spy_report.output.king_location}。' }}",
            "trigger_mode": "always_on",
            "priority": "{{ 100 if world.is_urgent_news else 20 }}"
          }
        ]
      }
    },
    "magic_is_unlocked": true,
    "is_urgent_news": false,
    "magic_source": "上古龙脉"
  }
}
```

#### **法典条目 (Entry) 的关键属性:**

每个 `entries` 列表中的对象都遵循以下结构：

-   `id` (str, 必须): 条目在其法典内的唯一标识符。
-   `content` (str, 必须): **[宏]** 核心内容。这是一个宏字符串，将在**第二阶段（渲染阶段）**被求值。它可以访问完整的上下文，包括 `world`, `run`, `nodes`, `pipe` 以及一个特殊的 `trigger` 对象。
-   `is_enabled` (bool | str, 可选, 默认 `true`): **[宏]** 一个布尔值或返回布尔值的宏。在**第一阶段（选择阶段）**求值，用于动态决定此条目是否参与本次处理。
-   `trigger_mode` (str, 可选, 默认 `"always_on"`): 触发模式。
    -   `"always_on"`: 只要条目 `is_enabled`，总是被激活。
    -   `"on_keyword"`: 只有当其 `keywords` 中的至少一个词出现在触发源文本中时才被激活。
-   `keywords` (List[str] | str, 可选, 默认 `[]`): **[宏]** 一个字符串列表或返回列表的宏。用于 `"on_keyword"` 模式。
-   `priority` (int | str, 可选, 默认 `0`): **[宏]** 一个整数或返回整数的宏。在**第一阶段（选择阶段）**求值。用于在全局的“待渲染池”中排序所有被激活的条目，**数值越大越优先**。

#### **新增的 `trigger` 上下文**
在条目的 `content` 宏中，可以访问一个特殊的 `trigger` 对象，它包含了触发此条目的相关信息：
-   `trigger.source_text` (str): 触发此条目的完整源文本。
-   `trigger.matched_keywords` (List[str]): 一个列表，包含此条目的哪些 `keywords` 在源文本中被匹配到。

### 1.2 `system.invoke` 运行时

这是将 `Codex` 数据变为鲜活文本的核心指令。它能从多个法典中，根据不同触发源，智能地融合信息。

**图中的使用示例:**
```json
{
  "id": "build_llm_context",
  "run": [{
    "runtime": "system.invoke",
    "config": {
      "from": [
        { "codex": "persona_rules" },
        {
          "codex": "world_lore",
          "source": "{{ '\\n'.join(h.content for h in world.history[-3:]) }}"
        }
      ],
      "recursion_enabled": true,
      "debug": true 
    }
  }]
}
```

#### **`invoke` 配置的关键属性:**

-   `from` (List[dict], 必须): 一个列表，定义了所有要咨询的数据源。列表中的每个对象包含：
    -   `codex` (str, 必须): 要咨询的法典名称（必须与 `world.codices` 中的键匹配）。
    -   `source` (str, 可选): **[宏]** 一个宏字符串，其求值结果将作为此法典的“触发源文本”。如果省略，则此法典只会激活其 `always_on` 条目。
-   `recursion_enabled` (bool, 可选, 默认 `false`): 是否允许在所有激活的条目间进行跨法典的递归触发。详见下文。
-   `debug` (bool, 可选, 默认 `false`): 是否开启调试模式。开启后，输出将变为一个包含 `final_text` 和详细 `trace` 信息的结构化对象，而非单个字符串。
    -   **`trace` 对象示例**:
        ```json
        {
          "final_text": "...",
          "trace": {
            "initial_activation": [
              { "id": "lore_king_status", "priority": 100, "reason": "always_on", "matched_keywords": [] }
            ],
            "recursive_activations": [
              { "id": "lore_magic_concept", "priority": 10, "reason": "recursive_keyword_match", "triggered_by": "some_other_entry" }
            ],
            "evaluation_log": [
              {"id": "lore_king_status", "status": "rendered"},
              {"id": "lore_magic_concept", "status": "rendered"}
            ],
            "rejected_entries": [
              { "id": "secret_entry", "reason": "is_enabled macro returned false" }
            ]
          }
        }
        ```

---

## 2. 执行模型：两阶段求值与递归

`system.invoke` 的核心是其内部的“两阶段求值”机制和强大的递归循环，这保证了宏在正确的时间被求值，并能访问到正确的上下文。

### 2.1 阶段一：选择与过滤 (Structural Evaluation)

此阶段的目标是确定**哪些条目被激活**以及它们的**最终顺序**。

1.  **上下文**: 只能访问 `world` 和 `run`。**注意：此时无法访问 `nodes` 上下文。**
2.  **流程**:
    -   `invoke` 遍历 `config.from` 中的每个数据源，并求值其 `source` 宏得到触发文本。
    -   接着，`invoke` 深入每个法典的每个条目，**只求值其结构性宏**：`is_enabled`, `keywords`, `priority`。
    -   `content` 宏在此阶段**保持原样**，不被触碰。
    -   根据求值后的结构属性和触发文本，筛选出所有被激活的条目，放入一个全局的“待渲染池 (Rendering Pool)”。

*此阶段结束后，我们得到了一个包含所有待处理条目（及其最终优先级）的列表，但它们的内容仍然是宏模板。*

### 2.2 阶段二：渲染与注入 (Content Evaluation)

此阶段的目标是将选中的条目的内容渲染成最终文本。

1.  **上下文**: 可以访问**全部**上下文，包括 `world`, `run`, `nodes`, `pipe` 和新增的 `trigger`。
2.  **流程**:
    -   对“待渲染池”中的所有条目，根据它们在阶段一计算出的 `priority` 进行一次**全局降序排序**。
    -   **（递归触发）** 如果 `recursion_enabled: true`，则启动一个动态循环（详见下一节）。
    -   按最终顺序遍历池中的每一个条目，**此刻才开始求值它们的 `content` 宏**。
    -   将所有渲染好的文本片段用 `\n\n` 拼接起来，形成最终输出。

### 2.3 递归执行流程 (`recursion_enabled: true`)

当递归开启时，渲染过程不再是一次性的遍历，而是一个动态的循环，直到没有更多条目可渲染或达到 `recursion_depth` 限制：

1.  **初始填充**: 系统首先执行**阶段一**，从所有 `source` 文本中激活初始的一批条目，将它们放入“待渲染池”。

2.  **启动循环**:
    a. **排序**: 对当前“待渲染池”中的所有条目，按 `priority` 进行降序排序。
    b. **提取**: 从池中取出并移除**优先级最高**的条目。
    c. **渲染**: 执行**阶段二**，渲染该条目的 `content` 宏，得到一段新的文本。这段文本被追加到最终结果中。
    d. **再触发**: 将刚刚渲染出的新文本，作为**新的触发源**，去扫描**所有法典中所有尚未被渲染的条目**。
    e. **再填充**: 如果有新的条目在此次扫描中被激活（满足 `is_enabled` 和 `on_keyword` 条件），则计算它们的 `priority` 并将它们加入“待渲染池”。
    f. **重复**: 只要“待渲染池”不为空，就跳回步骤 **a**，重新排序并继续处理。

这个过程确保了渲染的顺序是动态响应的。一个条目被渲染后，其内容可能会激活一个更高优先级的条目，而这个条目会在下一次循环中被优先处理。

---

## 3. 最佳实践与示例

### 3.1 关键：处理隐式依赖

Hevno 引擎的依赖推断是**静态的**。它在图执行开始前扫描图定义，当 `{{ nodes.A.output }}` 出现在`config`中时，会自动建立依赖。

**Codex 的内容存在于 `world` 状态中，是动态的。** 引擎的静态分析器无法预知 `world.codices` 内部的宏是否会引用 `nodes`。因此，`Codex` 内部对 `nodes` 的引用属于**隐式依赖**。

> **规则：如果你的 `invoke` 节点所调用的 Codex 条目的 `content` 宏中引用了 `nodes.some_node.output`，你必须在 `invoke` 节点上使用 `depends_on: ["some_node"]` 来明确声明这一依赖关系。**

**正确示例：**
```json
// world.codices
{
  "npc_dialogue": {
    "entries": [{
      "id": "report_summary",
      "content": "{{ f'根据密探 {nodes.spy_identity.output} 的报告，我们得知：{nodes.spy_report.output}' }}"
    }]
  }
}
```
```json
// 图定义 (graph "nodes" list)
[
  { "id": "spy_identity", "run": [/* ... */] },
  { "id": "spy_report", "run": [/* ... */] },
  {
    "id": "generate_npc_dialogue",
    // 关键：由于 codex 内容引用了 nodes，我们必须在这里明确声明依赖关系。
    "depends_on": ["spy_identity", "spy_report"],
    "run": [{
      "runtime": "system.invoke",
      "config": {
        "from": [{ "codex": "npc_dialogue" }]
      }
    }]
  }
]
```

### 3.2 示例：构建复杂的 LLM Prompt

`Codex` 系统最强大的用途之一是动态构建提示。

**场景**：我们想让一个 AI 角色扮演，它需要一个固定的“人格”部分，和一个根据用户输入动态变化的“知识”部分。

**`world.codices` 定义:**
```json
{
  "persona": {
    "entries": [
      { "id": "role", "content": "你是一个中世纪的、脾气暴躁的矮人铁匠。", "priority": 100 },
      { "id": "rules", "content": "你的回答必须简短且粗鲁。", "priority": 90 }
    ]
  },
  "knowledge": {
    "entries": [
      {
        "id": "sword_info", "trigger_mode": "on_keyword", "keywords": ["剑", "武器"],
        "content": "关于剑？我只打最好的大马士革钢。价格不菲。"
      },
      {
        "id": "armor_info", "trigger_mode": "on_keyword", "keywords": ["盔甲", "护甲"],
        "content": "盔甲得量身定做。别拿那些现成的垃圾跟我比。"
      }
    ]
  }
}
```

**图定义:**
```json
[
  {
    "id": "build_prompt",
    "run": [{
      "runtime": "system.invoke",
      "config": {
        "from": [
          { "codex": "persona" }, // 总是激活，提供基础人设
          { "codex": "knowledge", "source": "{{ run.trigger_input.user_message }}" } // 根据用户输入触发
        ]
      }
    }]
  },
  {
    "id": "call_llm",
    "run": [{
      "runtime": "llm.default",
      "config": {
        // 将 invoke 的结果作为 prompt，并附加上下文
        "prompt": "{{ f'{nodes.build_prompt.output}\\n\\nHuman: {run.trigger_input.user_message}\\nDwarf:' }}"
      }
    }]
  }
]
```
当用户输入 `"我想买一把剑"` 时，`system.invoke` 会智能地组合出：
```
你是一个中世纪的、脾气暴躁的矮人铁匠。

你的回答必须简短且粗鲁。

关于剑？我只打最好的大马士革钢。价格不菲。
```
这个组合后的文本再被传递给 `llm.default`，从而实现动态、精准的上下文注入。
```

### main.py
```
# backend/main.py
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Body, Depends, Request # <--- 1. 导入 Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.state_models import Sandbox, SnapshotStore, StateSnapshot
from backend.core.loader import load_modules
from backend.core.registry import runtime_registry
from backend.core.services import service_registry
from backend.llm.manager import KeyPoolManager, CredentialManager
from backend.llm.registry import provider_registry
from backend.core.reporting import auditor_registry, Auditor
from backend.runtimes.reporters import RuntimeReporter
from backend.llm.reporters import LLMProviderReporter
from backend.api.reporters import SandboxStatsReporter

PLUGGABLE_MODULES = [
    "backend.runtimes",
    "backend.llm.providers",
    "backend.services"
]

class CreateSandboxRequest(BaseModel):
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None

def create_app() -> FastAPI:
    return FastAPI(
        title="Hevno Backend Engine",
        description="A dynamically loaded, modular execution engine for Hevno.",
        version="0.5.0-di-refactor"
    )

def configure_app(app: FastAPI):
    # --- 1. 初始化核心状态存储 ---
    app.state.sandbox_store = {}
    app.state.snapshot_store = SnapshotStore()
    
    # --- 2. 审阅官系统初始化 ---
    print("--- Configuring Auditor System ---")
    
    # 实例化所有 Reporter
    runtime_reporter = RuntimeReporter()
    llm_reporter = LLMProviderReporter()
    # <--- 2. 修正 Reporter 初始化: 只实例化一次，并使用 app.state ---
    sandbox_stats_reporter = SandboxStatsReporter(
        app.state.sandbox_store, 
        app.state.snapshot_store
    )

    # 向注册表注册
    auditor_registry.register(runtime_reporter)
    auditor_registry.register(llm_reporter)
    auditor_registry.register(sandbox_stats_reporter)

    # 创建 Auditor 服务并存入 app.state
    app.state.auditor = Auditor(auditor_registry)
    print("--- Auditor System Configured ---")

    # --- 3. 应用配置与服务加载 ---
    print("--- Configuring FastAPI Application ---")
    
    load_modules(PLUGGABLE_MODULES)

    is_debug_mode = os.getenv("HEVNO_LLM_DEBUG_MODE", "false").lower() == "true"
    
    provider_registry.instantiate_all()
    cred_manager = CredentialManager()
    key_manager = KeyPoolManager(credential_manager=cred_manager)
    
    for name, info in provider_registry.get_all_provider_info().items():
        key_manager.register_provider(name, info.key_env_var)

    if is_debug_mode:
        MockLLMServiceClass = service_registry.get_class("mock_llm")
        if not MockLLMServiceClass: raise RuntimeError("MockLLMService not registered!")
        llm_service_instance = MockLLMServiceClass()
    else:
        LLMServiceClass = service_registry.get_class("llm")
        if not LLMServiceClass: raise RuntimeError("LLMService not registered!")
        llm_service_instance = LLMServiceClass(
            key_manager=key_manager,
            provider_registry=provider_registry,
            max_retries=3
        )

    services = {"llm": llm_service_instance}

    app.state.engine = ExecutionEngine(
        registry=runtime_registry,
        services=services
    )

    origins = ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("--- FastAPI Application Configured ---")

app = create_app()

# --- 依赖注入函数 ---
def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    return request.app.state.sandbox_store

def get_snapshot_store(request: Request) -> SnapshotStore:
    return request.app.state.snapshot_store

def get_engine(request: Request) -> ExecutionEngine:
    return request.app.state.engine

# --- API 端点 (全部使用依赖注入) ---

@app.post("/api/sandboxes", response_model=Sandbox)
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    name: str,
    sandbox_store: Dict = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store)
):
    sandbox = Sandbox(name=name)
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request_body.graph_collection,
        world_state=request_body.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    return sandbox

@app.get("/api/system/report", tags=["System"])
async def get_system_report(request: Request):
    auditor: Auditor = request.app.state.auditor
    return await auditor.generate_full_report()

@app.post("/api/sandboxes/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: Dict = Depends(get_sandbox_store), # <--- 3. 注入依赖
    snapshot_store: SnapshotStore = Depends(get_snapshot_store), # <--- 3. 注入依赖
    engine: ExecutionEngine = Depends(get_engine) # <--- 3. 注入依赖
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    latest_snapshot = sandbox.get_latest_snapshot(snapshot_store)
    if not latest_snapshot:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
    
    new_snapshot = await engine.step(latest_snapshot, user_input)
    
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    return new_snapshot

@app.get("/api/sandboxes/{sandbox_id}/history", response_model=List[StateSnapshot])
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: Dict = Depends(get_sandbox_store), # <--- 3. 注入依赖
    snapshot_store: SnapshotStore = Depends(get_snapshot_store) # <--- 3. 注入依赖
):
    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots and not sandbox_store.get(sandbox_id):
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return snapshots

@app.put("/api/sandboxes/{sandbox_id}/revert")
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID,
    sandbox_store: Dict = Depends(get_sandbox_store), # <--- 3. 注入依赖
    snapshot_store: SnapshotStore = Depends(get_snapshot_store) # <--- 3. 注入依赖
):
    sandbox = sandbox_store.get(sandbox_id)
    target_snapshot = snapshot_store.get(snapshot_id)
    if not sandbox or not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Sandbox or Snapshot not found.")
    
    sandbox.head_snapshot_id = snapshot_id
    # 注意: 对字典的修改是原地生效的，但如果 sandbox_store 是其他类型的对象，
    # 重新赋值（sandbox_store[sandbox.id] = sandbox）会更安全。
    return {"message": f"Sandbox reverted to snapshot {snapshot_id}"}
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on runtime-centric architecture!"}

if __name__ == "__main__":
    import uvicorn
    configure_app(app)
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### llm/service.py
```
# backend/llm/service.py
from __future__ import annotations
import asyncio
from typing import Dict, Optional, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.llm.manager import KeyPoolManager, KeyInfo
from backend.llm.models import (
    LLMResponse,
    LLMError,
    LLMErrorType,
    LLMResponseStatus,
    LLMRequestFailedError,
)
from backend.llm.registry import provider_registry
from backend.core.services import service_registry, ServiceInterface


@service_registry.register("llm")
class LLMService(ServiceInterface):
    """
    LLM Gateway 的核心服务，负责协调所有组件并执行请求。
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

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
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

        def log_before_sleep(retry_state):
            pass
        
        retry_decorator = retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(Exception),
            reraise=True,
            before_sleep=log_before_sleep
        )

        try:
            wrapped_attempt = retry_decorator(self._attempt_request)
            return await wrapped_attempt(provider_name, actual_model_name, prompt, **kwargs)
        
        except LLMRequestFailedError as e:
            final_message = (
                f"LLM request for model '{model_name}' failed after {self.max_retries} attempt(s)."
            )
            raise LLMRequestFailedError(
                final_message,
                last_error=self.last_known_error 
            ) from e
        
        except Exception as e:
            raise

    async def _attempt_request(
        self,
        provider_name: str,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise LLMRequestFailedError(f"Provider '{provider_name}' not found.")

        try:
            async with self.key_manager.acquire_key(provider_name) as key_info:
                try:
                    response = await provider.generate(
                        prompt=prompt, model_name=model_name, api_key=key_info.key_string, **kwargs
                    )
                    if response.status in [LLMResponseStatus.SUCCESS, LLMResponseStatus.FILTERED]:
                        return response
                    raise LLMRequestFailedError("Provider returned an error response.", last_error=response.error_details)
                
                except Exception as e:
                    llm_error = provider.translate_error(e)
                    self.last_known_error = llm_error
                    await self._handle_error(provider_name, key_info, llm_error)
                    error_message = f"Request attempt failed: {llm_error.message}"
                    raise LLMRequestFailedError(error_message, last_error=llm_error) from e
        
        except (RuntimeError, ValueError) as e:
            raise LLMRequestFailedError(str(e))

    async def _handle_error(self, provider_name: str, key_info: KeyInfo, error: LLMError):
        if error.error_type == LLMErrorType.AUTHENTICATION_ERROR:
            await self.key_manager.mark_as_banned(provider_name, key_info.key_string)
        elif error.error_type == LLMErrorType.RATE_LIMIT_ERROR:
            self.key_manager.mark_as_rate_limited(
                provider_name, key_info.key_string, error.retry_after_seconds or 60
            )

    def _parse_model_name(self, model_name: str) -> (str, str):
        parts = model_name.split('/', 1)
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"Invalid model name format: '{model_name}'. Expected 'provider/model_id'.")
        return parts[0], parts[1]
    
    def _create_failure_response(self, model_name: str, error: LLMError) -> LLMResponse:
        return LLMResponse(status=LLMResponseStatus.ERROR, model_name=model_name, error_details=error)

@service_registry.register("mock_llm")
class MockLLMService(ServiceInterface):
    """
    一个 LLMService 的模拟实现，用于调试。
    它不进行任何网络调用，而是立即返回一个可预测的假响应。
    """
    def __init__(self, *args, **kwargs):
        print("--- Hevno LLM Gateway is running in MOCK/DEBUG mode. No real API calls will be made. ---")

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        # 模拟一个非常短暂的延迟
        await asyncio.sleep(0.05)
        
        mock_content = f"[MOCK RESPONSE for {model_name}] - Prompt received: '{prompt[:50]}...'"
        
        return LLMResponse(
            status=LLMResponseStatus.SUCCESS,
            content=mock_content,
            model_name=model_name,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 15, "total_tokens": len(prompt.split()) + 15}
        )


```

### llm/models.py
```
# backend/llm/models.py

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

### llm/registry.py
```
# backend/llm/registry.py

from typing import Dict, Type, Optional, Callable
from pydantic import BaseModel
from backend.llm.providers.base import LLMProvider


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
        """
        装饰器，用于注册 LLM Provider 类及其关联的环境变量。
        """
        def decorator(provider_class: Type[LLMProvider]) -> Type[LLMProvider]:
            if name in self._provider_info:
                print(f"Warning: Overwriting LLM provider registration for '{name}'.")
            self._provider_info[name] = ProviderInfo(provider_class=provider_class, key_env_var=key_env_var)
            print(f"LLM Provider '{name}' registered via decorator (keys from '{key_env_var}').")
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

### llm/__init__.py
```

```

### llm/reporters.py
```
# backend/llm/reporters.py
from typing import Any, Dict
from backend.core.reporting import Reportable
from backend.llm.registry import provider_registry

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

### llm/manager.py
```
# backend/llm/manager.py

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

### core/interfaces.py
```
# backend/core/interfaces.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from backend.core.types import ExecutionContext


class SubGraphRunner(ABC):
    """
    一个抽象接口，定义了执行子图的能力。
    这是引擎必须提供给需要回调的运行时的服务。
    """
    @abstractmethod
    async def execute_graph(
        self,
        graph_name: str,
        context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

class RuntimeInterface(ABC):
    """
    重新定义的运行时接口。
    它现在只依赖于 ExecutionContext 和可选的 SubGraphRunner。
    它不再知道 ExecutionEngine 的存在。
    """
    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        subgraph_runner: Optional[SubGraphRunner] = None,
        # 我们可以保留 pipeline_state 以支持节点内管道
        pipeline_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        :param config: 已求值的配置。
        :param context: 当前的执行上下文 (包含 world_state 等)。
        :param subgraph_runner: 一个可选的回调接口，用于执行子图。
        :param pipeline_state: 节点内上一步的输出。
        """
        pass

```

### core/services.py
```
# backend/core/services.py (新文件)
from typing import Dict, Any, Type, Callable

class ServiceInterface:
    """一个可选的基类或标记接口，用于所有服务。"""
    pass

class ServiceRegistry:
    """管理整个应用中的核心服务。"""
    def __init__(self):

        self._service_classes: Dict[str, Type[ServiceInterface]] = {}


    def register(self, name: str) -> Callable[[Type[ServiceInterface]], Type[ServiceInterface]]:
        """装饰器，用于注册服务类。"""
        def decorator(service_class: Type[ServiceInterface]) -> Type[ServiceInterface]:
            if name in self._service_classes:
                print(f"Warning: Overwriting service registration for '{name}'.")
            self._service_classes[name] = service_class
            print(f"Service '{name}' registered via decorator: {service_class.__name__}")
            return service_class
        return decorator

    def get_class(self, name: str) -> Type[ServiceInterface] | None:
        """获取已注册的服务类。"""
        return self._service_classes.get(name)

# 全局单例
service_registry = ServiceRegistry()
```

### core/registry.py
```
# backend/core/registry.py (修改后)
from typing import Dict, Type, Callable
from backend.core.interfaces import RuntimeInterface

class RuntimeRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    def register(self, name: str) -> Callable[[Type[RuntimeInterface]], Type[RuntimeInterface]]:
        """
        一个可以作为装饰器使用的注册方法。
        用法:
        @runtime_registry.register("system.input")
        class InputRuntime(RuntimeInterface):
            ...
        """
        def decorator(runtime_class: Type[RuntimeInterface]) -> Type[RuntimeInterface]:
            if name in self._registry:
                print(f"Warning: Overwriting runtime registration for '{name}'.")
            self._registry[name] = runtime_class
            print(f"Runtime '{name}' registered via decorator.")
            return runtime_class
        return decorator

    def get_runtime(self, name: str) -> RuntimeInterface:
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime '{name}' not found.")
        return runtime_class()

# 全局单例
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
from backend.core.types import ExecutionContext # 显式导入

# 预编译宏的正则表达式和预置模块保持不变...
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

### core/__init__.py
```

```

### core/types.py
```
# backend/core/types.py 
from __future__ import annotations
import json 
import asyncio # <-- 需要导入 asyncio 来处理锁
from typing import Dict, Any, Callable, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone

from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection
from backend.core.utils import DotAccessibleDict

ServiceRegistry = Dict[str, Any]

class SharedContext(BaseModel):
    """
    一个封装了所有图执行期间共享资源的对象。
    """
    world_state: Dict[str, Any]
    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    # 【核心修改】用一个通用的服务容器替代了特定的 llm_service
    services: DotAccessibleDict

    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    """
    代表一个【单次图执行】的上下文。
    它包含私有状态（如 node_states）和对全局共享状态的引用。
    """
    # --- 私有状态 (Per-Graph-Run State) ---
    # 每次调用 execute_graph 时，都会为这次运行创建一个新的 ExecutionContext
    # 这确保了 node_states 是隔离的。
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    
    # --- 共享状态 (Shared State) ---
    # 这不是一个副本，而是对一个共享对象的引用。
    shared: SharedContext
    initial_snapshot: StateSnapshot # 引用初始快照以获取图定义等信息

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def create_for_main_run(
        cls, 
        snapshot: StateSnapshot, 
        # 【核心修改】接收一个服务注册表，而不是某个特定服务
        services: ServiceRegistry, 
        run_vars: Dict[str, Any] = None
    ) -> 'ExecutionContext':
        """为顶层图执行创建初始上下文。"""
        shared_context = SharedContext(
            world_state=snapshot.world_state.copy(),
            session_info={
                "start_time": datetime.now(timezone.utc),
                "conversation_turn": 0,
            },
            global_write_lock=asyncio.Lock(),
            # 将传入的服务注册表包装成可点访问的字典，并存入共享上下文
            services=DotAccessibleDict(services)
        )
        return cls(
            shared=shared_context,
            initial_snapshot=snapshot,
            run_vars=run_vars or {}
        )

    @classmethod
    def create_for_sub_run(cls, parent_context: 'ExecutionContext', run_vars: Dict[str, Any] = None) -> 'ExecutionContext':
        """
        为子图（由 call/map 调用）创建一个新的执行上下文。
        关键在于它【共享】父上下文的 `shared` 对象。
        """
        return cls(
            # 传递对同一个共享对象的引用
            shared=parent_context.shared,
            # 初始快照和图定义保持不变
            initial_snapshot=parent_context.initial_snapshot,
            # 子运行可以有自己的 run_vars，例如 map 迭代时的 item
            run_vars=run_vars or {}
            # 注意：node_states 会自动被 Pydantic 创建为一个新的空字典，实现了隔离！
        )

    def to_next_snapshot(
        self,
        final_node_states: Dict[str, Any],
        triggering_input: Dict[str, Any]
    ) -> StateSnapshot:
        """从当前上下文的状态生成下一个快照。"""
        # 从共享状态中获取最终的世界状态
        final_world_state = self.shared.world_state
        
        current_graphs = self.initial_snapshot.graph_collection
        # 检查世界状态中是否有演化的图定义
        if '__graph_collection__' in final_world_state:
            try:
                evolved_graph_value = final_world_state['__graph_collection__']
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
            world_state=final_world_state, # 使用最终的世界状态
            parent_snapshot_id=self.initial_snapshot.id,
            run_output=final_node_states,
            triggering_input=triggering_input
        )

# 重建模型以确保所有引用都已解析
SharedContext.model_rebuild()
ExecutionContext.model_rebuild()
```

### core/engine.py
```
# backend/core/engine.py
import asyncio
from enum import Enum, auto
from typing import Dict, Any, Set, List, Optional
from collections import defaultdict

from backend.models import GraphCollection, GraphDefinition, GenericNode
from backend.core.dependency_parser import build_dependency_graph
from backend.core.registry import RuntimeRegistry
from backend.core.evaluation import build_evaluation_context, evaluate_data
from backend.core.types import ExecutionContext, ServiceRegistry
from backend.core.interfaces import RuntimeInterface, SubGraphRunner


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
        return self.dependencies.get(node_id, set())
    def get_subscribers(self, node_id: str) -> Set[str]:
        return self.subscribers.get(node_id, set())
    def get_execution_context(self) -> ExecutionContext:
        return self.context
    def get_final_node_states(self) -> Dict[str, Any]:
        return self.context.node_states

# ExecutionEngine 现在实现了 SubGraphRunner 接口
class ExecutionEngine(SubGraphRunner):
    def __init__(self, registry: RuntimeRegistry, services: ServiceRegistry, num_workers: int = 5):
        self.registry = registry
        # 【核心修改】在构造时接收并存储服务注册表
        self.services = services
        self.num_workers = num_workers

    async def step(self, initial_snapshot, triggering_input: Dict[str, Any] = None):
        if triggering_input is None: triggering_input = {}
        
        # 【核心修改】从 self.services 获取服务注册表并注入
        context = ExecutionContext.create_for_main_run(
            snapshot=initial_snapshot,
            services=self.services,  # <-- 从实例属性注入
            run_vars={"trigger_input": triggering_input}
        )
        
        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def: raise ValueError("'main' graph not found.")
        
        final_node_states = await self._internal_execute_graph(main_graph_def, context)
        next_snapshot = context.to_next_snapshot(final_node_states, triggering_input)
        return next_snapshot

    # --- 实现 SubGraphRunner 接口 ---
    async def execute_graph(
        self,
        graph_name: str,
        # 注意：这里接收的是一个 ExecutionContext，但我们将用它来创建子上下文
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """这是暴露给运行时的公共接口。"""
        graph_collection = parent_context.initial_snapshot.graph_collection.root
        graph_def = graph_collection.get(graph_name)
        if not graph_def:
            raise ValueError(f"Graph '{graph_name}' not found.")
        
        # --- 【关键】为子图运行创建自己的上下文 ---
        # 它会共享 world_state 和锁，但有自己的 node_states
        sub_run_context = ExecutionContext.create_for_sub_run(parent_context)

        return await self._internal_execute_graph(
            graph_def=graph_def,
            context=sub_run_context, # <-- 使用新的子上下文
            inherited_inputs=inherited_inputs
        )

    async def _internal_execute_graph(self, graph_def: GraphDefinition, context: ExecutionContext, inherited_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        内部核心调度器，用于执行一个图。
        
        :param graph_def: 要执行的图的 Pydantic 模型。
        :param context: 本次图执行的上下文（包含共享状态的引用和私有的 node_states）。
        :param inherited_inputs: (可选) 从父图（如 system.call 或 system.map）注入的预计算结果。
                                  这些被当作是已经“成功”的虚拟节点。
        :return: 一个字典，包含图中所有成功执行的节点的最终输出。
        """
        
        # --- 1. 初始化运行状态 ---
        # 创建一个 GraphRun 实例来管理这次运行的所有动态信息。
        # 这样可以将状态管理的复杂性从主函数中分离出去。
        run = GraphRun(context=context, graph_def=graph_def)

        # 创建一个异步任务队列，用于存放“准备就绪”可以执行的节点。
        task_queue = asyncio.Queue()
        
        # --- 2. 处理继承的输入 (用于子图) ---
        # 如果这是由 `call` 或 `map` 启动的子图，它可能会有 `inherited_inputs`。
        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                # 我们将这些注入的输入视为已经成功完成的“占位符”节点。
                # 尽管这些节点ID可能不在当前图的 `node_map` 中，我们仍然设置它们的状态和结果。
                run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, result)
        
        # --- 3. 确定初始的可执行节点 ---
        # 再次检查所有“待定”节点，看它们的依赖是否已经满足（可能因为继承的输入）。
        for node_id in run.get_nodes_in_state(NodeState.PENDING):
            dependencies = run.get_dependencies(node_id)
            # all() 在空集合上返回 True，这正是我们想要的。
            if all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in dependencies):
                run.set_node_state(node_id, NodeState.READY)
        
        # 将所有初始“准备就绪”的节点放入任务队列。
        for node_id in run.get_nodes_in_state(NodeState.READY):
            task_queue.put_nowait(node_id)

        # --- 4. 检查是否无事可做 ---
        # 如果队列是空的，并且没有任何节点是“成功”状态（意味着没有继承的输入），
        # 那么这个图从一开始就无法执行。直接返回空结果。
        if task_queue.empty() and not any(s == NodeState.SUCCEEDED for s in run.node_states.values()):
            print(f"Warning: Graph '{graph_def.nodes[0].id if graph_def.nodes else 'empty'}' has no runnable starting nodes.")
            return {}

        # --- 5. 启动工作者 (Worker) 并执行 ---
        # 创建一组并发的工作者任务，它们将从队列中获取并执行节点。
        workers = [
            asyncio.create_task(self._worker(f"worker-{i}", run, task_queue))
            for i in range(self.num_workers)
        ]
        
        # 等待队列中的所有任务都被处理完毕。
        # `task_queue.join()` 会阻塞，直到每个 `put()` 都有一个对应的 `task_done()`。
        await task_queue.join()

        # --- 6. 清理并返回结果 ---
        # 一旦所有任务完成，我们就不再需要工作者了。取消它们以释放资源。
        for w in workers:
            w.cancel()
        
        # 等待所有取消操作完成。
        await asyncio.gather(*workers, return_exceptions=True)
        
        # 从上下文中收集所有被标记为有结果的节点的输出，并返回。
        # 这里的 `run.get_node_result(nid) is not None` 也可以用于过滤掉未执行或失败的节点。
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
                # --- 将 _execute_node 的调用也包在 try...except 中 ---
                # 这样即使 _execute_node 内部的宏预处理失败，也能捕获
                output = await self._execute_node(node, context)
                if isinstance(output, dict) and "error" in output:
                    run.set_node_state(node_id, NodeState.FAILED)
                else:
                    run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, output)
            except Exception as e:
                # 这个捕获块现在变得更重要
                error_message = f"Worker-level error for node {node_id}: {type(e).__name__}: {e}"
                import traceback
                traceback.print_exc() # 打印完整的堆栈以供调试
                run.set_node_state(node_id, NodeState.FAILED)
                run.set_node_result(node_id, {"error": error_message})
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
        
        # 从共享上下文中获取锁
        lock = context.shared.global_write_lock

        for i, instruction in enumerate(node.run):
            runtime_name = instruction.runtime
            try:
                eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
                
                config_to_process = instruction.config.copy()
                runtime_instance: RuntimeInterface = self.registry.get_runtime(runtime_name)
                
                templates = {}
                template_fields = getattr(runtime_instance, 'template_fields', [])
                for field in template_fields:
                    if field in config_to_process:
                        templates[field] = config_to_process.pop(field)

                # --- 传递锁给求值函数 ---
                processed_config = await evaluate_data(config_to_process, eval_context, lock)

                if templates:
                    processed_config.update(templates)

                # --- 传递 self 作为 SubGraphRunner, context 作为上下文 ---
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
                # 打印详细的错误信息以便调试
                import traceback
                print(f"Error in node {node.id}, step {i} ({runtime_name}): {type(e).__name__}: {e}")
                traceback.print_exc()
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {type(e).__name__}: {e}"
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}
        return pipeline_state
```

### core/utils.py
```
# backend/core/utils.py

from typing import Any, Dict

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
```

### core/loader.py
```
# backend/core/loader.py
import os
import pkgutil
import importlib
from typing import List

def load_modules(directories: List[str]):
    """
    动态地扫描并导入指定目录下的所有 Python 模块。

    :param directories: 一个包含要扫描的包目录路径的列表 (e.g., ["backend.runtimes", "backend.llm.providers"])
    """
    print("\n--- Starting Dynamic Module Loading ---")
    for package_name in directories:
        try:
            package = importlib.import_module(package_name)
            
            # 使用 pkgutil.walk_packages 来安全地、递归地查找所有子模块
            for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    print(f"  - Failed to load module '{module_name}': {e}")
        except ImportError as e:
            print(f"Warning: Could not import package '{package_name}'. Skipping. Error: {e}")
    print("--- Finished Dynamic Module Loading ---\n")
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

def build_dependency_graph(nodes: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    dependency_map: Dict[str, Set[str]] = {}

    for node in nodes:
        node_id = node['id']
        auto_inferred_deps = set()
        for instruction in node.get('run', []):
            instruction_config = instruction.get('config', {})
            dependencies = extract_dependencies_from_value(instruction_config)
            auto_inferred_deps.update(dependencies)
        
        explicit_deps = set(node.get('depends_on') or [])

        all_dependencies = auto_inferred_deps.union(explicit_deps)
        
        # 不再过滤，保留所有依赖
        dependency_map[node_id] = all_dependencies
    
    return dependency_map
```

### core/reporting.py
```
# backend/core/reporting.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Type

class Reportable(ABC):
    """
    一个统一的汇报协议。
    任何希望向系统提供状态或元数据的组件都应实现此接口。
    """
    
    @property
    @abstractmethod
    def report_key(self) -> str:
        """
        返回此报告在最终JSON对象中的唯一键名。
        例如: "runtimes", "llm_providers", "system_stats"
        """
        pass

    @property
    def is_static(self) -> bool:
        """
        指明此报告是否为静态。
        True: 报告内容在应用启动后不变，可以被缓存。
        False: 报告内容是动态的，每次请求都需重新生成。
        默认值为静态。
        """
        return True

    @abstractmethod
    async def generate_report(self) -> Any:
        """
        生成并返回此组件的报告内容。
        内容可以是任何可以被JSON序列化的类型 (dict, list, str, etc.)。
        """
        pass

class AuditorRegistry:
    """一个简单的注册表，用于收集所有 Reportable 实例。"""
    def __init__(self):
        self._reportables: List[Reportable] = []

    def register(self, reportable: Reportable):
        """注册一个 Reportable 实例。"""
        print(f"Auditor: Registering reportable component with key '{reportable.report_key}'.")
        self._reportables.append(reportable)
    
    def get_all(self) -> List[Reportable]:
        return self._reportables

class Auditor:
    """
    审阅官服务。负责从注册表中收集所有报告并进行聚合。
    """
    def __init__(self, registry: AuditorRegistry):
        self._registry = registry
        self._static_report_cache: Dict[str, Any] | None = None

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

    async def _generate_static_reports(self) -> Dict[str, Any]:
        """仅生成并缓存所有静态报告。"""
        print("Auditor: Generating static report cache...")
        static_reports = {}
        tasks = []
        reportables = [r for r in self._registry.get_all() if r.is_static]
        for r in reportables:
            tasks.append(r.generate_report())
        
        results = await asyncio.gather(*tasks)
        
        for r, result in zip(reportables, results):
            static_reports[r.report_key] = result
        
        return static_reports

    async def _generate_dynamic_reports(self) -> Dict[str, Any]:
        """仅生成所有动态报告。"""
        dynamic_reports = {}
        tasks = []
        reportables = [r for r in self._registry.get_all() if r.is_static is False]
        if not reportables:
            return {}
            
        for r in reportables:
            tasks.append(r.generate_report())
        
        results = await asyncio.gather(*tasks)
        
        for r, result in zip(reportables, results):
            dynamic_reports[r.report_key] = result
            
        return dynamic_reports

# 全局单例
auditor_registry = AuditorRegistry()
```

### runtimes/__init__.py
```

```

### runtimes/base_runtimes.py
```
# backend/runtimes/base_runtimes.py
import asyncio 
from typing import Dict, Any, Optional
from backend.core.interfaces import RuntimeInterface
from backend.core.registry import runtime_registry 
from backend.core.types import ExecutionContext
from backend.llm.models import LLMResponse, LLMRequestFailedError

@runtime_registry.register("system.input") 
class InputRuntime(RuntimeInterface):
    """从 config 中获取 'value'。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value", "")}

@runtime_registry.register("llm.default")
class LLMRuntime(RuntimeInterface):
    """
    一个轻量级的运行时，它通过 Hevno LLM Gateway 发起 LLM 调用。
    它的职责是：
    1. 从 config 中解析出调用意图（模型、prompt 等）。
    2. 从上下文中获取 LLMService。
    3. 调用 LLMService.request()。
    4. 将结果（成功或失败）格式化为标准的节点输出。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        # ... (解析 config 的逻辑不变) ...
        model_name = config.get("model")
        prompt = config.get("prompt")
        llm_params = {k: v for k, v in config.items() if k not in ["model", "prompt"]}

        if not model_name:
            raise ValueError("LLMRuntime requires a 'model' field in its config (e.g., 'gemini/gemini-1.5-flash').")
        if not prompt:
            raise ValueError("LLMRuntime requires a 'prompt' field in its config.")

        # 所有非'model'和'prompt'的键都作为额外参数传递
        llm_params = {k: v for k, v in config.items() if k not in ["model", "prompt"]}

        # 2. 从共享上下文中获取 LLM Service
        llm_service = context.shared.services.llm

        try:
            # 3. 调用 Gateway
            response: LLMResponse = await llm_service.request(
                model_name=model_name,
                prompt=prompt,
                **llm_params
            )
            
            # 4. 处理成功或过滤的响应
            if response.error_details:
                # 这是一个“软失败”，比如内容过滤
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
            # 5. 处理硬失败（所有重试都用尽后）
            print(f"ERROR: LLM request failed for node after all retries. Error: {e}")
            return {
                "error": str(e),
                "details": e.last_error.model_dump() if e.last_error else None
            }

@runtime_registry.register("system.set_world_var")
class SetWorldVariableRuntime(RuntimeInterface):
    """从 config 中获取变量名和值，并设置一个持久化的世界变量。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        variable_name = config.get("variable_name")
        value_to_set = config.get("value")

        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name' in its config.")
        
        context.shared.world_state[variable_name] = value_to_set
        
        return {}
```

### runtimes/control_runtimes.py
```
# backend/runtimes/control_runtimes.py
import asyncio
from typing import Dict, Any, List, Optional

from backend.core.interfaces import RuntimeInterface, SubGraphRunner # <-- 从新位置导入
# 导入所有需要的核心组件
from backend.core.evaluation import evaluate_data, evaluate_expression, build_evaluation_context
from backend.core.types import ExecutionContext
from backend.core.utils import DotAccessibleDict
from backend.core.registry import runtime_registry

@runtime_registry.register("system.execute")
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

@runtime_registry.register("system.call")
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

@runtime_registry.register("system.map")
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

### runtimes/reporters.py
```
# backend/runtimes/reporters.py
from typing import Any, Dict, Type
from backend.core.reporting import Reportable
from backend.core.registry import runtime_registry
from backend.core.interfaces import RuntimeInterface

class RuntimeReporter(Reportable):
    
    @property
    def report_key(self) -> str:
        return "runtimes"

    async def generate_report(self) -> Any:
        report = []
        # 注意：这里我们不再需要一个特殊的自省接口，
        # 我们直接使用运行时类本身声明的元数据。
        for name, runtime_class in runtime_registry._registry.items():
            # 假设 RuntimeInterface 增加了 config_model, description, category
            # (这个设计依然很好，可以保留)
            config_model = getattr(runtime_class, 'config_model', None)
            
            report.append({
                "name": name,
                "description": getattr(runtime_class, 'description', "N/A"),
                "category": getattr(runtime_class, 'category', "General"),
                "config_schema": config_model.model_json_schema() if config_model else {}
            })
        return sorted(report, key=lambda x: x['name'])
```

### api/reporters.py
```
# backend/api/reporters.py
from typing import Dict, Any
from backend.core.reporting import Reportable

class SandboxStatsReporter(Reportable):
    # 接收 main.py 中的状态存储作为依赖
    def __init__(self, sandbox_store: Dict, snapshot_store):
        self._sandbox_store = sandbox_store
        self._snapshot_store = snapshot_store

    @property
    def report_key(self) -> str:
        return "system_stats"

    @property
    def is_static(self) -> bool:
        # 这是一个动态报告！
        return False

    async def generate_report(self) -> Any:
        # 每次调用都实时计算
        active_sandboxes = len(self._sandbox_store)
        total_snapshots = len(self._snapshot_store._store) # 假设可以访问内部存储
        
        # 甚至可以报告更复杂的信息
        graphs_in_use = set()
        for sandbox in self._sandbox_store.values():
            latest_snapshot = sandbox.get_latest_snapshot(self._snapshot_store)
            if latest_snapshot:
                graphs_in_use.update(latest_snapshot.graph_collection.root.keys())

        return {
            "active_sandbox_count": active_sandboxes,
            "total_snapshot_count": total_snapshots,
            "unique_graph_names_in_use": sorted(list(graphs_in_use))
        }
```

### runtimes/codex/invoke_runtime.py
```
# backend/runtimes/codex/invoke_runtime.py
import asyncio
import re
from typing import Dict, Any, List, Optional, Set
import pprint  # 导入 pprint 以便美观地打印字典

from pydantic import ValidationError

from backend.core.interfaces import RuntimeInterface
from backend.core.types import ExecutionContext
from backend.core.evaluation import evaluate_data, build_evaluation_context
from backend.core.utils import DotAccessibleDict
from backend.core.registry import runtime_registry

from .models import CodexCollection, ActivatedEntry

from .models import TriggerMode

@runtime_registry.register("system.invoke")
class InvokeRuntime(RuntimeInterface):
    """
    system.invoke 运行时的实现。
    """
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        **kwargs
    ) -> Dict[str, Any]:
        # --- 0. 准备工作 ---
        from_sources = config.get("from", [])
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
        
        structural_eval_context = build_evaluation_context(context)

        for source_config in from_sources:
            codex_name = source_config.get("codex")
            if not codex_name: continue
            
            codex_model = codex_collection.get(codex_name)
            if not codex_model:
                raise ValueError(f"Codex '{codex_name}' not found in world.codices.")

            source_text_macro = source_config.get("source", "")
            source_text = await evaluate_data(source_text_macro, structural_eval_context, lock) if source_text_macro else ""

            for entry in codex_model.entries:
                is_enabled = await evaluate_data(entry.is_enabled, structural_eval_context, lock)
                if not is_enabled:
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
                        if re.search(re.escape(str(keyword)), source_text, re.IGNORECASE):
                            matched_keywords.append(keyword)
                    if matched_keywords:
                        is_activated = True
                
                if is_activated:
                    activated = ActivatedEntry(
                        entry_model=entry, codex_name=codex_name, codex_config=codex_model.config,
                        priority_val=int(priority), keywords_val=keywords, is_enabled_val=bool(is_enabled),
                        source_text=source_text, matched_keywords=matched_keywords
                    )
                    initial_pool.append(activated)
                    initial_activation_trace.append({
                        "id": entry.id, "priority": int(priority),
                        "reason": entry.trigger_mode.value,
                        "matched_keywords": matched_keywords
                    })
        
        # --- 2. 阶段二：渲染与注入 (Content Evaluation) ---
        final_text_parts = []
        rendered_entry_ids: Set[str] = set()
        rendering_pool = sorted(initial_pool, key=lambda x: x.priority_val, reverse=True)
        evaluation_log = []
        recursive_activations = []

        recursion_depth_counter = 0
        max_depth = max((act.codex_config.recursion_depth for act in rendering_pool), default=3) if rendering_pool else 3

        loop_count = 0
        while rendering_pool and (not recursion_enabled or recursion_depth_counter < max_depth):
            loop_count += 1
            rendering_pool.sort(key=lambda x: x.priority_val, reverse=True)
            
            entry_to_render = rendering_pool.pop(0)

            if entry_to_render.entry_model.id in rendered_entry_ids:
                continue

            content_eval_context = build_evaluation_context(context)
            content_eval_context['trigger'] = DotAccessibleDict({
                "source_text": entry_to_render.source_text,
                "matched_keywords": entry_to_render.matched_keywords
            })

            rendered_content = await evaluate_data(entry_to_render.entry_model.content, content_eval_context, lock)
            
            final_text_parts.append(str(rendered_content))
            rendered_entry_ids.add(entry_to_render.entry_model.id)
            evaluation_log.append({"id": entry_to_render.entry_model.id, "status": "rendered"})
            
            if recursion_enabled:
                recursion_depth_counter += 1
                new_source_text = str(rendered_content)
                
                for codex_name, codex_model in codex_collection.items():
                    for entry in codex_model.entries:
                        if entry.id in rendered_entry_ids or any(p.entry_model.id == entry.id for p in rendering_pool):
                            continue
                        
                        if entry.trigger_mode == TriggerMode.ON_KEYWORD:
                            is_enabled = await evaluate_data(entry.is_enabled, structural_eval_context, lock)
                            if not is_enabled: continue

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
                                recursive_activations.append({
                                    "id": entry.id, "priority": int(priority),
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
            return {
                "output": {
                    "final_text": final_text,
                    "trace": trace_data
                }
            }
        
        return {"output": final_text}

```

### runtimes/codex/models.py
```
# backend/runtimes/codex/models.py
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

### runtimes/codex/__init__.py
```

```

### llm/providers/__init__.py
```

```

### llm/providers/gemini.py
```
# backend/llm/providers/gemini.py

from typing import Dict, Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from google.generativeai import types as generation_types

from backend.llm.providers.base import LLMProvider
from backend.llm.models import (
    LLMResponse,
    LLMError,
    LLMResponseStatus,
    LLMErrorType,
)
from backend.llm.registry import provider_registry

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

### llm/providers/base.py
```
# backend/llm/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any

from backend.llm.models import LLMResponse, LLMError


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
