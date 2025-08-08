// plugins/core_goliath/src/components/editor/HistoryTimeline.jsx

import React from 'react';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import ListSubheader from '@mui/material/ListSubheader';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

export default function HistoryTimeline({ history, selectedSnapshotId, onSelectSnapshot, headSnapshotId }) {
    
    // 现实中，需要一个算法来处理分支并正确排序。
    // 这里我们先简单地倒序显示。
    const sortedHistory = [...(history || [])].reverse();

    if (!history || history.length === 0) {
        return (
            <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography color="text.secondary">No history found for this sandbox.</Typography>
            </Box>
        );
    }
    
    return (
        <List dense subheader={<ListSubheader>History</ListSubheader>}>
            {sortedHistory.map((snapshot, index) => (
                 <ListItem
                    key={snapshot.id}
                    disablePadding
                    secondaryAction={
                        snapshot.id === headSnapshotId ? <Chip label="HEAD" size="small" color="primary" /> : null
                    }
                >
                    <ListItemButton
                        selected={snapshot.id === selectedSnapshotId}
                        onClick={() => onSelectSnapshot(snapshot.id)}
                    >
                        <ListItemText
                            primary={`Snapshot #${history.length - index}`}
                            secondary={new Date(snapshot.created_at).toLocaleString()}
                        />
                    </ListItemButton>
                </ListItem>
            ))}
        </List>
    );
}