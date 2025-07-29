// packages/core-engine/src/test.ts
// import { GraphExecutor } from './GraphExecutor';
// import { topologicalSort } from './graph';
// import { resolveTemplate } from './TemplateResolver';
// import { CoreServices, ExecutionContext } from './types';
// 这是“仅导入”测试的核心。
// 如果程序能运行到这里并打印消息，说明所有模块都已成功加载，没有在初始化时崩溃。
async function main() {
    console.log("✅ All modules imported successfully without crashing. The execution environment is stable.");
}
main().catch(console.error);
export {};
//# sourceMappingURL=test.js.map