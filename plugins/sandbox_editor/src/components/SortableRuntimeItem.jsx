// plugins/sandbox_editor/src/components/SortableRuntimeItem.jsx
import React from 'react';
import { ListItem, ListItemIcon, ListItemText, IconButton, Chip } from '@mui/material';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export function SortableRuntimeItem({ id, run, onEdit, onDelete, children }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 1 : 0,
    position: 'relative',
    backgroundColor: isDragging ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
    display: 'flex',
    flexDirection: 'column'
  };

  return (
    <div ref={setNodeRef} style={style}>
      <ListItem
        sx={{ pl: 2, borderBottom: '1px dashed rgba(255, 255, 255, 0.08)', width: '100%' }}
        secondaryAction={
            <>
                <IconButton size="small" edge="end" aria-label="edit" onClick={onEdit}>
                    <EditIcon fontSize="small" />
                </IconButton>
                <IconButton size="small" edge="end" aria-label="delete" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
                    <DeleteIcon fontSize="small" />
                </IconButton>
            </>
        }
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab', minWidth: 32 }}>
          <DragIndicatorIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText 
            primary={<Chip label={run.runtime || 'Untitled'} size="small" variant="outlined" />} 
            secondary={run.config?.as ? `as: ${run.config.as}` : `Config keys: ${Object.keys(run.config || {}).length}`}
        />
      </ListItem>
      {children}
    </div>
  );
}