// plugins/core_layout/src/services/LayoutService.js

/**
 * 管理由布局插件定义的“插槽”（可供注入内容的DOM元素）。
 */
export class LayoutService {
    constructor() {
        this.slots = new Map(); // key: 'workbench.sidebar', value: HTMLElement
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
}