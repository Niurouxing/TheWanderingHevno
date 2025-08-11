// plugins/sandbox_editor/src/components/SortableEntryItem.jsx
import React from 'react';
import { ListItem, ListItemIcon, ListItemText, Switch, IconButton } from '@mui/material';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DeleteIcon from '@mui/icons-material/Delete';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export function SortableEntryItem({ id, entry, expanded, onToggleExpand, onToggleEnabled, onDelete, children }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

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
        onClick={() => onToggleExpand(entry.id)}
        sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab' }}>
          <DragIndicatorIcon />
        </ListItemIcon>
        <ListItemIcon>
          {expanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
        </ListItemIcon>
        <ListItemText primary={entry.id} secondary={`Priority: ${entry.priority}`} />
        <Switch
          checked={entry.is_enabled}
          onChange={(e) => onToggleEnabled(entry.id, e.target.checked)}
          onClick={(e) => e.stopPropagation()}
        />
        <IconButton onClick={(e) => { e.stopPropagation(); onDelete(entry.id); }}>
          <DeleteIcon />
        </IconButton>
      </ListItem>
      {children}
    </div>
  );
}