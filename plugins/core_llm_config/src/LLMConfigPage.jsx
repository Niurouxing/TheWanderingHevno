// plugins/core_llm_config/src/LLMConfigPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
    Box, Typography, Paper, CircularProgress, Button, Alert, TextField,
    Select, MenuItem, FormControl, InputLabel, Tooltip, IconButton
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SyncIcon from '@mui/icons-material/Sync';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import { KeyStatusTable } from './components/KeyStatusTable';
import { ProviderDetails } from './components/ProviderDetails';
import { fetchProviders, reloadConfig, fetchKeyConfig, addKey, deleteKey, addProvider, deleteProvider, updateProvider } from './utils/api';
import { ProviderEditDialog } from './components/ProviderEditDialog';

export function LLMConfigPage({ services }) {
    const [providers, setProviders] = useState([]);
    const [selectedProvider, setSelectedProvider] = useState('');
    const [keyConfig, setKeyConfig] = useState(null);
    const [loading, setLoading] = useState({ providers: true, keys: false, action: false });
    const [error, setError] = useState('');
    const [newKey, setNewKey] = useState('');
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [providerToEdit, setProviderToEdit] = useState(null);

    const confirmationService = services?.get('confirmationService');
    const selectedProviderDetails = providers.find(p => p.id === selectedProvider);
    
    // --- [核心修复 1/4] 简化 loadProviders 函数 ---
    // 它现在只负责获取和设置列表，不再管理选中状态。
    // 它的 useCallback 依赖为空，确保它在组件生命周期中是稳定的。
    const loadProviders = useCallback(async () => {
        setLoading(prev => ({ ...prev, providers: true }));
        setError('');
        let fetchedProviders = [];
        try {
            const data = await fetchProviders();
            fetchedProviders = data.filter(p => p.id !== 'mock');
            setProviders(fetchedProviders);
        } catch (e) {
            setError(`加载提供商列表失败: ${e.message}`);
            setProviders([]); // 出错时清空列表
        } finally {
            setLoading(prev => ({ ...prev, providers: false }));
        }
        // 返回获取到的数据，以便调用者可以立即使用
        return fetchedProviders;
    }, []);

    // [修改] 加载选中提供商的密钥配置
    const loadKeyData = useCallback(async () => {
        if (!selectedProvider) return;
        setLoading(prev => ({ ...prev, keys: true }));
        setError('');
        try {
            const data = await fetchKeyConfig(selectedProvider);
            setKeyConfig(data);
        } catch (e) {
            setError(e.message);
            setKeyConfig({ provider: selectedProvider, keys: [] });
        } finally {
            setLoading(prev => ({ ...prev, keys: false }));
        }
    }, [selectedProvider]);
    
    // --- [核心修复 2/4] 拆分 useEffect ---
    // 这个 Effect 只在组件首次挂载时运行，用于初始数据加载。
    useEffect(() => {
        const initialLoad = async () => {
            const data = await loadProviders();
            if (data.length > 0) {
                setSelectedProvider(data[0].id);
            }
        };
        initialLoad();
    }, [loadProviders]); // loadProviders 是稳定的，所以这只运行一次

    // 这个 Effect 行为正确，保持不变。它在选中项改变时加载密钥数据。
    useEffect(() => {
        if (selectedProvider) {
            loadKeyData();
        } else {
            setKeyConfig(null); // 如果没有选中项，清空密钥数据
        }
    }, [selectedProvider, loadKeyData]);

    const handleReload = async () => {
        setLoading(prev => ({...prev, action: true}));
        setError('');
        try {
            await reloadConfig();
            const data = await loadProviders();
            if (data.length > 0) {
                setSelectedProvider(data[0].id);
            }
        } catch (e) {
            setError(`重载失败: ${e.message}`);
        } finally {
            setLoading(prev => ({...prev, action: false}));
        }
    };

    const handleAddKey = async () => {
        if (!newKey.trim() || !selectedProvider) return;
        setLoading(prev => ({ ...prev, action: true }));
        setError('');
        try {
            await addKey(selectedProvider, newKey.trim());
            setNewKey('');
            await loadKeyData();
        } catch (e) {
            setError(`添加失败: ${e.message}`);
        } finally {
            setLoading(prev => ({ ...prev, action: false }));
        }
    };
    
    const handleDeleteKey = async (keySuffix) => {
        if (!confirmationService) return;
        const confirmed = await confirmationService.confirm({
            title: '删除密钥确认',
            message: `确定要从 .env 文件中永久删除提供商 "${selectedProvider}" 的密钥 "${keySuffix}" 吗？`,
        });
        if (!confirmed) return;
        
        setLoading(prev => ({ ...prev, action: true }));
        setError('');
        try {
            await deleteKey(selectedProvider, keySuffix);
            await loadKeyData();
        } catch (e) {
            setError(`删除失败: ${e.message}`);
        } finally {
            setLoading(prev => ({ ...prev, action: false }));
        }
    };

    // --- [新增] 打开编辑对话框的处理器 ---
    const handleOpenEditDialog = (provider) => {
        setProviderToEdit(provider);
        setIsDialogOpen(true);
    };

    // --- [新增] 打开新增对话框的处理器 ---
    const handleOpenAddDialog = () => {
        setProviderToEdit(null); // 传入 null 表示是新增模式
        setIsDialogOpen(true);
    };

    // --- [修改] 保存处理器，现在能处理新增和更新 ---
    // --- [核心修复 3/4] 在事件处理器中编排状态 ---
    const handleSaveProvider = async (providerConfig) => {
        setLoading(prev => ({ ...prev, action: true }));
        setError('');
        try {
            if (providerToEdit && providerToEdit.id) {
                // 更新模式
                await updateProvider(providerToEdit.id, providerConfig);
            } else {
                // 新增模式
                await addProvider(providerConfig);
            }
            setIsDialogOpen(false);
            setProviderToEdit(null);
            
            // 操作成功后，重新加载列表，并显式设置选中项为刚刚保存的那个
            await loadProviders();
            setSelectedProvider(providerConfig.id);

        } catch (e) {
            // 不关闭对话框，让用户看到错误
            setError(`保存提供商失败: ${e.message}`);
        } finally {
            setLoading(prev => ({ ...prev, action: false }));
        }
    };
    
    // --- [新增] 处理删除提供商的逻辑 ---
    // --- [核心修复 4/4] 在事件处理器中编排状态 ---
    const handleDeleteProvider = async (providerId) => {
        if (!confirmationService) return;
        const confirmed = await confirmationService.confirm({
            title: '删除提供商确认',
            message: `此操作将从 .env 文件中永久删除提供商 "${providerId}" 及其所有密钥。此操作不可逆，确定吗？`,
        });
        if (!confirmed) return;

        setLoading(prev => ({ ...prev, action: true }));
        setError('');
        try {
            await deleteProvider(providerId);
            
            // 操作成功后，重新加载列表
            const newList = await loadProviders();

            // 如果删除的是当前选中的提供商，则智能地选择下一个
            if (selectedProvider === providerId) {
                setSelectedProvider(newList.length > 0 ? newList[0].id : '');
            }
        } catch (e) {
            setError(`删除提供商失败: ${e.message}`);
        } finally {
            setLoading(prev => ({ ...prev, action: false }));
        }
    };

    const isActionInProgress = loading.action || loading.keys || loading.providers;

    return (
        <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h4" component="div">LLM 提供商配置</Typography>
                <Box sx={{display: 'flex', gap: 1}}>
                    <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        // [修改] 调用新的处理器
                        onClick={handleOpenAddDialog}
                        disabled={isActionInProgress}
                    >
                        添加提供商
                    </Button>
                    <Tooltip title="从 .env 文件重新加载所有提供商配置">
                        <span>
                            <Button
                                variant="outlined"
                                startIcon={loading.action ? <CircularProgress size={20} /> : <SyncIcon />}
                                onClick={handleReload}
                                disabled={isActionInProgress}
                            >
                                热重载
                            </Button>
                        </span>
                    </Tooltip>
                </Box>
            </Box>
            
            <Alert severity="warning" sx={{ mb: 3 }}>
                <b>警告:</b> 此页面上的操作将直接修改您服务器上的 <code>.env</code> 文件。请谨慎操作。
            </Alert>

            {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

            <Paper sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
                <FormControl sx={{ minWidth: 200 }} size="small" disabled={isActionInProgress}>
                    <InputLabel>选择提供商</InputLabel>
                    <Select value={selectedProvider} label="选择提供商" onChange={(e) => setSelectedProvider(e.target.value)}>
                        {loading.providers && <MenuItem value="" disabled><em>正在加载...</em></MenuItem>}
                        {!loading.providers && providers.length === 0 && <MenuItem value="" disabled><em>未找到自定义提供商</em></MenuItem>}
                        {providers.map(p => <MenuItem key={p.id} value={p.id}>{p.id}</MenuItem>)}
                    </Select>
                </FormControl>
                
                {selectedProvider && selectedProviderDetails ? (
                    <>
                        <Box sx={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
                        <ProviderDetails provider={selectedProviderDetails} onEdit={() => handleOpenEditDialog(selectedProviderDetails)} />
                        {/* --- [新增] 删除提供商按钮 --- */}
                        {!["gemini"].includes(selectedProviderDetails.id) && (
                                <Tooltip title={`删除提供商 '${selectedProviderDetails.id}'`}>
                                    <span>
                                        <IconButton onClick={() => handleDeleteProvider(selectedProviderDetails.id)} color="error" disabled={isActionInProgress}>
                                            <DeleteForeverIcon />
                                        </IconButton>
                                    </span>
                                </Tooltip>
                             )}
                        </Box>
                        <KeyManagementSection
                            providerId={selectedProvider}
                            keyConfig={keyConfig}
                            loading={loading.keys || loading.action}
                            newKey={newKey}
                            setNewKey={setNewKey}
                            onAddKey={handleAddKey}
                            onDeleteKey={handleDeleteKey}
                            onRefresh={loadKeyData}
                        />
                    </>
                ) : (
                     !loading.providers && <Typography color="text.secondary">请添加或选择一个提供商以管理其密钥。</Typography>
                )}
            </Paper>

            {/* [修改] 渲染对话框并传入正确的 props */}
            <ProviderEditDialog
                open={isDialogOpen}
                onClose={() => setIsDialogOpen(false)}
                onSave={handleSaveProvider}
                existingProviderIds={providers.map(p => p.id)}
                providerToEdit={providerToEdit}
            />
        </Box>
    );
}

// --- [新增] 提取密钥管理部分为一个独立的组件以保持整洁 ---
function KeyManagementSection({ providerId, keyConfig, loading, newKey, setNewKey, onAddKey, onDeleteKey, onRefresh }) {
    return (
        <>
            <Box>
                <Typography variant="h6" gutterBottom>当前密钥状态</Typography>
                {loading && !keyConfig ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /></Box>
                ) : (
                    <KeyStatusTable keys={keyConfig?.keys || []} onDelete={onDeleteKey} isDeleting={loading} />
                )}
            </Box>
            <Box>
                <Typography variant="h6" gutterBottom>为 "{providerId}" 添加新密钥</Typography>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <TextField fullWidth label="新 API 密钥" value={newKey} onChange={(e) => setNewKey(e.target.value)} placeholder="在此处粘贴完整的 API 密钥" variant="outlined" size="small" onKeyPress={(e) => e.key === 'Enter' && onAddKey()} disabled={loading} />
                    <Button variant="contained" onClick={onAddKey} disabled={loading || !newKey.trim()}>
                        {loading ? <CircularProgress size={24} color="inherit" /> : <AddIcon />}
                    </Button>
                </Box>
            </Box>
            <Button variant="outlined" onClick={onRefresh} disabled={loading} sx={{ alignSelf: 'flex-start' }}>
                刷新密钥状态
            </Button>
        </>
    );
}

export default LLMConfigPage;
export const registerPlugin = () => {};