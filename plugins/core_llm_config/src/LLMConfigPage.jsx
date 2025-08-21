// plugins/core_llm_config/src/LLMConfigPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
    Box, Typography, Paper, CircularProgress, Button, Alert, TextField,
    Select, MenuItem, FormControl, InputLabel, Tooltip, IconButton
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import SyncIcon from '@mui/icons-material/Sync';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever'; // For deleting a provider
import { KeyStatusTable } from './components/KeyStatusTable';
import { ProviderDetails } from './components/ProviderDetails';
// [修改] 导入所有 API 和新对话框
import { fetchProviders, reloadConfig, fetchKeyConfig, addKey, deleteKey, addProvider, deleteProvider } from './utils/api';
import { ProviderEditDialog } from './components/ProviderEditDialog';

export function LLMConfigPage({ services }) {
    const [providers, setProviders] = useState([]);
    const [selectedProvider, setSelectedProvider] = useState('');
    const [keyConfig, setKeyConfig] = useState(null);
    const [loading, setLoading] = useState({ providers: true, keys: false, action: false });
    const [error, setError] = useState('');
    const [newKey, setNewKey] = useState('');
    const [isDialogOpen, setIsDialogOpen] = useState(false); // [新增] 对话框状态

    const confirmationService = services?.get('confirmationService');
    const selectedProviderDetails = providers.find(p => p.id === selectedProvider);
    
    // --- [修改] 在加载时过滤掉 'mock' 提供商 ---
    const loadProviders = useCallback(async (selectFirst = false) => {
        setLoading(prev => ({ ...prev, providers: true }));
        setError('');
        try {
            const data = await fetchProviders();
            const filteredProviders = data.filter(p => p.id !== 'mock'); // <-- 核心过滤逻辑
            setProviders(filteredProviders);
            if (selectFirst && filteredProviders.length > 0) {
                setSelectedProvider(filteredProviders[0].id);
            } else if (filteredProviders.length === 0) {
                setSelectedProvider('');
                setKeyConfig(null);
            }
        } catch (e) {
            setError(`加载提供商列表失败: ${e.message}`);
        } finally {
            setLoading(prev => ({ ...prev, providers: false }));
        }
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
    
    // 初始加载
    useEffect(() => {
        loadProviders(true); // 首次加载并选中第一个
    }, [loadProviders]);

    // 当选择的提供商改变时，加载其密钥
    useEffect(() => {
        if (selectedProvider) {
            loadKeyData();
        }
    }, [selectedProvider, loadKeyData]);

    const handleReload = async () => {
        setLoading(prev => ({...prev, action: true}));
        setError('');
        try {
            await reloadConfig();
            await loadProviders(true); // 重载后，重新获取提供商列表并选中第一个
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

    // --- [新增] 处理添加提供商的逻辑 ---
    const handleSaveProvider = async (providerConfig) => {
        setLoading(prev => ({ ...prev, action: true }));
        setError('');
        try {
            await addProvider(providerConfig);
            setIsDialogOpen(false);
            await loadProviders(); // 重新加载列表
        } catch (e) {
            setError(`创建提供商失败: ${e.message}`);
        } finally {
            setLoading(prev => ({ ...prev, action: false }));
        }
    };

    // --- [新增] 处理删除提供商的逻辑 ---
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
            // 如果删除的是当前选中的提供商，则清空选择
            if(selectedProvider === providerId) {
                setSelectedProvider('');
                setKeyConfig(null);
            }
            await loadProviders(true); // 重新加载并选中第一个
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
                    {/* --- [新增] 添加提供商按钮 --- */}
                    <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={() => setIsDialogOpen(true)}
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
                             <ProviderDetails provider={selectedProviderDetails} />
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

            {/* --- [新增] 渲染对话框 --- */}
            <ProviderEditDialog
                open={isDialogOpen}
                onClose={() => setIsDialogOpen(false)}
                onSave={handleSaveProvider}
                existingProviderIds={providers.map(p => p.id)}
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