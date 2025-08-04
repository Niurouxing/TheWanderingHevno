import { definePlugin, PluginContext, services } from '@hevno/frontend-sdk';
import WorkbenchLayout from './components/WorkbenchLayout';

/**
 * 定义一个简单的布局服务，允许其他插件以编程方式与布局交互。
 */
class LayoutService {
    public focusPanel(panelId: string) {
        services.bus.emit(`layout:focus-panel`, { panelId });
        console.log(`[core-layout] Focusing panel: ${panelId}`);
    }

    public toggleSidebar() {
        services.bus.emit('layout:toggle-sidebar');
        console.log('[core-layout] Toggling sidebar visibility');
    }
}

export default definePlugin({
    /**
     * 在 onLoad 阶段，插件应该只做最基本的事情：注册自己。
     */
    onLoad: (context: PluginContext) => {
        const priority = context.getManifest().frontend?.priority;
        console.log(`[core-layout] Plugin loaded. Priority: ${priority}.`);
        
        // 注册主布局组件
        context.registerComponent('WorkbenchRoot', WorkbenchLayout);
    },

    /**
     * 在 onActivate 阶段，所有插件的 onLoad 都已完成。
     */
    onActivate: (context: PluginContext) => {
        console.log('[core-layout] Plugin activated.');
        
        const layoutService = new LayoutService();
        services.registry.register('layoutService', layoutService);
    }
});