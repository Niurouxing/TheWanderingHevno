// plugins/sandbox_editor/src/components/SortableStreamItem.jsx
import React from 'react';
import { ListItem, ListItemIcon, ListItemText, IconButton } from '@mui/material';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DeleteIcon from '@mui/icons-material/Delete';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export function SortableStreamItem({ id, stream, expanded, onToggleExpand, onDelete, children }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 1 : 0,
    position: 'relative',
    backgroundColor: isDragging ? 'rgba(255, 255, 255, 0.1)' : 'transparent'
  };

  return (
    <div ref={setNodeRef} style={style}>
      <ListItem
        button
        onClick={onToggleExpand}
        sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab' }}>
          <DragIndicatorIcon />
        </ListItemIcon>
        <ListItemIcon>
          {expanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
        </ListItemIcon>
        <ListItemText primary={stream.name} secondary={`条目数量: ${stream.data.entries?.length || 0}`} />
        <IconButton onClick={(e) => { e.stopPropagation(); onDelete(); }}>
          <DeleteIcon />
        </IconButton>
      </ListItem>
      {children}
    </div>
  );
}