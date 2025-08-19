import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Box, TextField, IconButton, Fade, Typography } from '@mui/material';
import SendRoundedIcon from '@mui/icons-material/SendRounded';

// 假数据保持不变
const initialMessages = [
    { type: 'system', text: "You wake up in the cramped backstage of the Apollo theater, the stale air thick with dust and mildew. The resistance has stashed you here for the past few hours while they scramble to plan an extraction. Your body aches, exhaustion weighing heavy from the night's evasion through the ruined streets." },
    { type: 'llm', sender: 'Red', text: "\"NN, wake up,\" Red says, kneeling beside you. Their augmented face mask flickers, revealing just enough of their features—pale skin and deep-set eyes—to make them seem real, human. \"You don't have much time.\" Their words are clipped, urgent. \"Stryker's close.\" You push yourself up, shoulders groaning as the exosuit's servos adjust to your movement. The dim emergency lights flicker above, casting long shadows over the cluttered backstage. Stripped-down bots—some missing limbs, others with exposed wiring—are stacked in the corners like discarded toys." },
    { type: 'llm', sender: 'Red', text: "\"They sent two squads to sweep the perimeter,\" Red continues, checking the readout on their augmented forearm. \"One ground unit, one aerial. They're methodical.\" Their gloved fingers tap rapidly against the exposed pipes of the old theater wall. \"You're fast, but not fast enough to outrun a drone swarm.\" A muscle twitches in their jaw. \"We need to get you underground.\"" },
    { type: 'action', text: "You trigger some emergency." },
    { type: 'user', text: "Your fingers dance across the neuralink interface, and the nearest inactive bot—a headless torso with exposed wiring—jerks to life with a sharp hiss of pneumatics. It shambles toward the wall, stumbling over the debris as you override its basic systems. Then you yank open a hatch you'd noticed earlier—a maintenance shaft that runs into the deeper levels of the theater." },
    { type: 'system', text: "The bot stumbles down into the darkness, and you wait. Seconds later, a distant explosion rumbles through the floor—controlled detonation of the old gas lines, triggering the emergency sprinkler system. The backstage erupts into chaos as the overhead pipes burst, drenching everything in a cold, hissing shower." }
];

// 消息渲染组件 (无变化)
const Message = React.memo(({ msg }) => {
    const getMessageStyle = () => {
        switch (msg.type) {
            case 'llm': return { fontStyle: 'normal', color: 'text.primary' };
            case 'user': return { fontStyle: 'normal', color: 'text.primary' };
            case 'system': return { fontStyle: 'italic', color: 'text.secondary' };
            case 'action': return { fontStyle: 'italic', color: 'primary.light', borderLeft: '2px solid', borderColor: 'primary.main', pl: 2 };
            default: return {};
        }
    };
    return (
        <Box sx={{ mb: 2.5 }}>
            <Typography variant="body1" sx={{ fontFamily: "'Georgia', serif", lineHeight: 1.7, ...getMessageStyle() }}>
                {msg.text}
            </Typography>
        </Box>
    );
});


export function ConversationCanvas() {
    const [messages, setMessages] = useState(initialMessages);
    const [inputValue, setInputValue] = useState('');
    const [isAtBottom, setIsAtBottom] = useState(true);
    const scrollRef = useRef(null);

    useEffect(() => {
        const scrollContainer = scrollRef.current;
        if (scrollContainer && isAtBottom) { // 只在用户位于底部时才自动滚动
            scrollContainer.scrollTo({
                top: scrollContainer.scrollHeight,
                behavior: 'smooth'
            });
        }
    }, [messages, isAtBottom]);
    
    const handleScroll = useCallback(() => {
        const container = scrollRef.current;
        if (container) {
            const { scrollTop, scrollHeight, clientHeight } = container;
            const atBottom = scrollHeight - scrollTop - clientHeight < 5;
            setIsAtBottom(atBottom);
        }
    }, []);

    const handleSendMessage = () => {
        if (inputValue.trim()) {
            setIsAtBottom(true); // 发送消息前，假定用户希望看到最新消息
            setMessages(prev => [...prev, { type: 'user', text: inputValue.trim() }]);
            setInputValue('');
            
            setTimeout(() => {
                setMessages(prev => [...prev, { type: 'llm', sender: 'Red', text: "Good thinking. That explosion will draw their attention. Now move, quickly! Down the shaft. I'll cover our tracks up here and meet you at the rendezvous point." }]);
            }, 1500);
        }
    };
    
    return (
        // [关键改动 1] 最外层容器现在是定位上下文 (position: relative)
        <Box sx={{ position: 'relative', width: '100%', height: '100%', bgcolor: '#121212', overflow: 'hidden' }}>
            
            {/* [关键改动 2] 滚动区域使用绝对定位，强制其尺寸与父容器完全一致 */}
            {/* 这创建了一个独立的滚动层，不会影响外部布局 */}
            <Box
                ref={scrollRef}
                onScroll={handleScroll}
                sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    overflowY: 'auto',
                    // 隐藏滚动条样式
                    '&::-webkit-scrollbar': { display: 'none' },
                    scrollbarWidth: 'none',
                    '-ms-overflow-style': 'none',
                }}
            >
                {/* 内容容器现在位于这个绝对定位的滚动层内部 */}
                <Box sx={{
                    maxWidth: '720px',
                    mx: 'auto',
                    py: '8vh',
                    px: 3,
                }}>
                    {messages.map((msg, index) => <Message key={index} msg={msg} />)}
                </Box>
                {/* 占位符确保最后一条消息不被输入框遮挡 */}
                <Box sx={{ height: '120px', flexShrink: 0 }} />
            </Box>

            {/* [无变化] 浮动输入栏仍然绝对定位于最外层容器，浮动在滚动层之上 */}
            <Fade in={isAtBottom} timeout={400}>
                <Box
                    sx={{
                        position: 'absolute',
                        bottom: 30,
                        left: '50%',
                        transform: 'translateX(-50%)',
                        width: 'clamp(300px, 90%, 720px)',
                        display: 'flex',
                        alignItems: 'center',
                        p: 1,
                        borderRadius: '12px',
                        backgroundColor: 'rgba(28, 28, 30, 0.65)',
                        backdropFilter: 'blur(12px) saturate(180%)',
                        boxShadow: '0px 8px 32px rgba(0, 0, 0, 0.3)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        zIndex: 10, // 确保在滚动内容之上
                    }}
                >
                    <TextField
                        fullWidth
                        multiline
                        maxRows={4}
                        variant="standard"
                        placeholder="Describe your action..."
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSendMessage();
                            }
                        }}
                        sx={{
                            '& .MuiInputBase-root': {
                                color: '#EAEAEF',
                                padding: '8px 12px',
                            },
                        }}
                        InputProps={{
                            disableUnderline: true,
                        }}
                    />
                    <IconButton
                        color="primary"
                        onClick={handleSendMessage}
                        disabled={!inputValue.trim()}
                        sx={{
                            bgcolor: 'rgba(255,255,255,0.1)',
                            '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' },
                            ml: 1,
                        }}
                    >
                        <SendRoundedIcon />
                    </IconButton>
                </Box>
            </Fade>
        </Box>
    );
}