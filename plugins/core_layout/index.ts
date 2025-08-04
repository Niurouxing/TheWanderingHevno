import { definePlugin, PluginContext, services } from '@hevno/frontend-sdk';
import WorkbenchLayout from './components/WorkbenchLayout';

/**
 * 定义一个简单的布局服务，允许其他插件以编程方式与布局交互。
 */
class LayoutService {
    public focusPanel(panelId: string) {
        // 这里的实现可以很复杂，例如通过事件总线通知特定面板组件获取焦点
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
     * 它不应该期望其他插件或服务已经存在。
     */
    onLoad: (context: PluginContext) => {
        console.log(`[core-layout] Plugin loaded. Priority: ${context.getManifest().config.priority}.`);
        
        // 注册主布局组件，以便 Workbench App 可以找到并渲染它。
        // 我们约定，Workbench 会寻找名为 "WorkbenchRoot" 的组件来渲染。
        context.registerComponent('WorkbenchRoot', WorkbenchLayout);
    },

    /**
     * 在 onActivate 阶段，所有插件的 onLoad 都已完成。
     * 这是注册需要依赖其他服务的服务的安全时机。
     */
    onActivate: (context: PluginContext) => {
        console.log('[core-layout] Plugin activated.');
        
        // 注册 LayoutService，供其他插件使用。
        const layoutService = new LayoutService();
        services.registry.register('layoutService', layoutService);
    }
});