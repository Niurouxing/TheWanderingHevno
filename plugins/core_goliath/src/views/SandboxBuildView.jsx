// plugins/core_goliath/src/views/SandboxBuildView.jsx

import React, { useState, useEffect, useCallback } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import { useSandbox } from '../context/SandboxContext';

import ScopeSelector from '../components/editor/ScopeSelector';
import JsonEditor from '../components/editor/JsonEditor';
import HistoryTimeline from '../components/editor/HistoryTimeline';

export default function SandboxBuildView() {
    const { selectedSandbox } = useSandbox();

    // 'definition', 'lore', or 'moment'
    const [activeScope, setActiveScope] = useState('lore'); 
    
    // 仅在 activeScope === 'moment' 时使用
    const [selectedSnapshotId, setSelectedSnapshotId] = useState(null);
    const [history, setHistory] = useState([]);

    const [jsonData, setJsonData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // 当作用域或选中的沙盒/快照变化时，获取JSON数据
    const fetchData = useCallback(async () => {
        if (!selectedSandbox) return;

        setLoading(true);
        setError('');
        setJsonData(null);
        
        let url = `/api/sandboxes/${selectedSandbox.id}/`;

        if (activeScope === 'moment') {
            // 对于 moment，我们需要先获取历史记录
            // 然后基于选中的快照ID来决定要显示哪个 moment
            try {
                const historyRes = await fetch(`/api/sandboxes/${selectedSandbox.id}/history`);
                if (!historyRes.ok) throw new Error('Failed to fetch history');
                const historyData = await historyRes.json();
                setHistory(historyData);
                
                // 默认选中最新的快照 (HEAD)
                const targetSnapshotId = selectedSnapshotId || historyData[historyData.length - 1]?.id;
                if(targetSnapshotId && !selectedSnapshotId) {
                    setSelectedSnapshotId(targetSnapshotId);
                }

                if (targetSnapshotId) {
                    // moment 数据存储在快照对象中
                    const targetSnapshot = historyData.find(s => s.id === targetSnapshotId);
                    setJsonData(targetSnapshot?.moment || {});
                } else {
                     setJsonData({}); // 没有快照时显示空对象
                }
            } catch (e) {
                setError(e.message);
            }

        } else {
            // 对于 definition 和 lore，直接获取
            url += activeScope;
            try {
                const res = await fetch(url);
                if (!res.ok) throw new Error(`Failed to fetch ${activeScope}`);
                const data = await res.json();
                setJsonData(data);
            } catch (e) {
                setError(e.message);
            }
        }
        setLoading(false);

    }, [selectedSandbox, activeScope, selectedSnapshotId]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // 处理JSON编辑器的保存/应用操作
    const handleSave = async (updatedJsonString) => {
        if (!selectedSandbox) return;
        setLoading(true);
        setError('');
        
        try {
            const data = JSON.parse(updatedJsonString);
            let url = `/api/sandboxes/${selectedSandbox.id}/`;
            let method = 'PATCH';
            
            if (activeScope === 'moment') {
                if(!selectedSnapshotId) {
                    throw new Error("No snapshot selected to apply changes to.");
                }
                // 在修改 moment 之前，需要先 revert 到目标快照
                await fetch(`/api/sandboxes/${selectedSandbox.id}/revert`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ snapshot_id: selectedSnapshotId })
                });

                url += 'moment';
                // JSON-Patch 是一种更优的方式，但为了简单起见，我们先用 PUT 完全替换
                // method = 'PUT';
            } else {
                url += activeScope;
                // method = 'PUT';
            }

            // 这里使用 PATCH / PUT 需要后端支持。为简单起见，我们假设后端支持完全替换
            // 真实场景下，生成 JSON-Patch 会更高效。
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                 const errorData = await response.json().catch(() => ({ detail: `Failed to save ${activeScope}` }));
                 throw new Error(errorData.detail);
            }
            
            // 保存后重新获取数据以同步UI
            fetchData();

        } catch (e) {
            setError(`Save failed: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };


    if (!selectedSandbox) {
        return (
            <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography>Please select a sandbox to start editing.</Typography>
            </Box>
        );
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', width: '100%' }}>
            {/* 顶部标题和作用域切换器 */}
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 2, borderBottom: 1, borderColor: 'divider', flexShrink: 0 }}>
                <Typography variant="h6">
                    Editor: {selectedSandbox.name}
                </Typography>
                <ScopeSelector activeScope={activeScope} onChange={setActiveScope} />
            </Stack>

            {/* 主内容区 */}
            <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
                
                {/* 左侧 JSON 编辑器 */}
                <Box sx={{ flexGrow: 1, p: 2, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
                    {loading && <CircularProgress sx={{ m: 'auto' }} />}
                    {error && <Typography color="error" sx={{ m: 'auto' }}>{error}</Typography>}
                    {jsonData !== null && (
                         <JsonEditor
                            initialJson={jsonData}
                            onSave={handleSave}
                            isMomentScope={activeScope === 'moment'}
                            loading={loading}
                        />
                    )}
                </Box>
                
                {/* 右侧历史时间轴 (条件渲染) */}
                {activeScope === 'moment' && (
                    <Box sx={{ width: 320, borderLeft: 1, borderColor: 'divider', flexShrink: 0, overflow: 'auto' }}>
                        <HistoryTimeline 
                            history={history}
                            selectedSnapshotId={selectedSnapshotId}
                            onSelectSnapshot={setSelectedSnapshotId}
                            headSnapshotId={history[history.length-1]?.id} // 简单假设最后一个是head
                        />
                    </Box>
                )}
            </Box>
        </Box>
    );
}