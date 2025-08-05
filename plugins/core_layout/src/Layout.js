// plugins/core_layout/src/Layout.js

/**
 * 负责创建应用的主布局骨架，并动态渲染由其他插件贡献的 UI 视图。
 */
export class Layout {
    constructor(targetElement, context) {
        this.target = targetElement;
        this.context = context;
        this.slots = {};
        this.target.innerHTML = '';
    }

    async mount() {
        console.log('[Layout] Mounting skeleton...');
        this.createSkeleton();
        
        console.log('[Layout] Rendering contributions provided by Kernel Registry...');
        await this.renderAllContributions();
        console.log('[Layout] All contributions rendered.');
    }

    /**
     * 创建布局的静态 HTML 骨架，并缓存对关键“插槽”的引用。
     */
    createSkeleton() {
        const workbench = document.createElement('div');
        workbench.className = 'hevno-workbench';

        // 使用模板字符串定义布局结构，清晰易懂
        workbench.innerHTML = `
            <div class="content-area">
                <div class="sidebar"></div>
                <div class="main-content">
                    <h1>Welcome to Hevno Engine</h1>
                    <p>Select a Sandbox or create a new one to begin.</p>
                </div>
            </div>
            <div class="statusbar">
                <div class="left-items"></div>
                <div class="right-items"></div>
            </div>
        `;

        this.target.appendChild(workbench);

        // 保存对关键“插槽”的引用，以便后续注入内容
        this.slots = {
            'workbench.sidebar': workbench.querySelector('.sidebar'),
            'workbench.main.view': workbench.querySelector('.main-content'),
            'statusbar.left': workbench.querySelector('.statusbar .left-items'),
            'statusbar.right': workbench.querySelector('.statusbar .right-items'),
        };
    }

    async renderAllContributions() {
        const renderTasks = [];
        
        for (const slotName in this.slots) {
            const targetSlot = this.slots[slotName];
            // 【修改】从 context (ServiceContainer) 中获取 registry
            const contributionRegistry = this.context.get('contributionRegistry');
            const viewsToRender = contributionRegistry.getViews(slotName);

            for (const view of viewsToRender) {
                const task = async () => {
                    try {
                        await customElements.whenDefined(view.component);
                        const componentElement = document.createElement(view.component);
                        
                        // 【修改】将整个 context 传递给组件，让组件自己去取所需的服务
                        if (this.context) {
                            componentElement.context = this.context;
                        }
                        
                        // 【关键修改】移除所有 if/else 和包装逻辑。
                        // 布局插件的职责就是找到插槽，然后把组件放进去。
                        targetSlot.appendChild(componentElement);

                    } catch (e) {
                        console.error(`[Layout] Failed to create or mount element '${view.component}' from plugin '${view.pluginId}'.`, e);
                    }
                };
                renderTasks.push(task());
            }
        }
        
        await Promise.all(renderTasks);
    }
}