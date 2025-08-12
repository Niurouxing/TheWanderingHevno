// plugins/core_runner_ui/src/components/MessageBubble.jsx
import React, { useState } from 'react';
import { Box, Paper, Typography, Avatar, IconButton, Tooltip, TextField, Button, CircularProgress } from '@mui/material';
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
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 1 }}>
                        <Button size="small" onClick={handleCancelEdit}>取消</Button>
                        <Button size="small" variant="contained" onClick={handleSaveEdit}>保存并提交</Button>
                    </Box>
                </Box>
            );
        }

        return (
            <Typography component="div" sx={{ '& p': { my: 0 }, '& pre': { whiteSpace: 'pre-wrap', wordBreak: 'break-all' }, '& table': {borderCollapse: 'collapse'}, '& th, & td': {border: '1px solid', borderColor: 'divider', px: 1, py: 0.5} }}>
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
            <Box sx={{ display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row', alignItems: 'flex-start', maxWidth: '85%', position: 'relative' }}>
                <Avatar sx={{ bgcolor: isUser ? 'primary.main' : 'secondary.main', ml: isUser ? 1.5 : 0, mr: isUser ? 0 : 1.5, mt: 0.5 }}>
                    {isUser ? <PersonIcon /> : <SmartToyIcon />}
                </Avatar>
                <Paper
                    variant="elevation"
                    elevation={1}
                    sx={{
                        p: 1.5,
                        bgcolor: isUser ? 'primary.dark' : 'background.paper',
                        borderRadius: isUser ? '20px 4px 20px 20px' : '4px 20px 20px 20px',
                        position: 'relative',
                    }}
                >
                   {renderContent()}
                </Paper>
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
                    mx: 0.5,
                    bgcolor: 'background.default',
                    borderRadius: '20px',
                    p: '2px',
                    boxShadow: 1
                }}>
                    {isUser && onEditSubmit && (
                         <Tooltip title="编辑并重新生成">
                            <IconButton size="small" onClick={handleEditClick}><EditIcon sx={{fontSize: '1rem'}} /></IconButton>
                         </Tooltip>
                    )}
                    {!isUser && onRegenerate && (
                         <Tooltip title="重新生成">
                            <IconButton size="small" onClick={() => onRegenerate(message)}><ReplayIcon sx={{fontSize: '1rem'}} /></IconButton>
                         </Tooltip>
                    )}
                </Box>
            </Box>
        </Box>
    );
};