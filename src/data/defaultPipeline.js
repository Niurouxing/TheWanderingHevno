export const defaultPipeline = [
    // =================================================================
    // 阶段 1: 故事创作与角色识别
    // =================================================================
    
    // 节点 1: 故事生成器
    {
        "id": "story_generator",
        "name": "1. 故事生成器",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.8 },
        "worldInfo": ["world_info"],
        "promptSlots": [{
            "enabled": true,
            "content": `你是一位富有想象力的小说家。请根据以下信息创作一个包含多个角色的、戏剧性的中世纪奇幻小说。

# 核心世界设定
{{module.worldInfo.before}}

# 用户信息:
- 用户名: {{sillyTavern.userName}}
- 用户请求: {{sillyTavern.userInput}}

# 角色设定:
- 角色名: {{sillyTavern.character.name}}

# 对话历史上下文:
{{sillyTavern.chat}}

# 场景与环境信息:
{{module.worldInfo.ANTop}}

# 补充世界信息:
{{module.worldInfo.after}}

场景描述需要生动，并明确介绍至少两名出场角色的名字和简要特征，为后续情节发展埋下伏笔。确保与之前的对话历史保持连贯性。你的输出必须是一段200字以上的流畅的故事，不能包含任何控制文本或者指令。`
        }]
    },
    
    // 节点 2: 角色识别LLM
    {
        "id": "character_identifier_llm",
        "name": "2. LLM识别角色",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.1 },
        "promptSlots": [{
            "enabled": true,
            "content": `分析工具：基于对话上下文和新故事，提取所有被命名的角色。

# 用户身份: {{sillyTavern.userName}}
# 对话角色: {{sillyTavern.character.name}}

# 对话历史:
{{sillyTavern.chat}}

# 新生成的故事:
{{outputs.story_generator}}

请严格按照 'Characters: 角色A, 角色B, 角色C' 的格式输出角色列表。如果没有角色，输出 'Characters: None'。不要添加任何其他解释或前言。`
        }]
    },

    // 节点 3: 解析角色列表
    {
        "id": "parse_character_list",
        "name": "3. 解析角色列表",
        "enabled": true,
        "type": "function",
        "functionName": "parseCharacterList",
        "params": { "sourceNode": "character_identifier_llm" }
    },

    // =================================================================
    // 阶段 2: 动态角色行动分析 (Map/Reduce 模式)
    // =================================================================

    // 节点 4: Map节点 - 为每个角色生成行动分析
    {
        "id": "dynamic_character_analysis_map",
        "name": "4. 动态角色分析 (Map)",
        "enabled": true,
        "type": "map",
        "inputListRef": "{{outputs.parse_character_list}}",
        "templateNode": {
            "id": "character_action_template",
            "name": "角色行动分析模板",
            "type": "llm",
            "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.7 },
            "worldInfo": ["character_info"],
            "promptSlots": [{
                "enabled": true,
                "content": `当前场景中有一位名叫 '{{item}}' 的角色。基于TA的背景故事和当前场景，设想TA接下来最可能的一个具体行动和一段内心独白。以第三人称小说风格进行描述。

# 角色基础信息
{{module.worldInfo.before}}

# 角色 '{{item}}' 的详细背景
{{module.worldInfo.after}}

# 当前场景
{{outputs.story_generator}}

`
            }]
        }
    },

    // 节点 5: 聚合角色行动 - 明确指定源Map节点
    {
        "id": "aggregate_character_actions",
        "name": "5. 聚合角色行动",
        "enabled": true,
        "type": "function",
        "functionName": "joinFromMapOutput",
        "params": {
            "sourceMapNode": "dynamic_character_analysis_map",
            "itemTemplate": `关于角色"{{item}}"的行动构想:
{{output}}`,
            "separator": "\n\n"
        }
    },

    // =================================================================
    // 阶段 3: 剧情分支 (Router 模式)
    // =================================================================
    
    // 节点 6: 战斗检查LLM
    {
        "id": "combat_check_llm",
        "name": "6. LLM检查战斗可能性",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.0 },
        "promptSlots": [{
            "enabled": true,
            "content": `分析以下场景描述中是否隐含了即将发生的物理冲突或战斗意图。你的回答只能是 'Yes' 或 'No'，不要包含任何其他字符或解释。

场景:
{{outputs.aggregate_character_actions}}`
        }]
    },
    
    // 节点 7: 战斗决策函数
    {
        "id": "combat_decision_function",
        "name": "7. 战斗决策函数",
        "enabled": true,
        "type": "function",
        "functionName": "textContains",
        "params": {
            "sourceNode": "combat_check_llm",
            "keyword": "Yes",
            "caseSensitive": false
        }
    },
    
    // 节点 8: 战斗路由器
    {
        "id": "combat_router",
        "name": "8. 战斗路由器",
        "enabled": true,
        "type": "router",
        "condition": "{{outputs.combat_decision_function}}",
        "routes": { 
            "true": "combat_module",
            "false": "peaceful_module"
        }
    },

    // 节点 9a & 9b: 剧情分支
    {
        "id": "combat_module",
        "name": "9a. 战斗流程",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.9 },
        "promptSlots": [{ 
            "enabled": true, 
            "content": `续写下面的故事，引入一场激烈的战斗。详细描写战斗的起因和最初的几个回合。

故事背景:
{{outputs.aggregate_character_actions}}`
        }]
    },
    {
        "id": "peaceful_module",
        "name": "9b. 和平流程",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.6 },
        "promptSlots": [{ 
            "enabled": true, 
            "content": `续写下面的故事，展开一段充满紧张感的对话或非暴力冲突。聚焦于角色的心理博弈和潜台词。

故事背景:
{{outputs.aggregate_character_actions}}`
        }]
    },

    // =================================================================
    // 阶段 4: 最终整合与清理
    // =================================================================

    // 节点 10: 最终整合器
    {
        "id": "final_formatter",
        "name": "10. 最终整合器",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.5 },
        "promptSlots": [{
            "enabled": true,
            "content": `你是一位优秀的故事编辑。你的任务是优化和完善下面的"主要故事文本"。
如果下面的"附加续写"部分有内容，请将其无缝地融入主要故事文本中，形成一个连贯、流畅的故事段落。如果"附加续写"部分为空，你只需对"主要故事文本"进行润色和续写，确保它有一个自然的结尾即可。
你的最终输出必须是完整的故事，不要包含任何解释或标签。

[主要故事文本]
{{outputs.story_generator}}

[附加续写]
{{outputs.combat_module}}{{outputs.peaceful_module}}`
        }]
    }
];