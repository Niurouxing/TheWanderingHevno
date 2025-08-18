// plugins/panel_debug_moment/src/MomentInspectorPanel.jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
// 注意这个相对路径，在真实项目中可能需要通过构建工具或别名来优化
import { useSandboxState } from '../../core_runner_ui/src/context/SandboxStateContext';

export function MomentInspectorPanel() {
    const { moment, isLoading } = useSandboxState();

    if (isLoading && !moment) {
        return <Typography color="text.secondary">Loading state...</Typography>;
    }
    
    if (!moment) {
        return <Typography color="text.secondary">No moment data available.</Typography>;
    }

    return (
        // 【修改】移除强制设置高度，让组件自然填充父容器空间
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.8rem' }}>
            {JSON.stringify(moment, null, 2)}
        </pre>
    );
}

export default MomentInspectorPanel;