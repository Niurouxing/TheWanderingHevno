// plugins/panel_snapshot_history/src/SnapshotHistoryPanel.jsx
import React, { useMemo, useContext } from 'react';
import { Box, Typography, Paper, IconButton, Tooltip, CircularProgress, Skeleton } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { SnapshotNode } from './SnapshotNode';
// [移除] 不再需要下面这行硬编码的 import
// import { SandboxStateContext } from '../../core_runner_ui/src/context/SandboxStateContext';

// buildTree 辅助函数保持不变
const buildTree = (snapshots) => {
    if (!snapshots || snapshots.length === 0) return [];
    const nodeMap = new Map(snapshots.map(s => [s.id, { ...s, children: [] }]));
    const roots = [];
    for (const node of nodeMap.values()) {
        if (node.parent_snapshot_id && nodeMap.has(node.parent_snapshot_id)) {
            nodeMap.get(node.parent_snapshot_id).children.push(node);
        } else {
            roots.push(node);
        }
    }
    for (const node of nodeMap.values()) {
        node.children.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }
    roots.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    return roots;
};

export function SnapshotHistoryPanel({ services }) {
    const confirmationService = services?.get('confirmationService');

    // --- 核心修改：采用与 panel_debug_moment 相同的依赖获取方式 ---
    // 1. 从服务容器中按名称查找 Context 对象
    const SandboxStateContext = services?.get('sandboxStateContext');

    // 2. 如果核心依赖不存在，则优雅地失败，提供明确的错误信息
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
    
    // 3. 使用动态获取到的 Context
    const { 
        history, 
        headSnapshotId, 
        isLoading, 
        error, 
        refreshState, 
        revertSnapshot,
        deleteSnapshotFromHistory 
    } = useContext(SandboxStateContext);

    const handleDelete = React.useCallback(async (snapshotId) => {
        if (isLoading || !confirmationService) return;
        const confirmed = await confirmationService.confirm({
            title: '删除快照确认',
            message: '确定要永久删除这个快照及其所有子快照吗？此操作不可撤销。',
        });
        if (confirmed) {
            await deleteSnapshotFromHistory(snapshotId);
        }
    }, [isLoading, confirmationService, deleteSnapshotFromHistory]);

    const snapshotTree = useMemo(() => buildTree(history), [history]);

    // ... 剩余的渲染逻辑完全不变 ...
    const renderContent = () => {
        if (isLoading && history.length === 0) {
            return (
                <Box sx={{ p: 2 }}>
                    <Skeleton variant="text" width="80%" />
                    <Skeleton variant="text" width="60%" sx={{ ml: 2 }} />
                    <Skeleton variant="text" width="60%" sx={{ ml: 2 }} />
                    <Skeleton variant="text" width="80%" />
                </Box>
            );
        }
        if (error) {
            return <Typography color="error.main" sx={{ p: 2 }}>{error}</Typography>;
        }
        if (snapshotTree.length === 0) {
            return <Typography color="text.secondary" sx={{ p: 2 }}>没有可用的快照历史。</Typography>;
        }
        return snapshotTree.map(rootNode => (
            <SnapshotNode 
                key={rootNode.id} 
                node={rootNode} 
                headSnapshotId={headSnapshotId}
                onRevert={revertSnapshot}
                onDelete={handleDelete}
                isLast={false}
            />
        ));
    };

    return (
        <Paper 
            variant="outlined" 
            sx={{ 
                height: '100%', 
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                bgcolor: 'rgba(30, 30, 30, 0.7)',
                backdropFilter: 'blur(10px)',
            }}
        >
            <Box
                className="drag-handle"
                sx={{
                    p: 1, pl: 2,
                    cursor: 'move',
                    bgcolor: 'rgba(255, 255, 255, 0.08)',
                    borderBottom: 1,
                    borderColor: 'divider',
                    flexShrink: 0,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}
            >
                <Typography variant="subtitle2" noWrap>快照历史</Typography>
                <Tooltip title="刷新">
                    <span>
                        <IconButton size="small" onClick={() => refreshState()} disabled={isLoading}>
                            {isLoading ? <CircularProgress size={16} color="inherit" /> : <RefreshIcon sx={{ fontSize: 16 }} />}
                        </IconButton>
                    </span>
                </Tooltip>
            </Box>
            <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
                {renderContent()}
            </Box>
        </Paper>
    );
}

export default SnapshotHistoryPanel;