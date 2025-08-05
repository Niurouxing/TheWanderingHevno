// plugins/core_layout/src/Layout.js
export class Layout {
    constructor(targetElement, context) {
        this.target = targetElement;
        this.layoutService = context.get('layoutService');
        if (!this.layoutService) {
            throw new Error("[Core Layout] CRITICAL: LayoutService not found!");
        }
        this.target.innerHTML = '';
    }

    mount() {
        console.log('[Layout] Mounting skeleton and registering slots...');
        this.createSkeleton();
        console.log('[Layout] Skeleton mounted and slots registered.');
    }

    createSkeleton() {
        const workbench = document.createElement('div');
        workbench.className = 'hevno-workbench';
        workbench.innerHTML = `
            <div class="main-area">
                <div class="content-area">
                    <div class="sidebar"></div>
                    <div class="main-content">
                        <h1>Welcome to Hevno Engine</h1>
                        <p>Select a Sandbox or create a new one to begin.</p>
                    </div>
                </div>
                <div class="bottom-panel-area"></div>
            </div>
            <div class="statusbar">
                <div class="left-items"></div>
                <div class="right-items"></div>
            </div>
        `;
        this.target.appendChild(workbench);

        // 向 LayoutService 注册所有插槽和可操作的容器
        this.layoutService.registerSlot('workbench.sidebar', workbench.querySelector('.sidebar'));
        this.layoutService.registerSlot('workbench.main.view', workbench.querySelector('.main-content'));
        this.layoutService.registerSlot('statusbar.left', workbench.querySelector('.statusbar .left-items'));
        this.layoutService.registerSlot('statusbar.right', workbench.querySelector('.statusbar .right-items'));
        
        // ++ 注册动态面板的容器
        this.layoutService.registerPanelContainer('bottom', workbench.querySelector('.bottom-panel-area'));
    }
}