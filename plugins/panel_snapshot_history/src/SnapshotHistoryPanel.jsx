// plugins/panel_snapshot_history/src/SnapshotHistoryPanel.jsx
import React from 'react';
import { Box, Typography, Paper, IconButton, Tooltip, CircularProgress, Skeleton } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { getHistory, getSandboxDetails, revert, deleteSnapshot } from '../../core_runner_ui/src/api';
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
    
    // 确保子节点按创建时间排序
    for (const node of nodeMap.values()) {
        node.children.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }
    roots.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    return roots;
};

export function SnapshotHistoryPanel({ services }) {
    const { currentSandboxId } = useLayout();
    const confirmationService = services?.get('confirmationService');

    const [history, setHistory] = React.useState([]);
    const [headSnapshotId, setHeadSnapshotId] = React.useState(null);
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState('');

    const loadData = React.useCallback(async (showLoadingSpinner = true) => {
        if (!currentSandboxId) return;
        if (showLoadingSpinner) setIsLoading(true);
        setError('');
        try {
            const [historyData, detailsData] = await Promise.all([
                getHistory(currentSandboxId),
                getSandboxDetails(currentSandboxId)
            ]);
            setHistory(historyData);
            setHeadSnapshotId(detailsData.head_snapshot_id);
        } catch (e) {
            setError(`加载失败: ${e.message}`);
        } finally {
            if (showLoadingSpinner) setIsLoading(false);
        }
    }, [currentSandboxId]);

    React.useEffect(() => {
        loadData();
    }, [loadData]);

    const handleRevert = React.useCallback(async (snapshotId) => {
        if (isLoading) return;
        setIsLoading(true);
        try {
            await revert(currentSandboxId, snapshotId);
            await loadData(false); // 重新加载数据以更新UI
        } catch (e) {
            setError(`切换失败: ${e.message}`);
        } finally {
            setIsLoading(false);
        }
    }, [currentSandboxId, isLoading, loadData]);

    const handleDelete = React.useCallback(async (snapshotId) => {
        if (isLoading || !confirmationService) return;

        const confirmed = await confirmationService.confirm({
            title: '删除快照确认',
            message: '确定要永久删除这个快照及其所有子快照吗？此操作不可撤销。',
        });

        if (!confirmed) return;

        setIsLoading(true);
        try {
            await deleteSnapshot(currentSandboxId, snapshotId);
            await loadData(false); // 删除后刷新
        } catch (e) {
            setError(`删除失败: ${e.message}`);
        } finally {
            setIsLoading(false);
        }
    }, [currentSandboxId, isLoading, loadData, confirmationService]);

    const snapshotTree = React.useMemo(() => buildTree(history), [history]);

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
                onRevert={handleRevert}
                onDelete={handleDelete}
                isLast={false} // 根节点没有兄弟
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
                        <IconButton size="small" onClick={() => loadData()} disabled={isLoading}>
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