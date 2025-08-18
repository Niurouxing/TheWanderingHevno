// plugins/core_runner_ui/src/components/ConversationStream.jsx
import React from 'react';
import { Box } from '@mui/material';
import { MessageBubble } from './MessageBubble'; //导入新组件

export const ConversationStream = ({ messages, onRegenerate, onEditSubmit }) => {
    // 过滤掉那些没有内容的临时快照消息
    const displayableMessages = messages.filter(msg => msg.content && msg.level);
    
    const conversationEndRef = React.useRef(null);
    React.useEffect(() => {
        conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    return (
        <Box sx={{ p: { xs: 1, sm: 2 } }}>
            {displayableMessages.map((msg, index) => (
                <MessageBubble 
                    key={msg.id || index} 
                    message={msg} 
                    onRegenerate={onRegenerate} 
                    onEditSubmit={onEditSubmit} 
                />
            ))}
            <div ref={conversationEndRef} />
        </Box>
    );
};