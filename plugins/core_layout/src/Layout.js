// plugins/core_layout/src/Layout.js
export class Layout {
    constructor(targetElement, context) {
        this.target = targetElement;
        this.layoutService = context.get('layoutService');
        if (!this.layoutService) {
            throw new Error("[Core Layout] CRITICAL: LayoutService not found!");
        }
        this.target.innerHTML = ''; // 清空 #app 容器
    }

    mount() {
        console.log('[Layout] Mounting minimalist root host...');

        const rootContainer = document.createElement('div');
        rootContainer.id = 'hevno-root-layout';
        rootContainer.style.width = '100%';
        rootContainer.style.height = '100%';
        
        // 关键变更: 不再创建侧边栏等具体布局元素。
        // 只创建一个单一的主工作区挂载点，让 Goliath 插件完全控制其内部布局。
        const mainWorkbenchSlot = document.createElement('div');
        mainWorkbenchSlot.id = 'hevno-workbench-slot';
        mainWorkbenchSlot.style.width = '100%';
        mainWorkbenchSlot.style.height = '100%';

        rootContainer.appendChild(mainWorkbenchSlot);
        this.target.appendChild(rootContainer);

        // 关键变更: 只向 LayoutService 注册一个插槽。
        // 这是 Goliath 插件将其 UI 贡献到的目标 "贡献点"。
        this.layoutService.registerSlot('workbench.main', mainWorkbenchSlot);

        console.log('[Layout] Minimalist host mounted. Single slot "workbench.main" is ready.');
    }
}