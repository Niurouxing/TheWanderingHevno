import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Box, TextField, IconButton, Typography } from '@mui/material';
import SendRoundedIcon from '@mui/icons-material/SendRounded';

const initialMessages = [
    { type: 'system', text: "You wake up in the cramped backstage of the Apollo theater, the stale air thick with dust and mildew. The resistance has stashed you here for the past few hours while they scramble to plan an extraction. Your body aches, exhaustion weighing heavy from the night's evasion through the ruined streets." },
    { type: 'llm', sender: 'Red', text: "\"NN, wake up,\" Red says, kneeling beside you. Their augmented face mask flickers, revealing just enough of their features—pale skin and deep-set eyes—to make them seem real, human. \"You don't have much time.\" Their words are clipped, urgent. \"Stryker's close.\" You push yourself up, shoulders groaning as the exosuit's servos adjust to your movement. The dim emergency lights flicker above, casting long shadows over the cluttered backstage. Stripped-down bots—some missing limbs, others with exposed wiring—are stacked in the corners like discarded toys." },
    { type: 'llm', sender: 'Red', text: "\"They sent two squads to sweep the perimeter,\" Red continues, checking the readout on their augmented forearm. \"One ground unit, one aerial. They're methodical.\" Their gloved fingers tap rapidly against the exposed pipes of the old theater wall. \"You're fast, but not fast enough to outrun a drone swarm.\" A muscle twitches in their jaw. \"We need to get you underground.\"" },
    { type: 'action', text: "You trigger some emergency." },
    { type: 'user', text: "Your fingers dance across the neuralink interface, and the nearest inactive bot—a headless torso with exposed wiring—jerks to life with a sharp hiss of pneumatics. It shambles toward the wall, stumbling over the debris as you override its basic systems. Then you yank open a hatch you'd noticed earlier—a maintenance shaft that runs into the deeper levels of the theater." },
    { type: 'system', text: "You wake up in the cramped backstage of the Apollo theater, the stale air thick with dust and mildew. The resistance has stashed you here for the past few hours while they scramble to plan an extraction. Your body aches, exhaustion weighing heavy from the night's evasion through the ruined streets." },
    { type: 'llm', sender: 'Red', text: "\"NN, wake up,\" Red says, kneeling beside you. Their augmented face mask flickers, revealing just enough of their features—pale skin and deep-set eyes—to make them seem real, human. \"You don't have much time.\" Their words are clipped, urgent. \"Stryker's close.\" You push yourself up, shoulders groaning as the exosuit's servos adjust to your movement. The dim emergency lights flicker above, casting long shadows over the cluttered backstage. Stripped-down bots—some missing limbs, others with exposed wiring—are stacked in the corners like discarded toys." },
    { type: 'llm', sender: 'Red', text: "\"They sent two squads to sweep the perimeter,\" Red continues, checking the readout on their augmented forearm. \"One ground unit, one aerial. They're methodical.\" Their gloved fingers tap rapidly against the exposed pipes of the old theater wall. \"You're fast, but not fast enough to outrun a drone swarm.\" A muscle twitches in their jaw. \"We need to get you underground.\"" },
    { type: 'action', text: "You trigger some emergency." },
    { type: 'user', text: "Your fingers dance across the neuralink interface, and the nearest inactive bot—a headless torso with exposed wiring—jerks to life with a sharp hiss of pneumatics. It shambles toward the wall, stumbling over the debris as you override its basic systems. Then you yank open a hatch you'd noticed earlier—a maintenance shaft that runs into the deeper levels of the theater." },
    { type: 'system', text: "The bot stumbles down into the darkness, and you wait. Seconds later, a distant explosion-controlled detonation of the old gas lines, triggering the emergency sprinkler system. The backstage erupts into chaos as the overhead pipes burst, drenching everything in a cold, hissing shower." }
];

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

// 定义非对称阈值
const SHOW_THRESHOLD = 250; // 出现动画的触发距离
const HIDE_THRESHOLD = 100;  // 消失动画的触发距离

export function ConversationCanvas() {
    const [messages, setMessages] = useState(initialMessages);
    const [inputValue, setInputValue] = useState('');
    const [isNearBottom, setIsNearBottom] = useState(true);
    const scrollRef = useRef(null);
    const debounceTimerRef = useRef(null);

    // 实现防抖的滚动逻辑
    const handleScroll = useCallback(() => {
        const container = scrollRef.current;
        if (!container) return;

        // 清除之前的防抖计时器
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }

        // 设置新的防抖计时器
        debounceTimerRef.current = setTimeout(() => {
            const { scrollTop, scrollHeight, clientHeight } = container;
            const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

            if (isNearBottom) {
                // 如果当前是显示的，那么只有当滚动距离超过 HIDE_THRESHOLD 时才隐藏
                if (distanceFromBottom > HIDE_THRESHOLD) {
                    setIsNearBottom(false);
                }
            } else {
                // 如果当前是隐藏的，那么只有当滚动距离小于 SHOW_THRESHOLD 时才显示
                if (distanceFromBottom < SHOW_THRESHOLD) {
                    setIsNearBottom(true);
                }
            }
        }, 50); // 50ms 防抖延迟
    }, [isNearBottom]); // 依赖 isNearBottom 以获取最新的状态

    // 清理防抖计时器
    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, []);

    // 自动滚动到底部
    useEffect(() => {
        const scrollContainer = scrollRef.current;
        if (scrollContainer) {
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }
    }, [messages.length]);
    
    // 发送消息
    const handleSendMessage = () => {
        if (inputValue.trim()) {
            setMessages(prev => [...prev, { type: 'user', text: inputValue.trim() }]);
            setInputValue('');
            
            setTimeout(() => {
                setMessages(prev => [...prev, { type: 'llm', sender: 'Red', text: "Good thinking. That explosion will draw their attention. Now move, quickly! Down the shaft. I'll cover our tracks up here and meet you at the rendezvous point." }]);
            }, 1500);
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
                    {messages.map((msg, index) => <Message key={index} msg={msg} />)}
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
                    placeholder="What do you do?"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
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
                    disabled={!inputValue.trim()}
                    sx={{ bgcolor: 'rgba(0, 0, 0, 0.15)', '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.25)' }, ml: 1, }}
                >
                    <SendRoundedIcon />
                </IconButton>
            </Box>
        </Box>
    );
}