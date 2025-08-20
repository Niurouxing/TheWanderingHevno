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
        return logs.slice().reverse(); 
    }, [moment]);

    const renderContent = () => {
        if (isLoading && logEntries.length === 0) {
            return Array.from(new Array(10)).map((_, index) => (
                <Box key={index} sx={{ p: '12px 16px' }}>
                    <Skeleton variant="text" width="60%" />
                    <Skeleton variant="text" width="80%" />
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
                backgroundColor: 'rgba(40, 40, 40, 0.35)',
                backdropFilter: 'blur(15px) saturate(200%)',
                WebkitBackdropFilter: 'blur(15px) saturate(200%)',
                borderRadius: '16px',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
                position: 'relative',
            }}
        >
            {/* --- [核心修改] 缩小了拖拽区的高度 --- */}
            <Box
                className="drag-handle"
                sx={{
                    height: '30px', // 从 40px 减小到 30px
                    width: '100%',
                    cursor: 'move',
                    flexShrink: 0,
                    position: 'relative',
                    zIndex: 2,
                }}
            />
            
            {/* --- [核心修改] 调整了滚动区和遮罩以实现无缝渐变 --- */}
            <Box sx={{ 
                flexGrow: 1, 
                overflow: 'auto',
                // 调整遮罩，让渐变区域更长，过渡更平滑
                maskImage: 'linear-gradient(to bottom, transparent 0%, black 40px)',
                WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 40px)',
                // 向上移动内容区，使其顶部与拖拽区重合
                marginTop: '-30px', // 匹配新的拖拽区高度
                // 移除顶部内边距，让内容直接滚动到顶端
                paddingTop: 0, 
            }}>
                {renderContent()}
            </Box>
        </Paper>
    );
}

export default MomentInspectorPanel;