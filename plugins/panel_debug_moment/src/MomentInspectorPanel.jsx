// plugins/panel_debug_moment/src/MomentInspectorPanel.jsx
import React, { useEffect, useContext, useMemo } from 'react';
import { Box, Typography, Paper, Skeleton } from '@mui/material';
import { LogEntry } from './LogEntry';

export function MomentInspectorPanel({ services }) {
    const hookManager = services?.get('hookManager');
    const SandboxStateContext = services?.get('sandboxStateContext');

    if (!SandboxStateContext) {
        return (
            <Paper variant="outlined" sx={{ p: 2, color: 'error.main', height: '100%' }}>
                <Typography variant="subtitle2">错误</Typography>
                <Typography variant="body2">
                    无法找到核心服务 'sandboxStateContext'。请确保 'core_runner_ui' 插件已正确加载。
                </Typography>
            </Paper>
        );
    }
    
    const { moment, isLoading, refreshState } = useContext(SandboxStateContext);

    useEffect(() => {
        if (!hookManager) return;
        
        const handleRefresh = () => {
            if (refreshState) {
                refreshState();
            }
        };

        hookManager.addImplementation('panel_debug_moment.refresh', handleRefresh);

        return () => {
            hookManager.removeImplementation('panel_debug_moment.refresh', handleRefresh);
        };
    }, [hookManager, refreshState]);

    const logEntries = useMemo(() => {
        const logs = moment?._log_info || [];
        if (!Array.isArray(logs)) return [];
        // 反转数组，使最新的日志显示在最上面
        return logs.slice().reverse(); 
    }, [moment]);

    // 渲染面板内容
    const renderContent = () => {
        // [优化] 当加载中且无任何日志时，显示更逼真的骨架屏
        if (isLoading && logEntries.length === 0) {
            return Array.from(new Array(8)).map((_, index) => (
                <Box key={index} sx={{ p: '12px 16px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
                        <Skeleton variant="circular" width={20} height={20} />
                        <Skeleton variant="text" width="25%" />
                        <Skeleton variant="rectangular" width="80px" height="20px" sx={{ borderRadius: '16px' }} />
                        <Skeleton variant="text" width="15%" sx={{ ml: 'auto' }} />
                    </Box>
                    <Skeleton variant="text" width="70%" sx={{ ml: '28px' }} />
                </Box>
            ));
        }

        if (!isLoading && logEntries.length === 0) {
            return <Typography color="text.secondary" sx={{p: 2, pt: 3}}>此会话暂无日志。</Typography>;
        }

        return logEntries.map((entry, index) => (
            <LogEntry key={`${entry.timestamp}-${index}`} item={entry} />
        ));
    };

    return (
        <Paper 
            sx={{ 
                height: '100%', 
                width: '100%', 
                display: 'flex', 
                flexDirection: 'column', 
                overflow: 'hidden',
                // [样式] "玻璃拟态" 效果，提供现代感
                backgroundColor: 'rgba(40, 40, 40, 0.35)',
                backdropFilter: 'blur(15px) saturate(200%)',
                WebkitBackdropFilter: 'blur(15px) saturate(200%)',
                borderRadius: '16px',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
                position: 'relative',
                willChange: 'transform',
            }}
        >
            {/* 拖拽句柄，用于移动面板 */}
            <Box
                className="drag-handle"
                sx={{
                    height: '30px',
                    width: '100%',
                    cursor: 'move',
                    flexShrink: 0,
                    position: 'relative',
                    zIndex: 2,
                }}
            />
            
            <Box sx={{ 
                flexGrow: 1, 
                overflow: 'auto',
                // [样式] 顶部的渐变遮罩，营造内容从下方滚动出来的感觉
                maskImage: 'linear-gradient(to bottom, transparent 0%, black 40px)',
                WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 40px)',
                // 向上移动内容以覆盖拖拽区下方，实现无缝滚动
                marginTop: '-30px',
                paddingTop: '30px', // 增加内边距，确保第一条日志不会被拖拽区遮挡
            }}>
                {renderContent()}
            </Box>
        </Paper>
    );
}

export default MomentInspectorPanel;