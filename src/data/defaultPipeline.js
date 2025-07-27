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
        "llm": { "provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.8 },
        "promptSlots": [{
            "enabled": true,
            "content": "你是一位富有想象力的小说家。请根据用户的请求，创作一个包含多个角色的、戏剧性的中世纪奇幻小说。场景描述需要生动，并明确介绍至少两名出场角色的名字和简要特征，为后续情节发展埋下伏笔。\n\n用户请求:\n{{sillyTavern.userInput}}\n\n你的输出必须是一段200字以上的流畅的故事，不能包含任何控制文本或者指令。"
        }]
    },
    
    // 节点 2: 角色识别LLM
    {
        "id": "character_identifier_llm",
        "name": "2. LLM识别角色",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.1 },
        "promptSlots": [{
            "enabled": true,
            "content": "分析工具：严格按照 'Characters: 角色A, 角色B, 角色C' 的格式，从以下文本中提取所有被命名的角色。如果一个角色都没有，必须输出 'Characters: None'。不要添加任何其他解释或前言。\n\n文本：\n{{outputs.story_generator}}"
        }]
    },

    // 节点 3: 解析角色列表 (使用保留的便利函数)
    // 尽管有更通用的regexExtract，但parseCharacterList对于这个常见任务更方便。
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
        "joinNode": "aggregate_character_actions", // 指定下一步的聚合节点
        "templateNode": { // 这是为每个角色动态创建的LLM节点的模板
            "id": "character_action_template", // 临时ID
            "name": "角色行动分析模板",
            "type": "llm",
            "llm": { "provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.7 },
            "worldInfo": ["Character-Backstory.json"], // 假设这是一个包含角色背景的世界书
            "promptSlots": [{
                "enabled": true,
                "content": "当前场景中有一位名叫 '{{item}}' 的角色。基于TA的背景故事和当前场景，设想TA接下来最可能的一个具体行动和一段内心独白。以第三人称小说风格进行描述。\n\n# 角色 '{{item}}' 的背景\n{{module.worldInfo}}\n\n# 当前场景\n{{outputs.story_generator}}"
            }]
        }
    },

    // 节点 5: Join/Reduce节点 - 聚合所有角色的行动
    // 【重大改进】使用新的 'joinFromDynamicNodes' 函数
    {
        "id": "aggregate_character_actions",
        "name": "5. 聚合角色行动",
        "enabled": true,
        "type": "function",
        "functionName": "joinFromDynamicNodes",
        "params": {
            // itemTemplate 定义了每个动态节点的输出如何被格式化
            "itemTemplate": "关于角色“{{item}}”的行动构想：\n{{output}}",
            // separator 定义了各项之间如何连接
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
        "llm": { "provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.0 }, // temperature=0.0 使输出更稳定
        "promptSlots": [{
            "enabled": true,
            "content": "分析以下场景描述中是否隐含了即将发生的物理冲突或战斗意图。你的回答只能是 'Yes' 或 'No'，不要包含任何其他字符或解释。\n\n场景:\n{{outputs.aggregate_character_actions}}"
        }]
    },
    
    // 节点 7: 战斗决策路由器
    // 【重大改进】这里不直接用 combat_check_llm 的输出，而是先通过一个函数节点返回布尔值，
    // 这样路由器的条件就是 "true" 或 "false"，更加稳健。
    // (虽然直接匹配 "Yes" 也可以，但这是一个展示组合性的好例子)
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
        "condition": "{{outputs.combat_decision_function}}", // 依赖函数节点的布尔输出
        "routes": { 
            "true": "combat_module",    // 如果是 true，走向战斗分支
            "false": "peaceful_module"  // 如果是 false，走向和平分支
        }
    },

    // 节点 9a & 9b: 剧情分支
    {
        "id": "combat_module",
        "name": "9a. 战斗流程",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.9 },
        "promptSlots": [{ "enabled": true, "content": "续写下面的故事，引入一场激烈的战斗。详细描写战斗的起因和最初的几个回合。\n\n故事背景：\n{{outputs.aggregate_character_actions}}" }]
    },
    {
        "id": "peaceful_module",
        "name": "9b. 和平流程",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.6 },
        "promptSlots": [{ "enabled": true, "content": "续写下面的故事，展开一段充满紧张感的对话或非暴力冲突。聚焦于角色的心理博弈和潜台词。\n\n故事背景：\n{{outputs.aggregate_character_actions}}" }]
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
        "llm": { "provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.5 },
        "promptSlots": [{
            "enabled": true,
            // 这个 prompt 现在可以安全地处理空输入了，因为 {{outputs.combat_module}} 或 {{outputs.peaceful_module}}
            // 在被跳过时，模板渲染会将其视为空字符串。
            "content": "你是一位优秀的故事编辑。你的任务是优化和完善下面的“主要故事文本”。\n如果下面的“附加续写”部分有内容，请将其无缝地融入主要故事文本中，形成一个连贯、流畅的故事段落。如果“附加续写”部分为空，你只需对“主要故事文本”进行润色和续写，确保它有一个自然的结尾即可。\n你的最终输出必须是完整的故事，不要包含任何解释或标签。\n\n[主要故事文本]\n{{outputs.story_generator}}\n\n[附加续写]\n{{outputs.combat_module}}{{outputs.peaceful_module}}"
        }]
    }
];