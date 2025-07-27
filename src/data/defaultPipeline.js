export const defaultPipeline = [
    // 节点 0: 故事生成器
    {
        "id": "story_generator",
        "name": "0. 故事生成器",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.8 }, // 建议使用 2.5-flash，能力更强
        "promptSlots": [{
            "enabled": true,
            // 【优化】更具体的指令，要求明确列出角色
            "content": "你是一位富有想象力的小说家。请根据用户的请求，创作一个包含多个角色的、戏剧性的中世纪奇幻小说。场景描述需要生动，并明确介绍至少两名出场角色的名字和简要特征，为后续情节发展埋下伏笔。\n\n用户请求:\n{{sillyTavern.userInput}}\n你的输出必须是一段200字以上的流畅的故事，不能包含任何控制文本或者指令"  
        }]
    },
    // 节点 1: 识别角色
    {
        "id": "character_identifier",
        "name": "1. 识别角色",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.1 },
        "promptSlots": [{
            "enabled": true,
            // 【优化】更严格的格式要求，减少废话
            "content": "分析工具：严格按照 'Characters: 角色A, 角色B, 角色C' 的格式，从以下文本中提取所有被命名的角色。如果一个角色都没有，必须输出 'Characters: None'。不要添加任何其他解释或前言。\n\n文本：\n{{outputs.story_generator}}"
        }]
    },
    // 节点 2: 解析角色列表 (JS函数，无需修改)
    {
        "id": "parse_character_list",
        "name": "2. 解析角色列表",
        "enabled": true,
        "type": "function",
        "functionName": "parseCharacterList",
        "params": { "sourceNode": "character_identifier" }
    },
    // 节点 3: 动态角色分析 (Map)
    {
        "id": "dynamic_character_analysis_map",
        "name": "3. 动态角色分析 (Map)",
        "enabled": true,
        "type": "map",
        "inputListRef": "{{outputs.parse_character_list}}",
        "joinNode": "aggregate_character_actions",
        "templateNode": {
            "id": "character_action_template",
            "name": "角色行动分析模板",
            "type": "llm",
            "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.7 },
            "worldInfo": ["Character-Backstory.json"], // 假设这是一个包含角色背景的世界书
            "promptSlots": [{
                "enabled": true,
                // 【优化】更聚焦的指令
                "content": "当前场景中有一位名叫 '{{item}}' 的角色。基于TA的背景故事和当前场景，设想TA接下来最可能的一个具体行动和一段内心独白。以第三人称小说风格进行描述。\n\n# 角色 '{{item}}' 的背景\n{{module.worldInfo}}\n\n# 当前场景\n{{outputs.story_generator}}"
            }]
        }
    },
    // 节点 4: 聚合行动 (JS函数，无需修改)
    {
        "id": "aggregate_character_actions",
        "name": "4. 聚合行动",
        "enabled": true,
        "type": "function",
        "functionName": "aggregateStoryParts",
        "params": {}
    },
    // 节点 5: 战斗检查
    {
        "id": "combat_check",
        "name": "5. 战斗检查",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.0 }, // temperature=0.0 使输出更稳定
        "promptSlots": [{
            "enabled": true,
            // 【优化】强制单字输出
            "content": "分析以下场景描述中是否隐含了即将发生的物理冲突或战斗意图。你的回答只能是 'Yes' 或 'No'，不要包含任何其他字符或解释。\n\n场景:\n{{outputs.aggregate_character_actions}}"
        }]
    },
    // 节点 6: 战斗路由器 (无需修改)
    {
        "id": "combat_router",
        "name": "6. 战斗路由器",
        "enabled": true,
        "type": "router",
        "condition": "{{outputs.combat_check}}",
        "routes": { "Yes": "combat_module", "No": "peaceful_module" }
    },
    // 节点 7 & 8: 分支
    {
        "id": "combat_module",
        "name": "7a. 战斗流程",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.9 },
        "promptSlots": [{ "enabled": true, "content": "续写下面的故事，引入一场激烈的战斗。详细描写战斗的起因和最初的几个回合。\n\n故事背景：\n{{outputs.aggregate_character_actions}}" }]
    },
    {
        "id": "peaceful_module",
        "name": "7b. 和平流程",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.6 },
        "promptSlots": [{ "enabled": true, "content": "续写下面的故事，展开一段充满紧张感的对话或非暴力冲突。聚焦于角色的心理博弈和潜台词。\n\n故事背景：\n{{outputs.aggregate_character_actions}}" }]
    },
    // 节点 9: 最终整合器
    {
        "id": "final_formatter",
        "name": "Final Formatter",
        "enabled": true,
        "type": "llm",
        "llm": { "provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.5 },
        "promptSlots": [{
            "enabled": true,
            // 【优化】这个 prompt 现在可以安全地处理空输入了
            "content": "你是一位优秀的故事编辑。你的任务是优化和完善下面的“主要故事文本”。\n如果下面的“附加续写”部分有内容，请将其无缝地融入主要故事文本中，形成一个连贯、流畅的故事段落。如果“附加续写”部分为空，你只需对“主要故事文本”进行润色和续写，确保它有一个自然的结尾即可。\n你的最终输出必须是完整的故事，不要包含任何解释或标签。\n\n[主要故事文本]\n{{outputs.story_generator}}\n\n[附加续写]\n{{outputs.combat_module}}{{outputs.peaceful_module}}"
        }]
    }
];