// plugins/core_goliath/src/views/SandboxBuildView.jsx

import React, { useState, useEffect, useCallback } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import { useSandbox } from '../context/SandboxContext';

import ScopeSelector from '../components/editor/ScopeSelector';
import SchemaFormEditor from '../components/editor/SchemaFormEditor'; // 使用新的 Schema 编辑器
import HistoryTimeline from '../components/editor/HistoryTimeline';

// 导入主 Schema 文件
import loreSchema from '../schemas/lore.schema.json';

// 为其他作用域提供临时的占位符 Schema。
// 在实际应用中，它们也应该有自己完整的 Schema 定义。
const definitionSchema = { 
    title: "Sandbox Blueprint (Definition)", 
    description: "The initial template for this sandbox. Changes here affect new games started from a reset.",
    type: "object", 
    properties: {} 
};
const momentSchema = { 
    title: "Snapshot State (Moment)", 
    description: "The volatile state of the world at a specific point in time. Any change here creates a new history branch.",
    type: "object", 
    properties: {} 
};

// 将作用域名称映射到其对应的 Schema
const scopeToSchemaMap = {
    lore: loreSchema,
    definition: definitionSchema,
    moment: momentSchema,
};

export default function SandboxBuildView() {
    const { selectedSandbox } = useSandbox();

    // 'definition', 'lore', or 'moment'
    const [activeScope, setActiveScope] = useState('lore');
    
    // 仅在 activeScope === 'moment' 时使用
    const [selectedSnapshotId, setSelectedSnapshotId] = useState(null);
    const [history, setHistory] = useState([]);

    // 存储从 API 获取的、要传递给表单的数据
    const [formData, setFormData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // 当作用域或选中的沙盒/快照变化时，获取JSON数据
    const fetchData = useCallback(async () => {
        if (!selectedSandbox) return;

        setLoading(true);
        setError('');
        setFormData(null);
        
        let url = `/api/sandboxes/${selectedSandbox.id}/`;

        if (activeScope === 'moment') {
            try {
                const historyRes = await fetch(`/api/sandboxes/${selectedSandbox.id}/history`);
                if (!historyRes.ok) throw new Error('Failed to fetch history');
                const historyData = await historyRes.json();
                setHistory(historyData);
                
                // 默认选中最新的快照 (HEAD)
                const lastSnapshot = historyData.length > 0 ? historyData[historyData.length - 1] : null;
                const targetSnapshotId = selectedSnapshotId || lastSnapshot?.id;

                // 如果是首次加载 moment，自动选中 HEAD
                if (targetSnapshotId && !selectedSnapshotId) {
                    setSelectedSnapshotId(targetSnapshotId);
                }

                // 从历史记录中找到目标快照，并提取其 moment 数据
                const targetSnapshot = historyData.find(s => s.id === targetSnapshotId);
                setFormData(targetSnapshot?.moment || {});

            } catch (e) {
                setError(e.message);
                setHistory([]);
            }
        } else {
            // 对于 definition 和 lore，直接获取其内容
            url += activeScope;
            try {
                const res = await fetch(url);
                if (!res.ok) throw new Error(`Failed to fetch ${activeScope}`);
                const data = await res.json();
                setFormData(data);
            } catch (e) {
                setError(e.message);
            }
        }
        setLoading(false);

    }, [selectedSandbox, activeScope, selectedSnapshotId]);

    // Effect to trigger data fetching
    useEffect(() => {
        // 重置快照选择，当作用域不是 moment 时
        if (activeScope !== 'moment') {
            setSelectedSnapshotId(null);
        }
        fetchData();
    }, [activeScope, selectedSandbox, fetchData]); // 添加 fetchData 依赖

    // 处理表单的保存/应用操作
    const handleSave = async (updatedFormData) => {
        if (!selectedSandbox) return;
        setLoading(true);
        setError('');
        
        try {
            let url = `/api/sandboxes/${selectedSandbox.id}/`;
            
            if (activeScope === 'moment') {
                if(!selectedSnapshotId) {
                    throw new Error("Cannot save: No snapshot selected to base the change on.");
                }
                // 修改 moment 前，必须先将沙盒的 HEAD 指向我们正在编辑的快照的父节点
                // 这是创建新历史分支的前提
                await fetch(`/api/sandboxes/${selectedSandbox.id}/revert`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ snapshot_id: selectedSnapshotId })
                });

                url += 'moment';
            } else {
                url += activeScope;
            }

            // 使用 PUT 方法，它会完全替换目标作用域的内容。
            // 对于大型数据，PATCH 会更高效，但 PUT 实现起来更简单。
            const response = await fetch(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatedFormData),
            });

            if (!response.ok) {
                 const errorData = await response.json().catch(() => ({ detail: `Failed to save ${activeScope}` }));
                 throw new Error(errorData.detail);
            }
            
            // 成功后，重新获取数据以刷新UI并显示最新状态
            await fetchData();

        } catch (e) {
            setError(`Save failed: ${e.message}`);
            setLoading(false);
        }
    };


    if (!selectedSandbox) {
        return (
            <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography>Please select a sandbox from the sidebar to start editing.</Typography>
            </Box>
        );
    }

    const activeSchema = scopeToSchemaMap[activeScope] || {};

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px - 48px)', width: '100%' }}>
            {/* 顶部标题和作用域切换器 */}
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 2, borderBottom: 1, borderColor: 'divider', flexShrink: 0 }}>
                <Typography variant="h6" noWrap>
                    Editor: {selectedSandbox.name}
                </Typography>
                <ScopeSelector activeScope={activeScope} onChange={setActiveScope} />
            </Stack>

            {/* 主内容区 */}
            <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
                
                {/* 左侧 Schema 编辑器 */}
                <Box sx={{ flexGrow: 1, p: 2, overflow: 'auto' }}>
                    {(loading && !formData) && <CircularProgress sx={{ display: 'block', mx: 'auto', mt: 4 }} />}
                    {error && <Typography color="error" sx={{m: 2}}>{error}</Typography>}
                    
                    {formData !== null && (
                         <SchemaFormEditor
                            schema={activeSchema}
                            formData={formData}
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
                            // 简单假设历史记录的最后一项是 HEAD
                            headSnapshotId={history.length > 0 ? history[history.length - 1].id : null}
                        />
                    </Box>
                )}
            </Box>
        </Box>
    );
}