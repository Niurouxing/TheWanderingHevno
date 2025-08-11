// plugins/sandbox_editor/src/components/SortableMemoryEntryItem.jsx
import React from 'react';
import { ListItem, ListItemIcon, ListItemText, IconButton, Chip, Box } from '@mui/material';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DeleteIcon from '@mui/icons-material/Delete';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export function SortableMemoryEntryItem({ id, entry, expanded, onToggleExpand, onDelete, children }) {
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
    backgroundColor: isDragging ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
  };

  const contentPreview = entry.content ? `${entry.content.slice(0, 80)}...` : '无内容';

  return (
    <div ref={setNodeRef} style={style}>
      <ListItem
        button
        onClick={onToggleExpand}
        sx={{
          borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
          backgroundColor: 'transparent',
          '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.08)' }
        }}
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab' }}>
          <DragIndicatorIcon />
        </ListItemIcon>
        <ListItemIcon>
          {expanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
        </ListItemIcon>
        <ListItemText
          primary={contentPreview}
          secondary={
            <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
              <Chip label={entry.level || 'event'} size="small" variant="outlined" />
              {(entry.tags || []).map(tag => (
                <Chip key={tag} label={tag} size="small" />
              ))}
            </Box>
          }
          secondaryTypographyProps={{ component: 'div' }}
        />
        <IconButton onClick={(e) => { e.stopPropagation(); onDelete(); }}>
          <DeleteIcon />
        </IconButton>
      </ListItem>
      {children}
    </div>
  );
}