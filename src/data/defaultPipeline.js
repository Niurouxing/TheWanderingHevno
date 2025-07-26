// src/data/defaultPipeline.js (修复版)
export const defaultPipeline = [
    {
        "id": "history_summarizer",
        // ... 此模块保持不变
        "name": "历史摘要器",
        "enabled": true,
        "llm": { "model": "gpt-3.5-turbo" },
        "promptSlots": [
            {
                "id": "summarize_task",
                "role": "system",
                "enabled": true,
                "content": "请将以下对话历史浓缩成一段简洁的摘要，不超过200字，捕捉核心情节和人物情绪。"
            },
            {
                "id": "chat_history",
                "role": "user",
                "enabled": true,
                "content": "{{sillyTavern.chat}}"
            }
        ]
    },
    {
        "id": "main_story_generator",
        "name": "主故事生成器",
        "enabled": true,
        "llm": { "model": "claude-3-opus-20240229" },
        "promptSlots": [
            {
                "id": "system_persona",
                "role": "system",
                "enabled": true,
                // ================== 【核心修复点】 ==================
                // 将不存在的 `persona` 替换为 `description`, `personality`, 和 `scenario` 的组合。
                // 这样即使某些字段为空，也不会影响整体结构。
                "content": `
# 角色设定
## 核心描述
{{sillyTavern.character.description}}

## 性格与背景
{{sillyTavern.character.personality}}

## 当前场景
{{sillyTavern.character.scenario}}
                `
                // ==================================================
            },
            {
                "id": "history_summary",
                "role": "user",
                "enabled": true,
                "content": "之前的对话摘要：\n{{outputs.history_summarizer}}"
            },
            {
                "id": "user_latest_input",
                "role": "user",
                "enabled": true,
                "content": "用户的最新输入：\n{{sillyTavern.userInput}}"
            }
        ]
    },
    {
        "id": "format_checker",
        "name": "格式检查器",
        "enabled": true,
        "llm": { "model": "gpt-3.5-turbo" },
        "promptSlots": [
            {
                "id": "check_task",
                "role": "user",
                "enabled": true,
                "content": "检查以下文本是否包含不当内容。如果安全，只回答'SAFE'。\n\n{{outputs.main_story_generator}}"
            }
        ]
    }
];