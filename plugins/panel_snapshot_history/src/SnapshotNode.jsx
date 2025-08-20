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
const ROW_HEIGHT = 52;
const ICON_SIZE = 20;
const ICON_BUTTON_PADDING = 4;
const ICON_BUTTON_WIDTH = ICON_SIZE + 2 * ICON_BUTTON_PADDING;
const CENTER = Math.floor(ICON_BUTTON_WIDTH / 2) - 1;
const BRANCH_LINE_WIDTH = 33; 
const CHILD_INDENT = 5; 
const VERTICAL_OFFSET = 16; 

export const SnapshotNode = React.memo(({ node, headSnapshotId, onRevert, onDelete, isRoot = false, isBranchedChild = false }) => {
    const theme = useTheme();
    const [isHovered, setIsHovered] = React.useState(false);

    const isHead = node.id === headSnapshotId;
    const summary = getSnapshotSummary(node);
    const timestamp = new Date(node.created_at).toLocaleString();
    const hasChildren = node.children.length > 0;
    const hasBranchingChildren = node.children.length > 1;

    let totalChildrenHeight = 0;
    let trunkHeight = 0;
    if (hasChildren) {
        totalChildrenHeight = node.children.reduce((acc, child) => acc + child.subtreeHeight, 0);
        if (hasBranchingChildren) {
            const lastChild = node.children[node.children.length - 1];
            trunkHeight = totalChildrenHeight - lastChild.subtreeHeight + (ROW_HEIGHT / 2);
        }
    }

    return (
        <Box 
            sx={{ 
                position: 'relative', 
                minWidth: 'max-content' 
            }}
        >
            {/* Incoming connector */}
            {!isRoot && !isBranchedChild && (
                <Box sx={{
                    position: 'absolute',
                    top: 0,
                    left: VERTICAL_OFFSET,
                    height: ROW_HEIGHT / 2,
                    width: '2px',
                    bgcolor: CONNECTOR_COLOR,
                }} />
            )}

            {/* Outgoing stub connector if has children */}
            {hasChildren && (
                <Box sx={{
                    position: 'absolute',
                    top: ROW_HEIGHT / 2,
                    left: VERTICAL_OFFSET,
                    height: ROW_HEIGHT / 2,
                    width: '2px',
                    bgcolor: CONNECTOR_COLOR,
                }} />
            )}

            {/* Node content */}
            <Box 
                sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    height: `${ROW_HEIGHT}px` 
                }}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
            >
                <Tooltip title={isHead ? "当前状态" : "点击切换到此状态"} placement="right">
                    <span style={{ zIndex: 1, background: theme.palette.background.default, borderRadius: '50%' }}>
                        <IconButton
                            size="small"
                            onClick={() => !isHead && onRevert(node.id)}
                            disabled={isHead}
                            sx={{ color: isHead ? theme.palette.primary.main : 'text.secondary', '&:hover': { color: isHead ? theme.palette.primary.main : theme.palette.primary.light } }}
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
                    <Tooltip title="永久删除此快照">
                        <IconButton 
                            size="small" 
                            onClick={() => onDelete(node.id)}
                            sx={{ ml: 'auto', color: 'error.light', opacity: 0.7, '&:hover': { opacity: 1 }, pl: 2 }}
                        >
                            <DeleteForeverIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                )}
            </Box>

            {/* Children rendering */}
            {hasChildren && (
                <Box sx={{ position: 'relative' }}>
                    {/* Trunk for branching children */}
                    {hasBranchingChildren && (
                        <Box sx={{
                            position: 'absolute',
                            top: 0,
                            left: VERTICAL_OFFSET,
                            height: trunkHeight,
                            width: '2px',
                            bgcolor: CONNECTOR_COLOR,
                        }} />
                    )}

                    {(() => {
                        let currentOffset = 0;
                        return node.children.map((childNode) => {
                            const branchTop = currentOffset + (ROW_HEIGHT / 2);
                            const frag = (
                                <React.Fragment key={childNode.id}>
                                    {hasBranchingChildren && (
                                        <Box sx={{
                                            position: 'absolute',
                                            top: branchTop,
                                            left: VERTICAL_OFFSET,
                                            width: BRANCH_LINE_WIDTH,
                                            height: '2px',
                                            bgcolor: CONNECTOR_COLOR,
                                        }} />
                                    )}
                                    <Box sx={{ pl: hasBranchingChildren ? CHILD_INDENT : 0 }}>
                                        <SnapshotNode
                                            node={childNode}
                                            headSnapshotId={headSnapshotId}
                                            onRevert={onRevert}
                                            onDelete={onDelete}
                                            isRoot={false}
                                            isBranchedChild={hasBranchingChildren}
                                        />
                                    </Box>
                                </React.Fragment>
                            );
                            currentOffset += childNode.subtreeHeight;
                            return frag;
                        });
                    })()}
                </Box>
            )}
        </Box>
    );
});