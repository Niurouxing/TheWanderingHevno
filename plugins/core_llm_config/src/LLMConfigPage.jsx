// plugins/core_llm_config/src/LLMConfigPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
    Box, Typography, Paper, CircularProgress, Button, Alert, TextField,
    Select, MenuItem, FormControl, InputLabel, Tooltip
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import SyncIcon from '@mui/icons-material/Sync';
import { KeyStatusTable } from './components/KeyStatusTable';
// [修改] 导入所有新的API函数
import { fetchProviders, reloadConfig, fetchKeyConfig, addKey, deleteKey } from './utils/api';

export function LLMConfigPage({ services }) {
    // [修改] 状态管理
    const [providers, setProviders] = useState([]);
    const [selectedProvider, setSelectedProvider] = useState('');
    const [keyConfig, setKeyConfig] = useState(null);
    const [loading, setLoading] = useState({ providers: true, keys: false, action: false });
    const [error, setError] = useState('');
    const [newKey, setNewKey] = useState('');

    const confirmationService = services?.get('confirmationService');

    // [修改] 加载提供商列表
    const loadProviders = useCallback(async (selectFirst = false) => {
        setLoading(prev => ({ ...prev, providers: true }));
        setError('');
        try {
            const data = await fetchProviders();
            setProviders(data);
            if (selectFirst && data.length > 0) {
                setSelectedProvider(data[0].id);
            } else if (data.length === 0) {
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

    const handleAdd = async () => {
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
    
    const handleDelete = async (keySuffix) => {
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

    const isActionInProgress = loading.action || loading.keys || loading.providers;

    return (
        <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h4" gutterBottom component="div" sx={{m:0}}>LLM 提供商配置</Typography>
                <Tooltip title="从 .env 文件重新加载所有提供商配置">
                    <span>
                        <Button
                            variant="outlined"
                            startIcon={loading.action ? <CircularProgress size={20} /> : <SyncIcon />}
                            onClick={handleReload}
                            disabled={isActionInProgress}
                        >
                            热重载配置
                        </Button>
                    </span>
                </Tooltip>
            </Box>
            
            <Alert severity="warning" sx={{ mb: 3 }}>
                <b>警告:</b> 此页面上的操作将直接修改您服务器上的 <code>.env</code> 文件。请谨慎操作。
            </Alert>

            {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

            <Paper sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
                <FormControl sx={{ minWidth: 200 }} size="small" disabled={isActionInProgress}>
                    <InputLabel>提供商</InputLabel>
                    <Select value={selectedProvider} label="提供商" onChange={(e) => setSelectedProvider(e.target.value)}>
                        {providers.length === 0 && <MenuItem value="" disabled><em>正在加载或未找到提供商...</em></MenuItem>}
                        {providers.map(p => <MenuItem key={p.id} value={p.id}>{p.id}</MenuItem>)}
                    </Select>
                </FormControl>
                
                {selectedProvider ? (
                    <>
                        <Box>
                            <Typography variant="h6" gutterBottom>当前密钥状态</Typography>
                            {loading.keys ? (
                                <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /></Box>
                            ) : (
                                <KeyStatusTable keys={keyConfig?.keys || []} onDelete={handleDelete} isDeleting={loading.action} />
                            )}
                        </Box>
                        <Box>
                            <Typography variant="h6" gutterBottom>为 "{selectedProvider}" 添加新密钥</Typography>
                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                <TextField fullWidth label="新 API 密钥" value={newKey} onChange={(e) => setNewKey(e.target.value)} placeholder="在此处粘贴完整的 API 密钥" variant="outlined" size="small" onKeyPress={(e) => e.key === 'Enter' && handleAdd()} disabled={isActionInProgress} />
                                <Button variant="contained" onClick={handleAdd} disabled={isActionInProgress || !newKey.trim()}>
                                    {loading.action ? <CircularProgress size={24} color="inherit" /> : <AddIcon />}
                                </Button>
                            </Box>
                        </Box>
                        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadKeyData} disabled={isActionInProgress} sx={{ alignSelf: 'flex-start' }}>
                            刷新状态
                        </Button>
                    </>
                ) : (
                    !loading.providers && <Typography color="text.secondary">请从环境变量配置并选择一个提供商。</Typography>
                )}
            </Paper>
        </Box>
    );
}

export default LLMConfigPage;
export const registerPlugin = () => {};