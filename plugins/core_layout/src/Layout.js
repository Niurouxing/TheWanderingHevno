// plugins/core_layout/src/Layout.js
export class Layout {
    constructor(targetElement, context) {
        this.target = targetElement;
        this.layoutService = context.get('layoutService');
        if (!this.layoutService) {
            throw new Error("[Core Layout] CRITICAL: LayoutService not found!");
        }
        this.target.innerHTML = ''; // 清空 app 容器
    }

    mount() {
        console.log('[Layout] Mounting minimalist skeleton...');

        const rootContainer = document.createElement('div');
        // 这个 ID 很重要，Goliath 插件会用它来应用顶级样式
        rootContainer.id = 'hevno-root-layout'; 
        
        // 创建两个插槽的容器
        const sidebarSlotContainer = document.createElement('div');
        sidebarSlotContainer.id = 'hevno-sidebar-slot';
        
        const mainSlotContainer = document.createElement('div');
        mainSlotContainer.id = 'hevno-main-slot';

        rootContainer.appendChild(sidebarSlotContainer);
        rootContainer.appendChild(mainSlotContainer);
        
        this.target.appendChild(rootContainer);

        // 向 LayoutService 注册插槽
        this.layoutService.registerSlot('workbench.sidebar', sidebarSlotContainer);
        this.layoutService.registerSlot('workbench.main', mainSlotContainer); // 简化插槽名

        console.log('[Layout] Minimalist skeleton mounted and slots registered.');
    }
}