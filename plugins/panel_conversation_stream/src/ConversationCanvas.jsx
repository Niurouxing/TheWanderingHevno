// plugins/panel_conversation_stream/src/ConversationCanvas.jsx
import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, TextField, GlobalStyles } from '@mui/material';

// 1. 静态假数据，用于UI开发
const mockMessages = [
    { type: 'system', content: 'The Riordanverse is a world where multiple pantheons of gods are real and are now living in the modern world... somewhere. The gods tend to have the heroes adwareof each book series (their demigod children or magicians) go on quests, fight monsters, and save the world.' },
    { type: 'system', content: 'Where am I? You are at the edge of a dark forest, its twisted branches clawing at the midnight sky. The leaves whisper with the breath of unseen creatures, and the air carries the metallic scent of blood and something more primal—wet fur and old stone. Moonlight struggles to pierce the canopy, casting dappled shadows across the uneven ground.' },
    { type: 'system', content: 'To your left, an old dirt road winds through the trees, leading deeper into the wood. The packed earth shows signs of recent activity—hoofprints and deep indentations that suggest a heavy cart had passed this way. To your right, a narrow trail ascends a steep hillside, dotted with gnarled roots and exposed rocks.' },
    { type: 'user', content: 'You say "Is anyone here?"' },
    { type: 'model', content: 'The moment your words leave your mouth, the woods tense. Somewhere in the darkness, a twig snaps under unseen weight. A low, rasping chuckle echoes from the trees—neither wholly human nor entirely inhuman. "Oh, someone is here," a voice hisses, thick with malice. "The question is... do you want to be?" The voice is smooth yet scratchy, like parchment left too long in the elements. From the underbrush, a single pair of glowing red eyes emerges, burning like dying embers in the night. A figure steps forward—a man draped in tattered robes, his skin mottled and pale. ⚠️' },
];

// 2. 为滚动条和背景添加全局样式
const customScrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    border: 1px solid rgba(0, 0, 0, 0.1);
  }
  /* 为了让毛玻璃效果可见，我们需要确保其下的元素（body, #root）有内容 */
  body, #root, #app {
      background: #111; /* fallback */
      background-image: linear-gradient(135deg, #2a2d34 0%, #1a1c20 100%);
  }
`;

export function ConversationCanvas() {
    const [messages] = useState(mockMessages);
    const [isInputVisible, setInputVisible] = useState(false);
    const scrollContainerRef = useRef(null);
    const lastScrollDirection = useRef('down'); // 用于检测滚动方向

    // 3. 自动滚动到最新消息的逻辑
    useEffect(() => {
        const container = scrollContainerRef.current;
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }, [messages]);

    // 4. 自动隐藏/显示输入栏的核心逻辑
    useEffect(() => {
        const container = scrollContainerRef.current;
        if (!container) return;
        
        const handleScroll = () => {
             // 如果用户向上滚动，立即隐藏输入栏
            if (container.scrollTop < container.scrollHeight - container.clientHeight - 5) {
                setInputVisible(false);
            }
        };

        const handleWheel = (event) => {
            const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 1;
             // 如果在底部，并且滚轮向下，则显示输入栏
            if (isAtBottom && event.deltaY > 0) {
                setInputVisible(true);
            }
        };

        container.addEventListener('scroll', handleScroll);
        container.addEventListener('wheel', handleWheel);

        return () => {
            container.removeEventListener('scroll', handleScroll);
            container.removeEventListener('wheel', handleWheel);
        };
    }, []);

    const glassEffectSx = {
        backgroundColor: 'rgba(28, 31, 34, 0.65)',
        backdropFilter: 'blur(12px) saturate(150%)',
        boxShadow: '0 0 0 0.5px rgba(0,0,0,0.3)',
    };
    
    return (
        <>
            <GlobalStyles styles={customScrollbarStyles} />
            <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
                
                {/* 5. 消息展示区域 */}
                <Box
                    ref={scrollContainerRef}
                    className="custom-scrollbar"
                    sx={{
                        flexGrow: 1,
                        overflowY: 'auto',
                        p: { xs: 2, sm: 3, md: 4 },
                        transition: 'padding-bottom 0.3s ease-in-out',
                        pb: isInputVisible ? '120px' : { xs: 2, sm: 3, md: 4 } // 为滑出的输入栏留出空间
                    }}
                >
                    <Box sx={{ maxWidth: '720px', mx: 'auto' }}>
                        {messages.map((msg, index) => (
                            <Box key={index} sx={{ mb: 2.5 }}>
                                <Typography
                                    sx={{
                                        fontFamily: '"Georgia", serif',
                                        fontSize: '1.1rem',
                                        lineHeight: 1.7,
                                        color: msg.type === 'user' ? '#aebac3' : '#e6edf3',
                                        fontStyle: msg.type === 'user' ? 'italic' : 'normal',
                                        textAlign: msg.type === 'user' ? 'right' : 'left',
                                        whiteSpace: 'pre-wrap', // 保持文本格式
                                    }}
                                >
                                    {msg.type === 'user' && <Box component="span" sx={{ fontSize: '0.9em', color: '#7d8590' }}>You say </Box>}
                                    {msg.content}
                                </Typography>
                            </Box>
                        ))}
                    </Box>
                </Box>

                {/* 6. 自动隐藏的输入栏 */}
                <Box
                    sx={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        p: { xs: 1, sm: 2 },
                        transform: isInputVisible ? 'translateY(0)' : 'translateY(100%)',
                        opacity: isInputVisible ? 1 : 0,
                        transition: 'transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
                        pointerEvents: isInputVisible ? 'auto' : 'none',
                    }}
                >
                    <Box sx={{
                        ...glassEffectSx,
                        maxWidth: '760px',
                        mx: 'auto',
                        p: 1,
                        borderRadius: '16px',
                    }}>
                        <TextField
                            fullWidth
                            multiline
                            maxRows={5}
                            placeholder="What do you say?"
                            variant="standard"
                            InputProps={{
                                disableUnderline: true,
                                sx: {
                                    p: 1.5,
                                    color: '#e6edf3',
                                    fontFamily: '"Georgia", serif',
                                    fontSize: '1.1rem',
                                    '::placeholder': { color: '#7d8590' },
                                }
                            }}
                            autoFocus={isInputVisible} // 当显示时自动聚焦
                        />
                    </Box>
                </Box>
            </Box>
        </>
    );
}

export default ConversationCanvas;