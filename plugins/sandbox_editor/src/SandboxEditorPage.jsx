import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, Button } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SCOPE_TABS } from './utils/constants';
import { DataTree } from './components/DataTree';
import { CodexEditor } from './editors/CodexEditor';
import { GraphEditor } from './editors/GraphEditor';
import { MemoriaEditor } from './editors/MemoriaEditor';
// --- [修改 1/4] 导入新的API客户端 ---
import { query } from './utils/api';

export function SandboxEditorPage({ services }) {
    const { currentSandboxId, setActivePageId, setCurrentSandboxId } = useLayout();
    const [sandboxData, setSandboxData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeScope, setActiveScope] = useState(0);
    const [editingCodex, setEditingCodex] = useState(null);
    const [editingGraph, setEditingGraph] = useState(null);
    const [editingMemoria, setEditingMemoria] = useState(null);

    // --- [修改 2/4] 重写数据加载函数，使用统一的 :query API ---
    const loadSandboxData = useCallback(async () => {
        if (!currentSandboxId) return;
        setLoading(true);
        setError('');
        try {
            // 在一次API调用中获取所有需要的数据
            const results = await query(currentSandboxId, ['definition', 'lore', 'moment']);
            setSandboxData(results); // API返回的已经是 { definition: {...}, lore: {...}, moment: {...} } 格式
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
    
    // --- [修改 3/4] 简化 onEdit 处理，路径现在直接来源于DataTree ---
    const handleEdit = (path, value) => {
        const pathParts = path.split('/');
        const editorType = value.__hevno_type__;
        const name = pathParts[pathParts.length - 1]; // e.g., 'main' or 'npc_status'
        const scope = pathParts[0]; // e.g., 'lore' or 'definition'

        if (editorType === 'hevno/codex') {
            setEditingCodex({ name, data: value, scope });
        } else if (editorType === 'hevno/graph') {
            setEditingGraph({ name, data: value, scope });
        } else if (editorType === 'hevno/memoria') {
             // Memoria 编辑器不需要 scope 和 name，它直接处理整个 moment.memoria 对象
            setEditingMemoria({ data: value, path: path });
        } else {
            alert(`Edit functionality for type "${editorType}" at "${path}" is not yet implemented.`);
        }
    };
    
    const handleBackToOverview = () => {
        setEditingCodex(null);
        setEditingGraph(null);
        setEditingMemoria(null);
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
                onBack={handleBackToOverview}
            />
        );
    } else if (editingGraph) {
        return (
            <GraphEditor
                sandboxId={currentSandboxId}
                scope={editingGraph.scope}
                graphName={editingGraph.name}
                graphData={editingGraph.data}
                onBack={handleBackToOverview}
            />
        );
    } else if (editingMemoria) {
      return (
        <MemoriaEditor
          sandboxId={currentSandboxId}
          // --- [修改 4/4] 传递 memoria 对象的完整路径和数据 ---
          basePath={editingMemoria.path}
          memoriaData={editingMemoria.data}
          onBack={handleBackToOverview}
        />
      );
    }

    // ... 其余渲染代码保持不变 ...
    const sandboxName = (sandboxData.definition?.name || sandboxData.lore?.name || 'Sandbox');

    return (
        <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
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
        </Box>
    );
}

export default SandboxEditorPage;