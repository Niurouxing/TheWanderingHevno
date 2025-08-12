// plugins/core_llm_config/src/LLMConfigPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
    Box, Typography, Paper, CircularProgress, Button, Alert, TextField,
    Select, MenuItem, FormControl, InputLabel
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import RefreshIcon from '@mui/icons-material/Refresh';
import { KeyStatusTable } from './components/KeyStatusTable';
import { fetchKeyConfig, updateKeyConfig } from './utils/api';

export function LLMConfigPage() {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [provider, setProvider] = useState('gemini'); // 目前硬编码
    const [keysText, setKeysText] = useState('');

    const loadData = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const data = await fetchKeyConfig(provider);
            setConfig(data);
            const currentKeys = data.keys.map(k => `****-****-****${k.key_suffix.slice(3)}`).join('\n');
            // 为了安全，我们不显示真实密钥，只显示一个格式化的占位符
            // 但用户编辑时会覆盖它
            // setKeysText(currentKeys); // 决定不预填充以避免混淆
        } catch (e) {
            setError(e.message);
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [provider]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleSave = async () => {
        setSaving(true);
        setError('');
        try {
            const newKeys = keysText.split('\n').map(k => k.trim()).filter(Boolean);
            await updateKeyConfig(provider, newKeys);
            // 保存后重新加载数据
            await loadData();
        } catch (e) {
            setError(`保存失败: ${e.message}`);
        } finally {
            setSaving(false);
        }
    };

    return (
        <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
            <Typography variant="h4" gutterBottom>LLM 提供商配置</Typography>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <Paper sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
                <Box>
                    <FormControl sx={{ minWidth: 200 }}>
                        <InputLabel>提供商</InputLabel>
                        <Select
                            value={provider}
                            label="提供商"
                            onChange={(e) => setProvider(e.target.value)}
                            size="small"
                        >
                            <MenuItem value="gemini">Gemini</MenuItem>
                            {/* <MenuItem value="openai" disabled>OpenAI (soon)</MenuItem> */}
                        </Select>
                    </FormControl>
                </Box>

                {loading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                        <CircularProgress />
                    </Box>
                ) : (
                    config && (
                        <Box>
                            <Typography variant="h6" gutterBottom>当前密钥状态</Typography>
                            <KeyStatusTable keys={config.keys} />
                        </Box>
                    )
                )}

                <Box>
                    <Typography variant="h6" gutterBottom>更新密钥</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        在此处粘贴新的 API 密钥，每行一个。点击保存后，将覆盖现有密钥配置。
                        <b>注意：</b>此更改仅在当前服务器会话中有效，重启后将恢复为环境变量中的设置。
                    </Typography>
                    <TextField
                        fullWidth
                        multiline
                        rows={6}
                        label="API 密钥 (每行一个)"
                        value={keysText}
                        onChange={(e) => setKeysText(e.target.value)}
                        placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxx\nai-xxxxxxxxxxxxxxxxxxxxxxxx"
                        variant="outlined"
                    />
                </Box>
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                        variant="contained"
                        startIcon={<SaveIcon />}
                        onClick={handleSave}
                        disabled={saving || loading}
                    >
                        {saving ? <CircularProgress size={24} color="inherit" /> : '保存并应用'}
                    </Button>
                    <Button
                        variant="outlined"
                        startIcon={<RefreshIcon />}
                        onClick={loadData}
                        disabled={loading || saving}
                    >
                        刷新状态
                    </Button>
                </Box>
            </Paper>
        </Box>
    );
}

// 默认导出，以便 host 插件可以懒加载
export default LLMConfigPage;

// 具名导出，以便 manifest 可以通过 componentExportName 找到它
export const registerPlugin = () => {};