// plugins/core_layout/src/services/LayoutService.js
export class LayoutService {
    constructor() {
        this.slots = new Map();
        // 已移除: this.panelContainers，因为面板管理现在是 Goliath 的内部职责。
    }

    /**
     * 注册一个由布局定义的插槽（贡献点）。
     * @param {string} slotName - 插槽的唯一名称, e.g., "workbench.main"
     * @param {HTMLElement} element - 对应的 DOM 元素容器
     */
    registerSlot(slotName, element) {
        if (this.slots.has(slotName)) {
            console.warn(`[LayoutService] Slot '${slotName}' is being re-registered.`);
        }
        this.slots.set(slotName, element);
        console.log(`[LayoutService] Slot registered: ${slotName}`);
    }

    /**
     * 获取一个已注册的插槽元素。
     * @param {string} slotName - 要获取的插槽名称
     * @returns {HTMLElement | undefined}
     */
    getSlot(slotName) {
        const slot = this.slots.get(slotName);
        if (!slot) {
            // 这是一个有用的警告，因为这通常意味着插件的 manifest.json 中指定的贡献点不存在
            console.warn(`[LayoutService] Attempted to get unregistered slot: '${slotName}'`);
        }
        return slot;
    }
    
    // 已移除: registerPanelContainer() 和 addPanel() 方法。
    // 这个服务现在只关心由核心布局静态定义的插槽。
}