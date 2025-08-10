// plugins/sandbox_editor/src/components/SortableRuntimeItem.jsx
// 类似于 SortableNodeItem，但为 runtime item 定制 (二级)
import React from 'react';
import { ListItem, ListItemIcon, ListItemText, IconButton } from '@mui/material';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DeleteIcon from '@mui/icons-material/Delete';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export function SortableRuntimeItem({ id, run, expanded, onToggleExpand, onDelete, children }) {
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
        onClick={() => onToggleExpand(id)}
        sx={{ pl: 4, borderBottom: '1px dashed rgba(255, 255, 255, 0.08)' }}
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab', minWidth: 32 }}>
          <DragIndicatorIcon fontSize="small" />
        </ListItemIcon>
        <ListItemIcon sx={{ minWidth: 32 }}>
          {expanded ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
        </ListItemIcon>
        <ListItemText primary={run.runtime || 'Untitled Runtime'} secondary="Config keys: ..." />
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); onDelete(id); }}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      </ListItem>
      {children}
    </div>
  );
}