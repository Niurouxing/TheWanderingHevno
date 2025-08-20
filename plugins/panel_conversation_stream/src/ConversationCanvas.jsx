import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Box, TextField, IconButton, Typography, CircularProgress } from '@mui/material';
import SendRoundedIcon from '@mui/icons-material/SendRounded';

// [改动] Message 组件现在将样式逻辑拆分到容器和文本上
const Message = React.memo(({ msg }) => {

    // 负责字体和颜色
    const getTypographyStyle = () => {
        switch (msg.type) {
            case 'llm':
                return {
                    fontFamily: "'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif",
                    color: 'text.primary',
                };
            case 'user':
                 return {
                    fontFamily: "'KaiTi', 'BiauKai', 'STKaiti', serif",
                    color: 'text.primary',
                };
            default: // 默认样式，以防万一
                return {
                    fontFamily: "'PingFang SC', 'Microsoft YaHei', sans-serif",
                };
        }
    };

    // 负责布局、边框和内外边距
    const getContainerStyle = () => {
        const baseStyle = { mb: 2.5 }; // 统一设置消息间距
        if (msg.type === 'user') {
            return {
                ...baseStyle,
                borderLeft: '3px solid', // 应用用户喜欢的边框样式
                borderColor: 'primary.main',
                pl: 2, // 增加左内边距，让文字和边框有呼吸空间
            };
        }
        return baseStyle;
    };

    return (
        <Box sx={getContainerStyle()}>
            <Typography variant="body1" sx={{ lineHeight: 1.7, ...getTypographyStyle() }}>
                {msg.content}
            </Typography>
        </Box>
    );
});

const SHOW_THRESHOLD = 250;
const HIDE_THRESHOLD = 100;

export function ConversationCanvas({ moment, performStep, isStepping }) {
    const [inputValue, setInputValue] = useState('');
    const [isNearBottom, setIsNearBottom] = useState(true);
    const scrollRef = useRef(null);
    const debounceTimerRef = useRef(null);

    const messages = useMemo(() => {
        const historyEntries = moment?.memoria?.chat_history?.entries || [];
        return historyEntries.map(entry => ({
            ...entry,
            type: entry.level === 'model' ? 'llm' : entry.level,
        }));
    }, [moment]);

    const handleScroll = useCallback(() => {
        const container = scrollRef.current;
        if (!container) return;

        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }

        debounceTimerRef.current = setTimeout(() => {
            const { scrollTop, scrollHeight, clientHeight } = container;
            const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

            if (isNearBottom) {
                if (distanceFromBottom > HIDE_THRESHOLD) {
                    setIsNearBottom(false);
                }
            } else {
                if (distanceFromBottom < SHOW_THRESHOLD) {
                    setIsNearBottom(true);
                }
            }
        }, 50); 
    }, [isNearBottom]);

    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, []);

    useEffect(() => {
        const scrollContainer = scrollRef.current;
        if (scrollContainer) {
             setTimeout(() => {
                scrollContainer.scrollTo({
                    top: scrollContainer.scrollHeight,
                    behavior: 'smooth'
                });
            }, 100);
        }
    }, [messages.length]);

    const handleSendMessage = async () => {
        if (inputValue.trim() && !isStepping && typeof performStep === 'function') {
            const textToSend = inputValue.trim();
            setInputValue('');
            try {
                await performStep({ user_message: textToSend });
            } catch (error) {
                console.error("发送消息失败:", error);
                setInputValue(textToSend);
            }
        }
    };
    
    return (
        <Box sx={{ position: 'relative', width: '100%', height: '100%', bgcolor: '#121212', overflow: 'hidden' }}>
            <Box
                ref={scrollRef}
                onScroll={handleScroll}
                sx={{
                    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                    overflowY: 'auto',
                    '&::-webkit-scrollbar': { display: 'none' },
                    scrollbarWidth: 'none', '-ms-overflow-style': 'none',
                }}
            >
                <Box sx={{
                    maxWidth: '1000px', width: '100%', mx: 'auto',
                    pt: '8vh', px: 3,
                    paddingBottom: isNearBottom ? '120px' : '20px',
                    transition: 'padding-bottom 0.5s cubic-bezier(0.23, 1, 0.32, 1)'
                }}>
                    {messages.map((msg, index) => <Message key={msg.id || index} msg={msg} />)}
                    {isStepping && (
                        <Box sx={{ display: 'flex', justifyContent: 'flex-start', my: 2 }}>
                           <CircularProgress size={24} />
                        </Box>
                    )}
                </Box>
            </Box>

            <Box
                sx={{
                    position: 'absolute', bottom: 30, left: '50%',
                    width: 'clamp(300px, 90%, 1000px)',
                    display: 'flex', alignItems: 'center', p: 1,
                    borderRadius: '20px', backgroundColor: 'rgba(44, 44, 46, 0.25)',
                    backdropFilter: 'blur(5px) saturate(200%)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.15)', zIndex: 10,
                    opacity: isNearBottom ? 1 : 0,
                    transform: isNearBottom ? 'translate(-50%, 0)' : 'translate(-50%, 150%)',
                    transition: 'transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.3s linear',
                }}
            >
                 <TextField
                    fullWidth
                    multiline
                    maxRows={4}
                    variant="standard"
                    placeholder="你想做什么？"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    disabled={isStepping}
                    onKeyPress={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSendMessage();
                        }
                    }}
                    InputProps={{
                        disableUnderline: true,
                        sx: { color: '#EAEAEF', fontSize: '1.05rem', padding: '10px 14px' }
                    }}
                />
                <IconButton
                    color="primary"
                    onClick={handleSendMessage}
                    disabled={!inputValue.trim() || isStepping}
                    sx={{ bgcolor: 'rgba(0, 0, 0, 0.15)', '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.25)' }, ml: 1, }}
                >
                    {isStepping ? <CircularProgress size={24} color="inherit" /> : <SendRoundedIcon />}
                </IconButton>
            </Box>
        </Box>
    );
}