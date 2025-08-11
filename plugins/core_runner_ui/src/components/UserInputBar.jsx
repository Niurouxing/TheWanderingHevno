import React, { useState } from 'react';
import { TextField, Button, Box, CircularProgress } from '@mui/material';
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
        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TextField
                fullWidth
                variant="outlined"
                placeholder="在此输入消息..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={isLoading}
                multiline
                maxRows={5}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit(e);
                    }
                }}
            />
            <Button
                type="submit"
                variant="contained"
                disabled={!text.trim() || isLoading}
                sx={{ height: '56px', minWidth: '56px', px: 2 }}
            >
                {isLoading ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
            </Button>
        </Box>
    );
}