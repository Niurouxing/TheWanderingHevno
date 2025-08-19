// plugins/panel_debug_moment/src/MomentInspectorPanel.jsx
import React, { useEffect, useContext } from 'react'; // [修改] 导入 useContext
import { Box, Typography, Paper } from '@mui/material';


export function MomentInspectorPanel({ services }) {
    // 1. 从 services 容器中按名称查找依赖项
    const hookManager = services?.get('hookManager');
    const SandboxStateContext = services?.get('sandboxStateContext');

    // 2. 如果核心依赖项不存在，则优雅地失败
    if (!SandboxStateContext) {
        return (
            <Paper variant="outlined" sx={{ p: 2, color: 'error.main' }}>
                错误：无法找到 'sandboxStateContext'。此面板是否在正确的宿主中运行？
            </Paper>
        );
    }

    // 3. 使用查找到的 Context
    const { moment, isLoading, refreshState } = useContext(SandboxStateContext);

    useEffect(() => {
        if (!hookManager) return;
        
        const handleRefresh = () => {
            console.log('[panel_debug_moment] Received refresh event via hook.');
            // refreshState 可能为 null，需要检查
            if (refreshState) {
                refreshState();
            }
        };

        hookManager.addImplementation('panel_debug_moment.refresh', handleRefresh);

        return () => {
            hookManager.removeImplementation('panel_debug_moment.refresh', handleRefresh);
        };
    }, [hookManager, refreshState]);

    // --- 渲染逻辑保持不变 ---
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