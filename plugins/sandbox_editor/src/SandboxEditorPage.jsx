import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, Button } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SCOPE_TABS } from './utils/constants';
import { DataTree } from './components/DataTree';
import { CodexEditor } from './editors/CodexEditor';
import { GraphEditor } from './editors/GraphEditor';
import { MemoriaEditor } from './editors/MemoriaEditor';
import { query, mutate } from './utils/api';
import { GenericEditorDialog } from './editors/GenericEditorDialog';
// --- [修改 1/4] 导入新的 AddItemDialog ---
import { AddItemDialog } from './editors/AddItemDialog';
import { isObject } from './utils/constants';

export function SandboxEditorPage({ services }) {
    const { currentSandboxId, setActivePageId, setCurrentSandboxId } = useLayout();
    const [sandboxData, setSandboxData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeScope, setActiveScope] = useState(0);
    const [editingCodex, setEditingCodex] = useState(null);
    const [editingGraph, setEditingGraph] = useState(null);
    const [editingMemoria, setEditingMemoria] = useState(null);
    const [editingGeneric, setEditingGeneric] = useState(null);
    // --- [修改 2/4] 添加管理添加对话框的状态 ---
    const [addItemTarget, setAddItemTarget] = useState(null); // e.g., { path: 'lore.graphs', existingKeys: ['main'] }

    const loadSandboxData = useCallback(async () => {
        
        if (!currentSandboxId) return;
        setLoading(true);
        setError('');
        try {
            const results = await query(currentSandboxId, ['definition', 'lore', 'moment']);
            setSandboxData(results);
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

    const handleGoBackToExplorer = () => {
        
        setCurrentSandboxId(null);
        setActivePageId('sandbox_explorer.main_view');
    };
    
    const handleEdit = (path, value) => {
        
        const editorType = isObject(value) ? value.__hevno_type__ : undefined;
        if (editorType) {
            const pathParts = path.split('/');
            const name = pathParts[pathParts.length - 1];
            if (editorType === 'hevno/codex') setEditingCodex({ name, data: value, basePath: path });
            else if (editorType === 'hevno/graph') setEditingGraph({ name, data: value, basePath: path });
            else if (editorType === 'hevno/memoria') setEditingMemoria({ data: value, path: path });
            else setEditingGeneric({ path, value });
        } else {
            setEditingGeneric({ path, value });
        }
    };
    
    const handleBackToOverview = () => {
        
        setEditingCodex(null);
        setEditingGraph(null);
        setEditingMemoria(null);
        loadSandboxData();
    };

    const handleGenericSave = async (path, newValue) => {
        
        try {
            await mutate(currentSandboxId, [{ type: 'UPSERT', path, value: newValue }]);
            setEditingGeneric(null);
            await loadSandboxData();
        } catch (err) {
            console.error(`Failed to save value for path "${path}":`, err);
            throw err;
        }
    };

    // --- [修改 3/4] 添加处理添加请求的函数 ---
    const handleOpenAddDialog = (path, existingKeys) => {
        setAddItemTarget({ path, existingKeys });
    };

    const handleAddItem = async (parentPath, key, value) => {
        const fullPath = `${parentPath}/${key}`;
        try {
            await mutate(currentSandboxId, [{ type: 'UPSERT', path: fullPath, value }]);
            setAddItemTarget(null); // 关闭对话框
            await loadSandboxData(); // 重新加载数据
        } catch (err) {
            console.error(`Failed to add item at path "${fullPath}":`, err);
            throw err; // 将错误传递回对话框以显示
        }
    };

    // ... (加载和错误状态的渲染保持不变) ...
    if (!currentSandboxId) return <Box sx={{ p: 4, textAlign: 'center' }}><Typography variant="h6" color="error">未选择要编辑的沙盒</Typography></Box>;
    if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>;
    if (error) return <Box sx={{ p: 4, textAlign: 'center' }}><Typography variant="h6" color="error">加载沙盒失败</Typography><Typography color="text.secondary">{error}</Typography><Button variant="outlined" sx={{ mt: 2 }} onClick={loadSandboxData}>重试</Button></Box>;

    const currentScopeData = sandboxData[SCOPE_TABS[activeScope]];

    if (editingCodex) return <CodexEditor sandboxId={currentSandboxId} basePath={editingCodex.basePath} codexName={editingCodex.name} codexData={editingCodex.data} onBack={handleBackToOverview} />;
    if (editingGraph) return <GraphEditor sandboxId={currentSandboxId} basePath={editingGraph.basePath} graphName={editingGraph.name} graphData={editingGraph.data} onBack={handleBackToOverview} />;
    if (editingMemoria) return <MemoriaEditor sandboxId={currentSandboxId} basePath={editingMemoria.path} memoriaData={editingMemoria.data} onBack={handleBackToOverview} />;

    const sandboxName = (sandboxData.definition?.name || sandboxData.lore?.name || 'Sandbox');

    return (
        <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, flexShrink: 0 }}>
                {/* ... (头部UI保持不变) ... */}
                <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={handleGoBackToExplorer} sx={{ mr: 2 }}>
                    返回沙盒列表
                </Button>
                <Typography variant="h4" component="h1" noWrap sx={{ flexGrow: 1 }}>
                    正在编辑: {sandboxName}
                </Typography>
            </Box>

            <Tabs value={activeScope} onChange={handleScopeChange} aria-label="sandbox scopes" sx={{ flexShrink: 0, borderBottom: 1, borderColor: 'divider' }}>
                {SCOPE_TABS.map((scope, index) => (
                    <Tab label={scope.charAt(0).toUpperCase() + scope.slice(1)} key={index} />
                ))}
            </Tabs>
            <Box sx={{ mt: 2, flexGrow: 1, overflowY: 'auto' }}>
                {currentScopeData ? (
                    // --- [修改 4/4] 将 onAdd 处理器传递给 DataTree ---
                    <DataTree data={currentScopeData} path={SCOPE_TABS[activeScope]} onEdit={handleEdit} onAdd={handleOpenAddDialog} />
                ) : (
                    <Typography color="text.secondary">该范围内没有可用数据</Typography>
                )}
            </Box>

            <GenericEditorDialog open={!!editingGeneric} onClose={() => setEditingGeneric(null)} onSave={handleGenericSave} item={editingGeneric} />
            
            <AddItemDialog
                open={!!addItemTarget}
                onClose={() => setAddItemTarget(null)}
                onAdd={handleAddItem}
                parentPath={addItemTarget?.path}
                existingKeys={addItemTarget?.existingKeys}
            />
        </Box>
    );
}

export default SandboxEditorPage;