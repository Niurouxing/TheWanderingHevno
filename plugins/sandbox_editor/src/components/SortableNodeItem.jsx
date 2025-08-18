// plugins/sandbox_editor/src/components/SortableNodeItem.jsx
// 类似于 SortableEntryItem，但为 node 定制
import React from 'react';
import { ListItem, ListItemIcon, ListItemText, IconButton, Box } from '@mui/material';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DeleteIcon from '@mui/icons-material/Delete';
import IosShareIcon from '@mui/icons-material/IosShare'; // 使用 "export" 图标
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// [修改] 添加 onExport prop
export function SortableNodeItem({ id, node, expanded, onToggleExpand, onDelete, onExport, children }) {
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
        onClick={onToggleExpand} // 这里从 onToggleExpand(node.id) 改为 onToggleExpand()，让父组件处理ID
        sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}
        secondaryAction={
          <Box>
            {/* [新增] 导出按钮 */}
            <IconButton edge="end" title="导出此节点" onClick={(e) => { e.stopPropagation(); onExport(); }}>
              <IosShareIcon />
            </IconButton>
            <IconButton edge="end" title="删除此节点" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
              <DeleteIcon />
            </IconButton>
          </Box>
        }
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab' }}>
          <DragIndicatorIcon />
        </ListItemIcon>
        <ListItemIcon>
          {expanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
        </ListItemIcon>
        <ListItemText primary={node.id} secondary={`Runs: ${node.run?.length || 0}`} />
      </ListItem>
      {children}
    </div>
  );
}