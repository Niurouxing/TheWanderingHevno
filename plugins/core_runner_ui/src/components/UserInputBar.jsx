// plugins/core_runner_ui/src/components/UserInputBar.jsx
import React, { useState } from 'react';
import { TextField, IconButton, Box, CircularProgress, Paper } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

export function UserInputBar({ onSendMessage, isLoading }) {
    const [text, setText] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (text.trim() && !isLoading) {
            onSendMessage(text);
            setText('');
        }
    };

    return (
        <Paper 
            component="form" 
            onSubmit={handleSubmit} 
            sx={{ 
                p: '4px 8px', 
                display: 'flex', 
                alignItems: 'center', 
                width: '100%',
                borderRadius: '12px'
            }}
            elevation={2}
        >
            <TextField
                fullWidth
                placeholder="在此输入消息... (Shift+Enter 换行)"
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={isLoading}
                multiline
                maxRows={8}
                variant="standard" // 使用无边框样式
                InputProps={{
                    disableUnderline: true, // 移除下划线
                }}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit(e);
                    }
                }}
                sx={{ ml: 1 }}
            />
            <IconButton
                type="submit"
                color="primary"
                disabled={!text.trim() || isLoading}
                sx={{ p: '10px' }}
            >
                {isLoading ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
            </IconButton>
        </Paper>
    );
}