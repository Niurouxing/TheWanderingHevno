import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, Button } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SCOPE_TABS } from './utils/constants';
import { DataTree } from './components/DataTree';
import { CodexEditor } from './editors/CodexEditor';
import { GraphEditor } from './editors/GraphEditor';
import { MemoriaEditor } from './editors/MemoriaEditor';

export function SandboxEditorPage({ services }) {
    // --- [修改 1/4] 从 LayoutContext 中获取 setActivePageId 和 setCurrentSandboxId ---
    const { currentSandboxId, setActivePageId, setCurrentSandboxId } = useLayout();
    const [sandboxData, setSandboxData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeScope, setActiveScope] = useState(0);
    const [editingCodex, setEditingCodex] = useState(null);
    const [editingGraph, setEditingGraph] = useState(null); 
    const [editingMemoria, setEditingMemoria] = useState(null);

    const loadSandboxData = useCallback(async () => {
        if (!currentSandboxId) return;
        setLoading(true);
        setError('');
        try {
            const [definitionRes, loreRes, momentRes] = await Promise.all([
                fetch(`/api/sandboxes/${currentSandboxId}/definition`),
                fetch(`/api/sandboxes/${currentSandboxId}/lore`),
                fetch(`/api/sandboxes/${currentSandboxId}/moment`)
            ]);
            if (!definitionRes.ok || !loreRes.ok || !momentRes.ok) throw new Error('Failed to fetch sandbox scopes');
            const definition = await definitionRes.json();
            const lore = await loreRes.json();
            const moment = await momentRes.json();
            setSandboxData({ definition, lore, moment });
        } catch (e) {
            setError(e.message);
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [currentSandboxId]);

    useEffect(() => {
        if (currentSandboxId) {
            loadSandboxData();
        }
    }, [currentSandboxId, loadSandboxData]);

    const handleScopeChange = (event, newValue) => {
        setActiveScope(newValue);
        setEditingCodex(null);
        setEditingGraph(null);
    };

    // --- [新增 2/4] 添加返回按钮的点击处理函数 ---
    const handleGoBackToExplorer = () => {
        setCurrentSandboxId(null); // 清理上下文
        setActivePageId('sandbox_explorer.main_view'); // 切换页面
    };

    const handleEdit = (path, value, codexName, activeScopeIndex) => {
        if (value.__hevno_type__ === 'hevno/codex' && value.entries && Array.isArray(value.entries)) {
            // 原有 codex 逻辑
            let effectiveScope = SCOPE_TABS[activeScopeIndex];
            if (activeScopeIndex === 0) {
                const parts = path.split('.');
                if (parts[0] === 'initial_lore') effectiveScope = 'initial_lore';
                else if (parts[0] === 'initial_moment') effectiveScope = 'initial_moment';
            }
            setEditingCodex({ name: codexName || path.split('.').pop(), data: value, scope: effectiveScope });
        } else if (value.__hevno_type__ === 'hevno/graph') {
            // 新增: graph 编辑
            let effectiveScope = SCOPE_TABS[activeScopeIndex];
            // 类似 scope 处理
            if (activeScopeIndex === 0) {
                const parts = path.split('.');
                if (parts[0] === 'initial_lore') effectiveScope = 'initial_lore';
                else if (parts[0] === 'initial_moment') effectiveScope = 'initial_moment';
            }
            setEditingGraph({ name: codexName || path.split('.').pop(), data: value, scope: effectiveScope });
        } else if (value.__hevno_type__ === 'hevno/memoria') {
            // New: memoria editing
            setEditingMemoria({ data: value, scope: 'moment' }); // Memoria is always in moment
        } else {
            alert(`Edit functionality for "${path}" is not yet implemented.`);
        }
    };

    const handleBackFromCodex = () => {
        setEditingCodex(null);
        loadSandboxData();
    };

    if (!currentSandboxId) {
        return (
            <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="h6" color="error">未选择要编辑的沙盒</Typography>
            </Box>
        );
    }
    if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>;
    if (error) return (
        <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="error">加载沙盒失败</Typography>
            <Typography color="text.secondary">{error}</Typography>
            <Button variant="outlined" sx={{ mt: 2 }} onClick={loadSandboxData}>重试</Button>
        </Box>
    );

    const currentScopeData = sandboxData[SCOPE_TABS[activeScope]];

    if (editingCodex) {
        return (
            <CodexEditor
                sandboxId={currentSandboxId}
                scope={editingCodex.scope}
                codexName={editingCodex.name}
                codexData={editingCodex.data}
                onBack={handleBackFromCodex}
            />
        );
    } else if (editingGraph) {
        return (
            <GraphEditor
                sandboxId={currentSandboxId}
                scope={editingGraph.scope}
                graphName={editingGraph.name}
                graphData={editingGraph.data}
                onBack={() => { setEditingGraph(null); loadSandboxData(); }}
            />
        );
    } else if (editingMemoria) {
  return (
    <MemoriaEditor
      sandboxId={currentSandboxId}
      scope={editingMemoria.scope}
      memoriaData={editingMemoria.data}
      onBack={() => { setEditingMemoria(null); loadSandboxData(); }}
    />
  );
}

    return (
        <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* --- [修改 3/4] 重新组织标题区域，添加返回按钮 --- */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, flexShrink: 0 }}>
                <Button
                    variant="outlined"
                    startIcon={<ArrowBackIcon />}
                    onClick={handleGoBackToExplorer}
                    sx={{ mr: 2 }}
                >
                    返回沙盒列表
                </Button>
                <Typography variant="h4" component="h1" noWrap sx={{ flexGrow: 1 }}>
                    正在编辑: {sandboxData?.name || 'Sandbox'}
                </Typography>
            </Box>

            {/* --- [修改 4/4] 调整布局，使内容区可滚动 --- */}
            <Tabs value={activeScope} onChange={handleScopeChange} aria-label="sandbox scopes" sx={{ flexShrink: 0, borderBottom: 1, borderColor: 'divider' }}>
                {SCOPE_TABS.map((scope, index) => (
                    <Tab label={scope.charAt(0).toUpperCase() + scope.slice(1)} key={index} />
                ))}
            </Tabs>
            <Box sx={{ mt: 2, flexGrow: 1, overflowY: 'auto' }}>
                {currentScopeData ? (
                    <DataTree data={currentScopeData} onEdit={(path, value, codexName) => handleEdit(path, value, codexName, activeScope)} activeScope={activeScope} />
                ) : (
                    <Typography color="text.secondary">该范围内没有可用数据</Typography>
                )}
            </Box>
        </Box>
    );
}

export default SandboxEditorPage;