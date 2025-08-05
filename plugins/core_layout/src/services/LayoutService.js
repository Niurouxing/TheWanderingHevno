// plugins/core_layout/src/services/LayoutService.js
export class LayoutService {
    constructor() {
        this.slots = new Map();
        this.panelContainers = new Map(); // ++ 新增：存储面板容器
    }

    registerSlot(slotName, element) {
        if (this.slots.has(slotName)) {
            console.warn(`[LayoutService] Slot '${slotName}' is being re-registered.`);
        }
        this.slots.set(slotName, element);
        console.log(`[LayoutService] Slot registered: ${slotName}`);
    }

    getSlot(slotName) {
        const slot = this.slots.get(slotName);
        if (!slot) {
            console.warn(`[LayoutService] Attempted to get unregistered slot: '${slotName}'`);
        }
        return slot;
    }
    
    // ++ 新增：由 Layout.js 调用，注册可用于添加面板的区域
    registerPanelContainer(position, element) {
        this.panelContainers.set(position, element);
    }
    
    // ++ 新增核心 API：动态添加一个面板
    /**
     * 向主布局添加一个可容纳视图的面板。
     * @param {string} position - 面板的位置, e.g., "bottom"
     * @param {object} options - 面板的配置
     * @param {string} options.id - 面板的唯一ID
     * @param {string} options.title - 面板的标题
     * @returns {HTMLElement | null} 返回为该面板内容创建的插槽元素
     */
    addPanel(position, options) {
        const container = this.panelContainers.get(position);
        if (!container) {
            console.error(`[LayoutService] No panel container found for position: '${position}'`);
            return null;
        }

        // 简化的实现：只允许一个底部面板。一个完整的实现会有标签页系统。
        container.innerHTML = ''; // 清空现有内容

        const panelContentSlot = document.createElement('div');
        // 为这个新面板创建一个新的、动态的贡献点（插槽）
        const slotId = `workbench.panel.${options.id}`;
        this.registerSlot(slotId, panelContentSlot);

        // 这里可以创建更复杂的面板结构，比如带标题栏和关闭按钮
        container.appendChild(panelContentSlot);
        container.classList.add('visible'); // 使其可见

        console.log(`[LayoutService] Panel '${options.id}' added to '${position}'. New slot created: '${slotId}'`);
        
        return panelContentSlot;
    }
}