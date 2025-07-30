
# Hevno Backend Engine

欢迎来到 Hevno 项目的后端引擎！这是一个高度可扩展、由配置驱动的图执行引擎，旨在为复杂的、多步骤的LLM应用提供动力。

## 核心设计哲学

本项目的构建基于一个核心哲学：**“拒绝类型爆炸，拥抱配置组合”**。

在许多工作流或节点编辑器系统中，功能的增加往往伴随着新节点类型（`If-Else Node`, `Loop Node`, `Sub-Flow Node` 等）的涌入。这种方式虽然初看直观，但长期来看会导致系统变得复杂、僵化，并增加用户的学习成本。

我们采取了截然不同的方法：

1.  **极简的节点结构**: 我们只有一个通用的节点模型 (`GenericNode`)。一个节点是“LLM调用”还是“代码执行”，不由其类型决定。

2.  **行为由运行时配置决定**: 节点是一个“变色龙”，其具体行为完全由其数据负载中的 `runtime` 字段指定。这意味着我们可以通过增加新的`runtime`实现来无限扩展功能，而无需修改或增加基础节点结构。

    *   **旧方式 (我们避免的)**:
        ```json
        {"type": "LLMNode", "prompt": "..."}
        {"type": "CodeNode", "code": "..."}
        ```

    *   **Hevno 的方式 (我们采用的)**:
        ```json
        {"type": "default", "data": {"runtime": "llm.default", "prompt": "..."}}
        {"type": "default", "data": {"runtime": "code.python", "code": "..."}}
        ```

3.  **元能力下沉为核心函数**: 像“修改流图”或“创建新节点”这样的系统级“元能力”，我们不将其实现为特殊的节点类型。相反，它们将被实现为可供任何运行时调用的内置核心函数。这使得系统的核心功能和用户自定义功能在结构上完全等价，极大地增强了统一性和灵活性。

这种设计使得 Hevno 不仅仅是一个应用，更是一个构建AI原生工作流的**框架**。




# Hevno Engine: JSON 格式与 Map 功能设计规范

本文档定义了 Hevno 引擎的图（Graph）数据格式，并重点阐述了 `map` 和 `call` 这两个核心运行时的设计与实现约定。我们的核心设计哲学是**约定优于配置 (Convention over Configuration)**，旨在通过隐式约定和自动化推断，最大化框架的易用性和表达力。

## 1. 核心数据结构：图集合（Graph Collection）

系统中只有一个顶层概念：**可被命名的图（Graph）的集合**。一个完整的工作流定义就是一个包含一个或多个图的JSON对象。

-   整个配置文件是一个JSON对象，其`key`为图的唯一名称（`Graph ID`），`value`为图的定义。
-   **约定入口图的名称必须为 `"main"`**。引擎执行时将从此图开始。
-   **不再需要 `edges` 字段**。节点间的依赖关系由引擎通过解析宏引用自动推断。

**示例结构:**

```json
{
  "main": {
    "nodes": [
      // ... main graph's nodes ...
    ]
  },
  "process_character_arc": {
    "nodes": [
      // ... nodes for a reusable character processing graph ...
    ]
  }
}
```

## 2. 节点（Node）

节点是图的基本执行单元。

```json
{
  "id": "unique_node_id",
  "data": {
    "runtime": "runtime_name"_or_["runtime_A", "runtime_B"],
    // ... other key-value pairs for runtime configuration ...
  }
}
```

-   `id`: 在其所在的图（Graph）内必须唯一。
-   `data.runtime`: 指定该节点执行一个或一个流水线（pipeline）的运行时。
-   `data` 中的其他字段为运行时的配置参数。

## 3. 宏与依赖推断

引擎通过静态解析节点 `data` 中字符串值的宏 `{{ ... }}` 来自动构建依赖图。

-   **语法:** `{{ <expression> }}`
-   **核心对象:** `nodes`, `vars`, `session` 等。
-   **依赖推断规则:**
    -   当宏的格式为 `{{ nodes.<node_id>.<...> }}` 时，引擎会自动建立从 `<node_id>` 到当前节点的执行依赖。
    -   **重要限制**: 用于依赖推断的 `<node_id>` **目前必须是静态的字面量字符串**。动态的节点引用（如 `{{ nodes[vars.dynamic_id].output }}`）不用于构建初始依赖图，其依赖关系只能在运行时解析，可能导致执行时因依赖未就绪而失败。这将在未来版本中改进。

## 4. 核心运行时

### 4.1 `map` 运行时：Fan-out / Scatter-Gather

`map` 运行时是实现并行迭代的核心。它将一个子图（subgraph）并发地应用到输入列表的每个元素上。

#### **调用格式**

```json
{
  "id": "map_characters",
  "data": {
    "runtime": "system.map",
    // 1. 指定要迭代的列表
    "list": "{{ nodes.data_provider.characters_list }}",
    // 2. 指定要调用的图的名称
    "graph": "process_character_arc",
    // 3. (可选) 精细化地聚合输出
    "collect": "{{ nodes.internal_summary_node.summary }}",
    // 4. 定义如何将外部数据映射到子图的输入占位符
    "using": {
      "character_input": "{{ source.item }}",
      "iteration_info": "{{ source.index }}",
      "external_data": "{{ nodes.some_other_node.value }}"
    }
  }
}
```

#### **核心概念与引擎行为**

1.  **输入占位符 (Input Placeholder):**
    -   在一个被调用的子图（如 `"process_character_arc"`）中，如果一个宏引用了一个**在该图内部不存在的节点ID**（如 `{{ nodes.character_input.name }}`），这个ID (`character_input`) 就被引擎自动识别为一个**输入占位符**。

2.  **输入映射 (`using`):**
    -   `using` 字段的作用是告诉 `map` 运行时如何**满足**子图的输入占位符。
    -   `key` (e.g., `"character_input"`): 必须匹配子图中的输入占位符ID。
    -   `value` (e.g., `"{{ source.item }}"`): 是一个表达式，其值将被注入。
    -   **`source` 对象:** 这是一个特殊的、**只在 `using` 字段的宏表达式中有效**的保留对象，它代表了当前的迭代状态。它包含以下属性：
        -   `source.item`: 当前正在迭代的列表元素。
        -   `source.index`: 当前迭代的从0开始的索引。
        -   `source.list`: 对整个原始迭代列表的引用。

3.  **执行流程:**
    a. `map` 运行时获取 `list` 中的列表。
    b. 对于列表中的每一个 `item`，引擎在内存中创建一个子图的独立执行实例。
    c. 根据 `using` 映射规则，在子图实例的初始状态中**创建虚拟的、已成功的占位符节点**。
    d. 并发地执行所有这些独立的子图实例。
    e. **ID 命名空间:** 为避免冲突，引擎在内部会自动为子图中的节点ID添加唯一前缀。子图内部的宏引用会由引擎自动解析到正确的命名空间。

4.  **输出聚合:**
    -   `map` 运行时会等待所有子图实例执行完毕，并根据 `collect` 字段决定聚合方式：
        -   **如果 `collect` 字段未提供 (默认行为):**
            -   `map` 节点的 `output` 将是一个**列表**，每个元素是对应子图执行的**完整最终状态**。
        -   **如果 `collect` 字段已提供:**
            -   `map` 节点的 `output` 将是一个根据 `collect` 表达式从每个子图提取的值所组成的**扁平列表**。
            -   `collect` 表达式中的 `nodes` 对象指向其所在子图的内部节点。

### 4.2 `call` 运行时：子图调用

`call` 运行时用于实现非迭代式的、单一的子图调用，是代码复用的基础。

#### **调用格式**

```json
{
  "id": "process_main_character",
  "data": {
    "runtime": "system.call",
    "graph": "process_character_arc",
    "using": {
      "character_data": "{{ nodes.main_character_provider.output }}"
    }
  }
}
```

#### **核心概念与引擎行为**

-   **执行流程:**
    -   行为与 `map` 类似，但只执行一次。
    -   根据 `using` 映射，创建虚拟输入节点。
    -   执行 `process_character_arc` 图。
-   **输出:**
    -   `call` 节点的 `output` 就是被调用子图的**完整的最终状态字典**。下游节点可以通过 `{{ nodes.process_main_character.output.internal_summary_node.summary }}` 访问其内部结果。

---