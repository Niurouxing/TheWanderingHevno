// plugins/core_runner_ui/src/components/MessageBubble.jsx
import React, { useState } from 'react';
import { Box, Paper, Typography, Avatar, IconButton, Tooltip, TextField, Button } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ReplayIcon from '@mui/icons-material/Replay'; 
import EditIcon from '@mui/icons-material/Edit'; 

export const MessageBubble = ({ message, onRegenerate, onEditSubmit }) => {
    const isUser = message.level === 'user';
    const [isHovered, setIsHovered] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editedContent, setEditedContent] = useState(message.content);

    const handleEditClick = () => {
        setIsEditing(true);
    };

    const handleCancelEdit = () => {
        setIsEditing(false);
        setEditedContent(message.content); // 恢复原始内容
    };

    const handleSaveEdit = () => {
        if (editedContent.trim()) {
            onEditSubmit(message, editedContent);
            setIsEditing(false);
        }
    };
    
    const renderContent = () => {
        if (isEditing) {
            return (
                <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <TextField
                        fullWidth
                        multiline
                        variant="standard"
                        value={editedContent}
                        onChange={(e) => setEditedContent(e.target.value)}
                        autoFocus
                    />
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                        <Button size="small" onClick={handleCancelEdit}>取消</Button>
                        <Button size="small" variant="contained" onClick={handleSaveEdit}>保存</Button>
                    </Box>
                </Box>
            );
        }

        return (
            <Typography component="div" sx={{ '& p': { my: 0 }, '& pre': { whiteSpace: 'pre-wrap', wordBreak: 'break-all' } }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                </ReactMarkdown>
            </Typography>
        );
    };

    return (
        <Box
            sx={{
                display: 'flex',
                justifyContent: isUser ? 'flex-end' : 'flex-start',
                mb: 2,
            }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <Box sx={{ display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row', alignItems: 'center', width: '85%', position: 'relative' }}>
                <Box sx={{
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    opacity: isHovered && !isEditing ? 1 : 0,
                    transition: 'opacity 0.2s',
                    position: 'absolute',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    left: isUser ? 'auto' : '100%',
                    right: isUser ? '100%' : 'auto',
                    mx: 1,
                }}>
                    {isUser && onEditSubmit && (
                         <Tooltip title="编辑并重新生成">
                            <IconButton size="small" onClick={handleEditClick}><EditIcon fontSize="inherit" /></IconButton>
                         </Tooltip>
                    )}
                    {!isUser && onRegenerate && (
                         <Tooltip title="重新生成">
                            <IconButton size="small" onClick={() => onRegenerate(message)}><ReplayIcon fontSize="inherit" /></IconButton>
                         </Tooltip>
                    )}
                </Box>
                
                <Avatar sx={{ bgcolor: isUser ? 'primary.main' : 'secondary.main', ml: isUser ? 1 : 0, mr: isUser ? 0 : 1, alignSelf: 'flex-start' }}>
                    {isUser ? <PersonIcon /> : <SmartToyIcon />}
                </Avatar>
                <Paper
                    variant="outlined"
                    sx={{
                        p: 1.5,
                        bgcolor: isUser ? 'primary.dark' : 'background.paper',
                        border: '1px solid',
                        borderColor: isUser ? 'primary.main' : 'divider',
                        borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
                        width: '100%'
                    }}
                >
                   {renderContent()}
                </Paper>
            </Box>
        </Box>
    );
};