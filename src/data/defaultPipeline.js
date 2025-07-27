// src/data/defaultPipeline.js

export const defaultPipeline = [
    {
        "id": "scene_setter",
        "name": "1. 场景设定器",
        "enabled": true,
        "llm": {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "temperature": 0.7
        },
        "worldInfo": [
            // 这个模块只应该知道城市和魔法的信息
            "City-Details.json",
            "Magic-System.json"
        ],
        "promptSlots": [
            {
                "id": "task",
                "role": "system",
                "enabled": true,
                "content": `
你是一个场景导演。你的任务是为一个奇幻故事写一个简短而富有氛围的开头段落。
用户将提供一个简单的起始提示。使用提供的相关背景知识来丰富场景。

# 相关背景知识
{{module.worldInfo}}
`
            },
            {
                "id": "user_input_for_scene",
                "role": "user",
                "enabled": true,
                "content": "故事开始于埃塞尔堡城，有人即将施展一个法术。"
            }
        ]
    },
    {
        "id": "character_action_generator",
        "name": "2. 角色行动生成器",
        "enabled": true,
        "llm": {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "temperature": 0.85
        },
        "worldInfo": [
            // 这个模块只应该知道角色背景和魔法系统
            "Character-Backstory.json",
            "Magic-System.json"
        ],
        "promptSlots": [
            {
                "id": "task",
                "role": "system",
                "enabled": true,
                "content": `
你是一个角色行动生成器。基于已确立的场景，描述主角的行动和想法。
使用相关的角色和魔法知识。不要重复场景描述。

# 相关背景知识
{{module.worldInfo}}
`
            },
            {
                "id": "scene_context",
                "role": "user",
                "enabled": true,
                "content": `
这是当前场景：
{{outputs.scene_setter}}

现在，描述名叫索恩的盗贼在做什么。他正在准备施展一个法术。
`
            }
        ]
    },
    {
        "id": "final_formatter", // This is our final output module
        "name": "3. 最终故事整合器",
        "enabled": true,
        "llm": {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "temperature": 0.5
        },
        "worldInfo": [
            // 这个模块不加载任何世界书，以证明模块可以独立运作
        ],
        "promptSlots": [
            {
                "id": "task",
                "role": "system",
                "enabled": true,
                "content": "你是一个故事编辑。将场景和角色的行动合并成一个连贯的叙述段落。使其流畅自然。"
            },
            {
                "id": "full_context",
                "role": "user",
                "enabled": true,
                "content": `
场景描述：
{{outputs.scene_setter}}

角色行动：
{{outputs.character_action_generator}}
`
            }
        ]
    }
];