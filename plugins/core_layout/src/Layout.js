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
        
        // 遍历布局定义的所有插槽
        for (const slotName in this.slots) {
            const targetSlot = this.slots[slotName];

            // 从注册表中获取该插槽的、已处理过的视图
            const viewsToRender = this.context.contributionRegistry.getViews(slotName);

            for (const view of viewsToRender) {
                const task = async () => {
                    try {
                        await customElements.whenDefined(view.component);
                        const componentElement = document.createElement(view.component);
                        
                        if (this.context) {
                            componentElement.context = this.context;
                        }
                        
                        if (slotName === 'workbench.sidebar') {
                            const container = document.createElement('div');
                            container.className = 'sidebar-view-container';
                            container.innerHTML = `<h3>${view.title || 'Untitled View'}</h3><div class="component-slot"></div>`;
                            container.querySelector('.component-slot').appendChild(componentElement);
                            targetSlot.appendChild(container);
                        } else {
                            targetSlot.appendChild(componentElement);
                        }
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
