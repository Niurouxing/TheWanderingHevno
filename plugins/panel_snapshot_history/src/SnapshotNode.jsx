// plugins/panel_snapshot_history/src/SnapshotNode.jsx
import React from 'react';
import { Box, Typography, IconButton, Tooltip, useTheme } from '@mui/material';
import RadioButtonCheckedIcon from '@mui/icons-material/RadioButtonChecked';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';

const getSnapshotSummary = (snapshot) => {
    const input = snapshot.triggering_input?.user_message;
    if (input) {
        return `“${input.slice(0, 50)}${input.length > 50 ? '...' : ''}”`;
    }
    return '初始状态或系统事件';
};

const CONNECTOR_COLOR = 'rgba(255, 255, 255, 0.2)';
const ICON_SIZE = 24;
const LEVEL_INDENT = 28;

export const SnapshotNode = React.memo(({ node, headSnapshotId, onRevert, onDelete, isLast }) => {
    const theme = useTheme();
    const [isHovered, setIsHovered] = React.useState(false);
    
    const isHead = node.id === headSnapshotId;
    const summary = getSnapshotSummary(node);
    const timestamp = new Date(node.created_at).toLocaleString();

    return (
        <Box sx={{ position: 'relative', pl: `${LEVEL_INDENT}px`, pt: '4px', pb: '4px' }}>
            {/* 垂直连接线 (连接兄弟节点) */}
            {!isLast && (
                <Box sx={{
                    position: 'absolute',
                    top: ICON_SIZE / 2,
                    left: (LEVEL_INDENT - 16) / 2,
                    bottom: 0,
                    width: '2px',
                    bgcolor: CONNECTOR_COLOR,
                    transform: 'translateX(-50%)',
                }}/>
            )}
            
            <Box 
                sx={{ display: 'flex', alignItems: 'center', position: 'relative' }}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
            >
                {/* 水平连接线 (连接父节点) */}
                <Box sx={{
                    position: 'absolute',
                    top: '50%',
                    left: `-${(LEVEL_INDENT / 2) + 7}px`,
                    width: `${(LEVEL_INDENT / 2) - 1}px`,
                    height: '2px',
                    bgcolor: CONNECTOR_COLOR
                }}/>

                <Tooltip title={isHead ? "当前状态" : "点击切换到此状态"} placement="right">
                    <span>
                        <IconButton
                            size="small"
                            onClick={() => !isHead && onRevert(node.id)}
                            disabled={isHead}
                            sx={{
                                color: isHead ? theme.palette.primary.main : 'text.secondary',
                                '&:hover': {
                                    color: isHead ? theme.palette.primary.main : theme.palette.primary.light,
                                },
                            }}
                        >
                            {isHead ? <RadioButtonCheckedIcon /> : <RadioButtonUncheckedIcon />}
                        </IconButton>
                    </span>
                </Tooltip>
                <Box sx={{ ml: 1 }}>
                    <Typography variant="body2" sx={{ lineHeight: 1.2 }}>{summary}</Typography>
                    <Typography variant="caption" color="text.secondary">{timestamp}</Typography>
                </Box>
                
                {isHovered && !isHead && (
                    <Tooltip title="永久删除此快照及后续分支">
                        <IconButton 
                            size="small" 
                            onClick={() => onDelete(node.id)}
                            sx={{ 
                                ml: 'auto', 
                                color: 'error.light',
                                opacity: 0.7,
                                '&:hover': {
                                    opacity: 1
                                }
                            }}
                        >
                            <DeleteForeverIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                )}
            </Box>

            {node.children && node.children.length > 0 && (
                <Box sx={{ position: 'relative' }}>
                    {node.children.map((childNode, index) => (
                        <SnapshotNode 
                            key={childNode.id}
                            node={childNode}
                            headSnapshotId={headSnapshotId}
                            onRevert={onRevert}
                            onDelete={onDelete}
                            isLast={index === node.children.length - 1}
                        />
                    ))}
                </Box>
            )}
        </Box>
    );
});