// src/data/defaultPipeline.js (丰富交互版)

export const defaultPipeline = [
    {
        "id": "stage_setter",
        "name": "场景与背景设定器",
        "enabled": true,
        "llm": { "model": "gpt-3.5-turbo" },
        "promptSlots": [
            {
                "id": "task_description",
                "role": "system",
                "enabled": true,
                "content": "你是一个场景导演。根据以下信息，生成一段充满氛围的开场白，为接下来的故事奠定基调。"
            },
            {
                "id": "character_info",
                "role": "user",
                "enabled": true,
                "content": `
# 角色核心设定
{{sillyTavern.character.description}}

# 角色性格
{{sillyTavern.character.personality}}

# 作者笔记/全局指令
{{sillyTavern.authorsNote}}
                `
            },
            {
                "id": "world_info",
                "role": "user",
                "enabled": true,
                "content": `
# 世界观与关键信息
{{sillyTavern.worldInfo}}
                `
            }
        ]
    },
    {
        "id": "history_summarizer",
        "name": "历史摘要器",
        "enabled": true,
        "llm": { "model": "gpt-3.5-turbo" },
        "promptSlots": [
            {
                "id": "summarize_task",
                "role": "system",
                "enabled": true,
                "content": "将以下对话历史浓缩成一段简洁的摘要，不超过200字，捕捉核心情节和人物情绪。"
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
                "id": "combined_context",
                "role": "system",
                "enabled": true,
                "content": `
# 场景与基调
{{outputs.stage_setter}}

# 历史回顾
{{outputs.history_summarizer}}

请基于以上背景，并以前次对话的风格，继续下面的故事。
                `
            },
            {
                "id": "user_latest_input",
                "role": "user",
                "enabled": true,
                "content": "{{sillyTavern.userInput}}"
            }
        ]
    },
    {
        "id": "style_enhancer",
        "name": "文笔润色器",
        "enabled": true,
        "llm": { "model": "gpt-4" },
        "promptSlots": [
            {
                "id": "style_task",
                "role": "system",
                "enabled": true,
                "content": "你是一位文学大师。请将以下文本用更具诗意和表现力的语言重写，但保持原意不变。"
            },
            {
                "id": "original_text",
                "role": "user",
                "enabled": true,
                "content": "{{outputs.main_story_generator}}"
            }
        ]
    },
    {
        "id": "emotion_detector",
        "name": "情绪分析器",
        "enabled": true,
        "llm": { "model": "gpt-3.5-turbo" },
        "promptSlots": [
            {
                "id": "emotion_task",
                "role": "system",
                "enabled": true,
                "content": "分析以下文本中表达的主要情绪。用一个词回答，例如：喜悦、悲伤、愤怒、惊讶、平静。"
            },
            {
                "id": "text_to_analyze",
                "role": "user",
                "enabled": true,
                "content": "{{outputs.main_story_generator}}"
            }
        ]
    },
    {
        "id": "final_formatter",
        "name": "最终格式化模块",
        "enabled": true,
        "llm": { "model": "gpt-3.5-turbo" },
        "promptSlots": [
            {
                "id": "format_task",
                "role": "system",
                "enabled": true,
                "content": "你是一个格式化助手。将主文本和情绪标签组合成最终的输出。格式如下：\n[角色当前情绪：<情绪标签>]\n\n<主文本>"
            },
            {
                "id": "final_content",
                "role": "user",
                "enabled": true,
                "content": `
情绪标签：{{outputs.emotion_detector}}
主文本：{{outputs.style_enhancer}}
                `
            }
        ]
    }
];