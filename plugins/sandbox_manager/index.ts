import { definePlugin, PluginContext } from '@hevno/frontend-sdk';
import SandboxList from './components/SandboxList';

export default definePlugin({
    onLoad: (context: PluginContext) => {
        // 注册将在侧边栏渲染的组件
        context.registerComponent('SandboxList', SandboxList);
    },
});