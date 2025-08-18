// plugins/core_llm_config/src/LLMConfigPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
    Box, Typography, Paper, CircularProgress, Button, Alert, TextField,
    Select, MenuItem, FormControl, InputLabel
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import { KeyStatusTable } from './components/KeyStatusTable';
import { fetchKeyConfig, addKey, deleteKey } from './utils/api';

export function LLMConfigPage({ services }) {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [actionInProgress, setActionInProgress] = useState(false); // 通用加载状态
    const [error, setError] = useState('');
    const [provider, setProvider] = useState('gemini');
    const [newKey, setNewKey] = useState('');

    // 获取确认服务
    const confirmationService = services?.get('confirmationService');

    const loadData = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const data = await fetchKeyConfig(provider);
            setConfig(data);
        } catch (e) {
            setError(e.message);
            setConfig({ provider, keys: [] }); // 即使出错也显示空表
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [provider]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleAdd = async () => {
        if (!newKey.trim()) return;
        setActionInProgress(true);
        setError('');
        try {
            await addKey(provider, newKey.trim());
            setNewKey(''); // 清空输入框
            await loadData(); // 重新加载数据
        } catch (e) {
            setError(`添加失败: ${e.message}`);
        } finally {
            setActionInProgress(false);
        }
    };
    
    const handleDelete = async (keySuffix) => {
        if (!confirmationService) {
            console.error('ConfirmationService not available');
            return;
        }
        
        const confirmed = await confirmationService.confirm({
            title: '删除密钥确认',
            message: `确定要从 .env 文件中永久删除密钥 "${keySuffix}" 吗？`,
        });
        if (!confirmed) return;
        
        setActionInProgress(true);
        setError('');
        try {
            await deleteKey(provider, keySuffix);
            await loadData(); // 重新加载数据
        } catch (e) {
            setError(`删除失败: ${e.message}`);
        } finally {
            setActionInProgress(false);
        }
    };

    return (
        <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
            <Typography variant="h4" gutterBottom>LLM 提供商配置</Typography>

            <Alert severity="warning" sx={{ mb: 3 }}>
                <b>警告:</b> 此页面上的操作将直接修改您服务器上的 <code>.env</code> 文件。请谨慎操作。
            </Alert>

            {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

            <Paper sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
                <FormControl sx={{ minWidth: 200 }} size="small">
                    <InputLabel>提供商</InputLabel>
                    <Select value={provider} label="提供商" onChange={(e) => setProvider(e.target.value)}>
                        <MenuItem value="gemini">Gemini</MenuItem>
                    </Select>
                </FormControl>

                <Box>
                    <Typography variant="h6" gutterBottom>当前密钥状态</Typography>
                     {loading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /></Box>
                    ) : (
                        <KeyStatusTable keys={config?.keys || []} onDelete={handleDelete} isDeleting={actionInProgress} />
                    )}
                </Box>

                <Box>
                    <Typography variant="h6" gutterBottom>添加新密钥</Typography>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                         <TextField
                            fullWidth
                            label="新 API 密钥"
                            value={newKey}
                            onChange={(e) => setNewKey(e.target.value)}
                            placeholder="在此处粘贴完整的 API 密钥"
                            variant="outlined"
                            size="small"
                            onKeyPress={(e) => e.key === 'Enter' && handleAdd()}
                        />
                         <Button
                            variant="contained"
                            // startIcon={<AddIcon />}
                            onClick={handleAdd}
                            disabled={actionInProgress || loading || !newKey.trim()}
                        >
                            {actionInProgress && !loading ? <CircularProgress size={36} color="inherit" /> : '添加'}
                        </Button>
                    </Box>
                </Box>
                 <Button
                    variant="outlined"
                    startIcon={<RefreshIcon />}
                    onClick={loadData}
                    disabled={loading || actionInProgress}
                    sx={{ alignSelf: 'flex-start' }}
                >
                    刷新状态
                </Button>
            </Paper>
        </Box>
    );
}

export default LLMConfigPage;
export const registerPlugin = () => {};