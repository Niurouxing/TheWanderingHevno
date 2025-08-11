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
    listStyleType: 'none',
  };

  const contentPreview = entry.content ? `${entry.content.slice(0, 80)}...` : '无内容';

  return (
    <li ref={setNodeRef} style={style}>
      <ListItem
        component="div"
        button
        onClick={onToggleExpand}
        sx={{
          // --- [美术修复] ---
          // 1. 强制覆盖 button 属性带来的默认“灰色”背景，使其透明
          backgroundColor: 'transparent', 
          // 2. 明确定义鼠标悬停时的背景色，以保持良好的交互反馈
          '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
          },
          // --- [修复结束] ---
          
          // 保留原有样式
          borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
          borderLeft: `3px solid ${expanded ? '#90caf9' : 'transparent'}`,
          paddingLeft: '10px',
        }}
        secondaryAction={
          <IconButton edge="end" title="删除此条目" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
            <DeleteIcon />
          </IconButton>
        }
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab', minWidth: 'auto', mr: 1 }}>
          <DragIndicatorIcon />
        </ListItemIcon>
        <ListItemIcon sx={{ minWidth: 'auto', mr: 1 }}>
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
      </ListItem>
      {children}
    </li>
  );
}