// plugins/core_layout/src/Layout.js
export class Layout {
    /**
     * @param {HTMLElement} targetElement - 要挂载布局的 DOM 元素。
     */
    constructor(targetElement) {
        this.target = targetElement;
        this.target.innerHTML = ''; // 清空加载提示
    }

    /**
     * 创建主布局骨架并渲染所有插件贡献的视图。
     */
    async mount() {
        this.createSkeleton();
        const manifests = await this.fetchPluginManifests();
        this.renderContributions(manifests);
    }

    /**
     * 创建布局的 HTML 骨架。
     */
    createSkeleton() {
        const workbench = document.createElement('div');
        workbench.className = 'hevno-workbench';

        workbench.innerHTML = `
            <div class="content-area">
                <div class="sidebar"></div>
                <div class="main-content">
                    <h1>Welcome to Hevno Engine</h1>
                </div>
            </div>
            <div class="statusbar">
                <div class="left-items"></div>
                <div class="right-items"></div>
            </div>
        `;

        this.target.appendChild(workbench);

        // 保存对关键“插槽”的引用
        this.slots = {
            'workbench.sidebar': workbench.querySelector('.sidebar'),
            'workbench.main.view': workbench.querySelector('.main-content'),
            'statusbar.left': workbench.querySelector('.statusbar .left-items'),
            'statusbar.right': workbench.querySelector('.statusbar .right-items'),
        };
    }

    /**
     * 获取所有插件的清单。
     */
    async fetchPluginManifests() {
        try {
            const response = await fetch('/api/plugins/manifest');
            return await response.json();
        } catch (e) {
            console.error("Layout failed to fetch manifests:", e);
            return [];
        }
    }

    /**
     * 遍历清单，将插件贡献的视图渲染到对应的插槽中。
     * @param {Array<object>} manifests - 所有插件的清单数组。
     */
    /**
 * 遍历清单，将插件贡献的视图渲染到对应的插槽中。
 * @param {Array<object>} manifests - 所有插件的清单数组。
 */
renderContributions(manifests) {
    for (const manifest of manifests) {
        const contributions = manifest.frontend?.contributions?.views;
        if (!contributions) continue;

        for (const [slotName, views] of Object.entries(contributions)) {
            const targetSlot = this.slots[slotName];
            if (targetSlot) {
                for (const view of views) {
                    // 【修改】添加健壮性检查
                    const componentName = view.component;

                    if (!componentName || typeof componentName !== 'string' || componentName.indexOf('-') === -1) {
                        console.error(
                            `[Layout] Invalid component name '${componentName}' contributed by plugin '${manifest.id}'. ` +
                            `Custom element names must contain a hyphen ('-'). Skipping.`
                        );
                        continue; // 跳过这个不合法的贡献
                    }
                    
                    try {
                        const componentElement = document.createElement(componentName);
                        
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
                        console.error(`[Layout] Failed to create element '${componentName}' contributed by plugin '${manifest.id}'.`, e);
                    }
                }
            }
        }
    }
}
}