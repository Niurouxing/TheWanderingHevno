// plugins/panel_debug_moment/src/MomentInspectorPanel.jsx
import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { useSandboxState } from '../../core_runner_ui/src/context/SandboxStateContext';

export function MomentInspectorPanel() {
    const { moment, isLoading } = useSandboxState();

    // 【新增】现在，面板自己负责渲染自己的“外壳”
    return (
        <Paper 
            variant="outlined" 
            // 【新增】确保面板填满由 react-grid-layout 分配的空间
            sx={{ 
                height: '100%', 
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden' // 防止内容溢出
            }}
        >
            {/* 【新增】面板自己实现拖动手柄 */}
            <Box
                className="drag-handle"
                sx={{
                    p: 1,
                    cursor: 'move',
                    bgcolor: 'rgba(255, 255, 255, 0.08)',
                    borderBottom: 1,
                    borderColor: 'divider',
                    flexShrink: 0
                }}
            >
                <Typography variant="subtitle2" noWrap>状态监视器 (Moment)</Typography>
            </Box>

            {/* 【新增】内容区域现在需要自己处理滚动 */}
            <Box sx={{ flexGrow: 1, overflow: 'auto', p: 1 }}>
                {isLoading && !moment ? (
                    <Typography color="text.secondary">Loading state...</Typography>
                ) : !moment ? (
                    <Typography color="text.secondary">No moment data available.</Typography>
                ) : (
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.8rem' }}>
                        {JSON.stringify(moment, null, 2)}
                    </pre>
                )}
            </Box>
        </Paper>
    );
}

export default MomentInspectorPanel;