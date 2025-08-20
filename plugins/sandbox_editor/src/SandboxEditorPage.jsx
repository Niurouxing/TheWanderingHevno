// plugins/sandbox_editor/src/SandboxEditorPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, Button, Alert } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PublishedWithChangesIcon from '@mui/icons-material/PublishedWithChanges';
import AddIcon from '@mui/icons-material/Add';
import { SCOPE_TABS } from './utils/constants';
import { DataTree } from './components/DataTree';
import { CodexEditor } from './editors/CodexEditor';
import { GraphEditor } from './editors/GraphEditor';
import { MemoriaEditor } from './editors/MemoriaEditor';
import { query, mutate, applyDefinition } from './utils/api';
import { loadSchemas } from './utils/schemaManager';
import { GenericEditorDialog } from './editors/GenericEditorDialog';
import { AddItemDialog } from './editors/AddItemDialog';
// ---导入新的 Rename 对话框 ---
import { RenameItemDialog } from './components/RenameItemDialog';
import { isObject } from './utils/constants';

export function SandboxEditorPage({ services }) {
    const useLayout = services.get('useLayout');
    if (!useLayout) {
        console.error('[sandbox_editor] useLayout hook not found in services.');
        return <Box sx={{ p: 4, color: 'error.main' }}>错误：核心布局服务不可用。</Box>;
    }
    const { currentSandboxId, setActivePageId, setCurrentSandboxId } = useLayout();
    
    const [sandboxData, setSandboxData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeScope, setActiveScope] = useState(0);
    const [editingCodex, setEditingCodex] = useState(null);
    const [editingGraph, setEditingGraph] = useState(null);
    const [editingMemoria, setEditingMemoria] = useState(null);
    const [editingGeneric, setEditingGeneric] = useState(null);
    const [addItemTarget, setAddItemTarget] = useState(null);
    // ---用于重命名对话框的状态 ---
    const [renameItemTarget, setRenameItemTarget] = useState(null);

    // --- 1. 从 props 获取服务实例 ---
    const confirmationService = services.get('confirmationService');

    const loadSandboxData = useCallback(async () => {
        if (!currentSandboxId) return;
        try {
            const results = await query(currentSandboxId, ['definition', 'lore', 'moment']);
            setSandboxData(results);
        } catch (e) {
            console.error('加载沙盒数据失败:', e);
            throw new Error(`加载沙盒数据失败: ${e.message}`);
        }
    }, [currentSandboxId]);

    const loadAllEditorData = useCallback(async () => {
        if (!currentSandboxId) return;

        setLoading(true);
        setError('');
        
        try {
            console.log("开始并行加载沙盒数据和UI Schemas...");
            await Promise.all([
                loadSandboxData(),
                loadSchemas()
            ]);
            console.log("沙盒数据和UI Schemas均已加载完毕。");
        } catch (e) {
            setError(e.message);
            console.error("加载编辑器所需数据时出错:", e);
        } finally {
            setLoading(false);
        }
    }, [currentSandboxId, loadSandboxData]); 

    useEffect(() => {
        loadAllEditorData();
    }, [loadAllEditorData]);

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

    //一个专门用于在根目录打开添加对话框的处理器
    const handleOpenAddDialogAtRoot = () => {
        const currentScopeName = SCOPE_TABS[activeScope];
        const currentScopeData = sandboxData[currentScopeName];
        if (currentScopeData) {
            const existingKeys = Object.keys(currentScopeData);
            // 调用已有的 handleOpenAddDialog，但路径是根路径
            handleOpenAddDialog(currentScopeName, existingKeys);
        }
    };

    const handleApplyDefinition = async () => {
        // --- 2. 直接调用服务的 confirm 方法 ---
        const confirmed = await confirmationService.confirm({
            title: '应用蓝图确认',
            message: '确定要应用这个蓝图吗？\n\n这将完全覆盖当前的 `lore` 和 `moment` 状态，并用 `definition` 中的初始值替换它们。\n\n当前的所有记忆和演化知识都将丢失，并开启一个全新的历史记录。此操作不可撤销。',
        });

        if (!confirmed) {
            return;
        }

        setLoading(true);
        setError('');
        try {
            await applyDefinition(currentSandboxId);
            await loadSandboxData();
            alert("蓝图已成功应用！");
        } catch (e) {
            setError(`应用蓝图失败: ${e.message}`);
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    // ---处理删除操作的函数 ---
    const handleDeleteItem = async (path) => {
        const itemName = path.split('/').pop();

        // --- 2. 直接调用服务的 confirm 方法 ---
        const confirmed = await confirmationService.confirm({
            title: '删除确认',
            message: `你确定要删除 "${itemName}" 吗？此操作无法撤销。`,
        });

        if (!confirmed) {
            return;
        }

        // --- 3. 执行原有逻辑 ---
        try {
            await mutate(currentSandboxId, [{ type: 'DELETE', path }]);
            await loadSandboxData(); // 成功后刷新数据
        } catch (e) {
            setError(`删除失败: ${e.message}`);
            console.error(`删除路径 "${path}" 失败:`, e);
        }
    };

    // ---打开重命名对话框的函数 ---
    const handleRenameRequest = (path, value, existingKeys) => {
        const oldKey = path.split('/').pop();
        // 过滤掉当前正在重命名的键
        const otherKeys = existingKeys.filter(k => k !== oldKey);
        setRenameItemTarget({ path, value, existingKeys: otherKeys });
    };

    // ---执行重命名操作的函数 ---
    const handleRenameConfirm = async (oldPath, newKey) => {
        const parentPath = oldPath.substring(0, oldPath.lastIndexOf('/'));
        const newPath = `${parentPath}/${newKey}`;
        const itemValue = renameItemTarget.value;

        // 重命名通过 "删除旧的" + "插入新的" 两个操作原子化完成
        await mutate(currentSandboxId, [
            { type: 'DELETE', path: oldPath },
            { type: 'UPSERT', path: newPath, value: itemValue }
        ]);

        // 成功后关闭对话框并刷新数据
        setRenameItemTarget(null);
        await loadSandboxData();
    };


    if (!currentSandboxId) return <Box sx={{ p: 4, textAlign: 'center' }}><Typography variant="h6" color="error">未选择要编辑的沙盒</Typography></Box>;
    if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>;
    if (error) return <Box sx={{ p: 4, textAlign: 'center' }}><Alert severity="error" onClose={() => setError('')}>{error}</Alert><Button variant="outlined" sx={{ mt: 2 }} onClick={loadAllEditorData}>重试</Button></Box>;
    const currentScopeData = sandboxData[SCOPE_TABS[activeScope]];

    if (editingCodex) return <CodexEditor sandboxId={currentSandboxId} basePath={editingCodex.basePath} codexName={editingCodex.name} codexData={editingCodex.data} onBack={handleBackToOverview} confirmationService={confirmationService} />;
    if (editingGraph) return <GraphEditor sandboxId={currentSandboxId} basePath={editingGraph.basePath} graphName={editingGraph.name} graphData={editingGraph.data} onBack={handleBackToOverview} confirmationService={confirmationService} />;
    if (editingMemoria) return <MemoriaEditor sandboxId={currentSandboxId} basePath={editingMemoria.path} memoriaData={editingMemoria.data} onBack={handleBackToOverview} confirmationService={confirmationService} />;

    const sandboxName = (sandboxData.definition?.name || sandboxData.lore?.name || 'Sandbox');

    return (
        <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, flexShrink: 0 }}>
                <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={handleGoBackToExplorer} sx={{ mr: 2 }}>
                    返回沙盒列表
                </Button>
                <Typography variant="h4" component="h1" noWrap sx={{ flexGrow: 1 }}>
                    正在编辑: {sandboxName}
                </Typography>
                {SCOPE_TABS[activeScope] === 'definition' && (
                    <Button 
                        variant="contained" 
                        color="secondary"
                        startIcon={<PublishedWithChangesIcon />} 
                        onClick={handleApplyDefinition}
                        disabled={loading}
                    >
                        应用蓝图
                    </Button>
                )}
            </Box>

            <Tabs value={activeScope} onChange={handleScopeChange} aria-label="sandbox scopes" sx={{ flexShrink: 0, borderBottom: 1, borderColor: 'divider' }}>
                {SCOPE_TABS.map((scope, index) => (
                    <Tab label={scope.charAt(0).toUpperCase() + scope.slice(1)} key={index} />
                ))}
            </Tabs>
            <Box sx={{ mt: 2, flexGrow: 1, overflowY: 'auto' }}>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', pr: 2, pb: 1 }}>
                    <Button
                        variant="outlined"
                        size="small"
                        startIcon={<AddIcon />}
                        onClick={handleOpenAddDialogAtRoot}
                        disabled={!currentScopeData} // 如果当前范围没有数据（是null），则禁用
                    >
                        在 "{SCOPE_TABS[activeScope]}" 中添加项
                    </Button>
                </Box>
                {currentScopeData ? (
                    // ---将新的处理器传递给 DataTree ---
                    <DataTree 
                        data={currentScopeData} 
                        path={SCOPE_TABS[activeScope]} 
                        onEdit={handleEdit} 
                        onAdd={handleOpenAddDialog}
                        onRename={handleRenameRequest}
                        onDelete={handleDeleteItem}
                    />
                ) : (
                    <Typography color="text.secondary" sx={{ p: 2 }}>
                        该范围内没有可用数据。
                        <Button onClick={handleOpenAddDialogAtRoot} sx={{ml: 1}}>点击此处创建。</Button>
                    </Typography>
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
            
            {/* ---渲染 Rename 对话框 --- */}
            <RenameItemDialog
                open={!!renameItemTarget}
                onClose={() => setRenameItemTarget(null)}
                onRename={handleRenameConfirm}
                item={renameItemTarget}
                existingKeys={renameItemTarget?.existingKeys}
            />
        </Box>
    );
}

export default SandboxEditorPage;