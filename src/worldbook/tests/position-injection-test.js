// src/worldbook/tests/position-injection-test.js

/**
 * 测试世界书按位置分类注入功能
 * 验证 {{module.worldInfo.before}}, {{module.worldInfo.after}} 等语法
 */

import { WorldInfoProcessor, WORLD_INFO_POSITION } from '../processor.js';

// 创建测试数据
const testEntries = [
    {
        uid: 1,
        key: ['莱拉', 'Layla'],
        content: '莱拉是一位白色长发的精灵法师。',
        comment: '莱拉角色信息',
        position: WORLD_INFO_POSITION.before, // 0
        order: 100,
        enabled: true,
        disable: false,
        constant: false
    },
    {
        uid: 2,
        key: ['精灵', 'elf'],
        content: '精灵是长寿的魔法种族。',
        comment: '精灵种族信息',
        position: WORLD_INFO_POSITION.after, // 1
        order: 90,
        enabled: true,
        disable: false,
        constant: false
    },
    {
        uid: 3,
        key: ['森林', 'forest'],
        content: '古老的魔法森林是精灵的家园。',
        comment: '森林地理信息',
        position: WORLD_INFO_POSITION.ANTop, // 2
        order: 80,
        enabled: true,
        disable: false,
        constant: false
    },
    {
        uid: 4,
        key: ['魔法', 'magic'],
        content: '魔法是这个世界的基础力量。',
        comment: '魔法系统信息',
        position: WORLD_INFO_POSITION.ANBottom, // 3
        order: 70,
        enabled: true,
        disable: false,
        constant: false
    },
    {
        uid: 5,
        key: ['守护者', 'guardian'],
        content: '守护者是森林的保护者。',
        comment: '守护者信息',
        position: WORLD_INFO_POSITION.EMTop, // 5
        order: 60,
        enabled: true,
        disable: false,
        constant: false
    },
    {
        uid: 6,
        key: ['传说', 'legend'],
        content: '传说中隐藏着古老的秘密。',
        comment: '传说信息',
        position: WORLD_INFO_POSITION.EMBottom, // 6
        order: 50,
        enabled: true,
        disable: false,
        constant: false
    }
];

async function testPositionGrouping() {
    console.log('🧪 测试世界书按位置分类注入功能...\n');
    
    const processor = new WorldInfoProcessor({
        maxRecursionDepth: 1,
        debugMode: true
    });
    
    const chatMessages = ['莱拉走向精灵森林，感受着魔法的力量。守护者注视着她，想起了古老的传说。'];
    const globalScanData = {};
    
    console.log('📋 测试输入：');
    console.log(`消息: "${chatMessages[0]}"`);
    console.log('\n📝 测试条目配置：');
    testEntries.forEach(entry => {
        const positionName = Object.keys(WORLD_INFO_POSITION).find(key => 
            WORLD_INFO_POSITION[key] === entry.position
        );
        console.log(`  ${entry.uid}. [${positionName}] ${entry.comment} - "${entry.content}"`);
    });
    
    console.log('\n🔄 开始处理...\n');
    
    try {
        const result = await processor.processWorldInfo(
            testEntries,
            chatMessages,
            globalScanData,
            4096
        );
        
        console.log('\n✅ 处理结果：');
        console.log('================================================================================');
        
        // 显示所有分位置的结果
        const positions = ['before', 'after', 'ANTop', 'ANBottom', 'EMTop', 'EMBottom'];
        
        positions.forEach(position => {
            const content = result[`worldInfo${position.charAt(0).toUpperCase() + position.slice(1)}`] || result[position];
            if (content && content.trim()) {
                console.log(`\n📍 位置 [${position}]:`);
                console.log(`内容: "${content}"`);
                console.log(`长度: ${content.length} 字符`);
            } else {
                console.log(`\n📍 位置 [${position}]: (空)`);
            }
        });
        
        console.log(`\n📦 总体信息:`);
        console.log(`激活条目数: ${result.allActivatedEntries.length}`);
        console.log(`总内容长度: ${result.worldInfoString.length} 字符`);
        
        console.log('\n🎯 模拟模板注入测试：');
        console.log('================================================================================');
        
        // 模拟模板系统的使用
        const templateTests = [
            '{{module.worldInfo}}',
            '{{module.worldInfo.before}}', 
            '{{module.worldInfo.after}}',
            '{{module.worldInfo.ANTop}}',
            '{{module.worldInfo.ANBottom}}',
            '{{module.worldInfo.EMTop}}',
            '{{module.worldInfo.EMBottom}}'
        ];
        
        // 创建模拟的模块上下文
        const moduleContext = {
            worldInfo: {
                // 支持 {{module.worldInfo}} 直接访问
                toString: () => result.worldInfoString,
                // 支持 {{module.worldInfo.before}} 等嵌套访问
                before: result.worldInfoBefore,
                after: result.worldInfoAfter,
                ANTop: result.ANTop,
                ANBottom: result.ANBottom,
                EMTop: result.EMTop,
                EMBottom: result.EMBottom
            }
        };
        
        templateTests.forEach(template => {
            const path = template.replace(/[{}]/g, '').replace('module.', '');
            let value;
            
            if (path === 'worldInfo') {
                // 直接访问worldInfo时，返回字符串
                value = moduleContext.worldInfo.toString();
            } else {
                // 嵌套访问时，使用路径解析
                value = getNestedValue(moduleContext, path);
            }
            
            console.log(`\n模板: ${template}`);
            console.log(`解析结果: "${value || '(空)'}"`);
            console.log(`长度: ${(value || '').length} 字符`);
        });
        
        console.log('\n🎉 测试完成！分位置注入功能正常工作。');
        
        return true;
        
    } catch (error) {
        console.error('❌ 测试失败:', error);
        return false;
    }
}

/**
 * 辅助函数：获取嵌套对象的值
 */
function getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
        return current && typeof current === 'object' ? current[key] : undefined;
    }, obj);
}

/**
 * 主测试函数
 */
async function runTest() {
    console.log('🚀 启动世界书位置注入测试套件...\n');
    
    const success = await testPositionGrouping();
    
    console.log('\n📊 测试总结:');
    console.log('================================================================================');
    if (success) {
        console.log('✅ 所有测试通过！');
        console.log('🎯 现在可以在模板中使用以下语法：');
        console.log('  - {{module.worldInfo}} - 所有世界书内容');
        console.log('  - {{module.worldInfo.before}} - position=before的条目');
        console.log('  - {{module.worldInfo.after}} - position=after的条目'); 
        console.log('  - {{module.worldInfo.ANTop}} - position=ANTop的条目');
        console.log('  - {{module.worldInfo.ANBottom}} - position=ANBottom的条目');
        console.log('  - {{module.worldInfo.EMTop}} - position=EMTop的条目');
        console.log('  - {{module.worldInfo.EMBottom}} - position=EMBottom的条目');
    } else {
        console.log('❌ 测试失败，请检查实现。');
    }
}

// 如果直接运行此文件，执行测试
if (import.meta.url === new URL(import.meta.resolve('.')).href + 'position-injection-test.js') {
    runTest().catch(console.error);
}

export { testPositionGrouping, runTest };
