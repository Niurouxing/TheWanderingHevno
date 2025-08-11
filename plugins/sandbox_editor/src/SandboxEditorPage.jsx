import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, Button } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SCOPE_TABS } from './utils/constants';
import { DataTree } from './components/DataTree';
import { CodexEditor } from './editors/CodexEditor';
import { GraphEditor } from './editors/GraphEditor';
import { MemoriaEditor } from './editors/MemoriaEditor';
// --- [修改 1/5] 导入新的API客户端和通用编辑器 ---
import { query, mutate } from './utils/api';
import { GenericEditorDialog } from './editors/GenericEditorDialog';
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
    // --- [修改 2/5] 添加用于通用编辑器的状态 ---
    const [editingGeneric, setEditingGeneric] = useState(null);

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
    
    // --- [修改 3/5] 重写 onEdit 处理器以路由到正确的编辑器 ---
    const handleEdit = (path, value) => {
        const editorType = isObject(value) ? value.__hevno_type__ : undefined;

        if (editorType) {
            const pathParts = path.split('/');
            const name = pathParts[pathParts.length - 1];

            if (editorType === 'hevno/codex') {
                setEditingCodex({ name, data: value, basePath: path });
            } else if (editorType === 'hevno/graph') {
                setEditingGraph({ name, data: value, basePath: path });
            } else if (editorType === 'hevno/memoria') {
                setEditingMemoria({ data: value, path: path });
            } else {
                // 对于未知的特殊类型，也使用通用编辑器
                setEditingGeneric({ path, value });
            }
        } else {
            // 对于所有普通值（字符串、数字、数组、普通对象），使用通用编辑器
            setEditingGeneric({ path, value });
        }
    };
    
    const handleBackToOverview = () => {
        setEditingCodex(null);
        setEditingGraph(null);
        setEditingMemoria(null);
        loadSandboxData();
    };

    // --- [修改 4/5] 添加保存通用数据的方法 ---
    const handleGenericSave = async (path, newValue) => {
        try {
            await mutate(currentSandboxId, [{ type: 'UPSERT', path, value: newValue }]);
            setEditingGeneric(null); // 关闭对话框
            await loadSandboxData(); // 重新加载数据以刷新树
        } catch (err) {
            console.error(`保存路径 "${path}" 的值失败:`, err);
            // 将错误重新抛出，以便对话框可以捕获并显示它
            throw err;
        }
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
        return <CodexEditor sandboxId={currentSandboxId} basePath={editingCodex.basePath} codexName={editingCodex.name} codexData={editingCodex.data} onBack={handleBackToOverview} />;
    } else if (editingGraph) {
        return <GraphEditor sandboxId={currentSandboxId} basePath={editingGraph.basePath} graphName={editingGraph.name} graphData={editingGraph.data} onBack={handleBackToOverview} />;
    } else if (editingMemoria) {
      return <MemoriaEditor sandboxId={currentSandboxId} basePath={editingMemoria.path} memoriaData={editingMemoria.data} onBack={handleBackToOverview} />;
    }

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
            </Box>

            <Tabs value={activeScope} onChange={handleScopeChange} aria-label="sandbox scopes" sx={{ flexShrink: 0, borderBottom: 1, borderColor: 'divider' }}>
                {SCOPE_TABS.map((scope, index) => (
                    <Tab label={scope.charAt(0).toUpperCase() + scope.slice(1)} key={index} />
                ))}
            </Tabs>
            <Box sx={{ mt: 2, flexGrow: 1, overflowY: 'auto' }}>
                {currentScopeData ? (
                    <DataTree data={currentScopeData} path={SCOPE_TABS[activeScope]} onEdit={handleEdit} />
                ) : (
                    <Typography color="text.secondary">该范围内没有可用数据</Typography>
                )}
            </Box>

            {/* --- [修改 5/5] 在页面上渲染通用编辑器对话框 --- */}
            <GenericEditorDialog
                open={!!editingGeneric}
                onClose={() => setEditingGeneric(null)}
                onSave={handleGenericSave}
                item={editingGeneric}
            />
        </Box>
    );
}

export default SandboxEditorPage;