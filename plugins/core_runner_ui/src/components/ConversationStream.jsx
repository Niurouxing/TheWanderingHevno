import React from 'react';
import { Box, Paper, Typography, Avatar } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';

const Message = ({ message }) => {
    const isUser = message.level === 'user';
    const align = isUser ? 'right' : 'left';

    return (
        <Box
            sx={{
                display: 'flex',
                justifyContent: isUser ? 'flex-end' : 'flex-start',
                mb: 2,
            }}
        >
            <Box sx={{ display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row', alignItems: 'flex-start', maxWidth: '80%' }}>
                <Avatar sx={{
                    bgcolor: isUser ? 'primary.main' : 'secondary.main',
                    ml: isUser ? 1 : 0,
                    mr: isUser ? 0 : 1
                }}>
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
                    }}
                >
                    <Typography component="div" sx={{
                        '& p': { my: 0 },
                        '& pre': { whiteSpace: 'pre-wrap', wordBreak: 'break-all' }
                    }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                        </ReactMarkdown>
                    </Typography>
                </Paper>
            </Box>
        </Box>
    );
};

export const ConversationStream = ({ messages }) => {
    return (
        <Box sx={{ p: { xs: 1, sm: 2 } }}>
            {messages.map((msg, index) => (
                <Message key={msg.id || index} message={msg} />
            ))}
        </Box>
    );
};