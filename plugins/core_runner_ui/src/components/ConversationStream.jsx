// plugins/core_runner_ui/src/components/ConversationStream.jsx
import React from 'react';
import { Box, Paper, Typography, Avatar, IconButton, Tooltip } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ReplayIcon from '@mui/icons-material/Replay'; 
import EditIcon from '@mui/icons-material/Edit'; 

const Message = ({ message, onRegenerate, onEdit }) => {
    const isUser = message.level === 'user';
    const [isHovered, setIsHovered] = React.useState(false);

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
            <Box sx={{ display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row', alignItems: 'center', maxWidth: '80%', position: 'relative' }}>
                {/* [新增] 操作按钮 */}
                <Box sx={{
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    opacity: isHovered ? 1 : 0,
                    transition: 'opacity 0.2s',
                    position: 'absolute',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    left: isUser ? 'auto' : '100%',
                    right: isUser ? '100%' : 'auto',
                    mx: 1,
                }}>
                    {isUser && onEdit && (
                         <Tooltip title="编辑并重新生成">
                            <IconButton size="small" onClick={() => onEdit(message)}><EditIcon fontSize="inherit" /></IconButton>
                         </Tooltip>
                    )}
                    {!isUser && onRegenerate && (
                         <Tooltip title="重新生成">
                            <IconButton size="small" onClick={() => onRegenerate(message)}><ReplayIcon fontSize="inherit" /></IconButton>
                         </Tooltip>
                    )}
                </Box>
                
                <Avatar sx={{
                    bgcolor: isUser ? 'primary.main' : 'secondary.main',
                    ml: isUser ? 1 : 0,
                    mr: isUser ? 0 : 1,
                    alignSelf: 'flex-start'
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

//  将 onRegenerate 和 onEdit 传递给 Message
export const ConversationStream = ({ messages, onRegenerate, onEdit }) => {
    // 过滤掉那些没有内容的临时快照消息
    const displayableMessages = messages.filter(msg => msg.content && msg.level);
    return (
        <Box sx={{ p: { xs: 1, sm: 2 } }}>
            {displayableMessages.map((msg, index) => (
                <Message key={msg.id || index} message={msg} onRegenerate={onRegenerate} onEdit={onEdit} />
            ))}
        </Box>
    );
};