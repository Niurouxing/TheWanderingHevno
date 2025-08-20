// plugins/panel_snapshot_history/src/SnapshotHistoryPanel.jsx
import React, { useMemo, useContext } from 'react'; // 引入 useContext 和 useMemo
import { Box, Typography, Paper, IconButton, Tooltip, CircularProgress, Skeleton } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
// 直接从 core_runner_ui 导入 context，因为它是核心服务
import { SandboxStateContext } from '../../core_runner_ui/src/context/SandboxStateContext';
import { SnapshotNode } from './SnapshotNode';

// 一个辅助函数，用于从扁平数组构建树状结构
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

    // [核心修改] 从 context 获取所有状态和方法，移除本地 state
    const context = useContext(SandboxStateContext);
    if (!context) {
        return <Paper variant="outlined" sx={{p: 2, color: 'error.main'}}>错误: SandboxStateContext 未找到。</Paper>
    }
    
    const { 
        history, 
        headSnapshotId, 
        isLoading, 
        error, 
        refreshState, 
        revertSnapshot,
        deleteSnapshotFromHistory 
    } = context;

    // [核心修改] 将删除操作封装，并集成确认对话框
    const handleDelete = React.useCallback(async (snapshotId) => {
        if (isLoading || !confirmationService) return;

        const confirmed = await confirmationService.confirm({
            title: '删除快照确认',
            message: '确定要永久删除这个快照及其所有子快照吗？此操作不可撤销。',
        });

        if (confirmed) {
            // 调用 context 提供的方法
            await deleteSnapshotFromHistory(snapshotId);
        }
    }, [isLoading, confirmationService, deleteSnapshotFromHistory]);

    // 使用 useMemo 避免在每次渲染时都重新计算树结构
    const snapshotTree = useMemo(() => buildTree(history), [history]);

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
                // [核心修改] 直接传递 context 的方法
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
                        {/* [核心修改] 刷新按钮调用 context 的 refreshState */}
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