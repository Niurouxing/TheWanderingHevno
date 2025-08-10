// frontend/DataTree.jsx (修正后)

import React, { useState } from 'react';
import { List, ListItem, ListItemButton, ListItemIcon, ListItemText, Collapse, IconButton } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import EditIcon from '@mui/icons-material/Edit';

// 导入更具体的图标
import AutoStoriesIcon from '@mui/icons-material/AutoStories'; // For Codex
import AccountTreeIcon from '@mui/icons-material/AccountTree'; // For Graph
import HistoryIcon from '@mui/icons-material/History'; // For Memoria

import { isObject, isArray } from '../utils/constants';

// --- 核心修改：更新类型映射 ---
// 类型现在是单数形式，代表可编辑的单个实体
const HEVNO_TYPE_EDITORS = {
  'hevno/codex': { icon: <AutoStoriesIcon />, tooltip: 'Edit Codex' },
  'hevno/graph': { icon: <AccountTreeIcon />, tooltip: 'Edit Graph' },
  'hevno/memoria': { icon: <HistoryIcon />, tooltip: 'Edit Memoria' }, 
};

export function DataTree({ data, path = '', onEdit, activeScope }) {
  const [expanded, setExpanded] = useState({});
  const toggleExpand = (key) => { setExpanded((prev) => ({ ...prev, [key]: !prev[key] })); };

  if (!data) return null;

  return (
    <List disablePadding sx={{ pl: path ? 2 : 0 }}>
      {Object.entries(data).map(([key, value]) => {
        // 忽略我们自己的元数据键
        if (key === '__hevno_type__') return null;

        const currentPath = path ? `${path}.${key}` : key;
        const isExpandable = isObject(value) || isArray(value);
        
        // --- 逻辑现在完美匹配 ---
        // 它会检查每个子对象 (比如 `main` 图或 `npc_status` codex) 是否有类型标记
        const hevnoType = isObject(value) ? value.__hevno_type__ : undefined;
        const editorInfo = hevnoType ? HEVNO_TYPE_EDITORS[hevnoType] : null;

        return (
          <React.Fragment key={currentPath}>
            <ListItem 
              secondaryAction={
                editorInfo ? (
                  <IconButton edge="end" onClick={() => onEdit(currentPath, value, key, activeScope)} title={editorInfo.tooltip}>
                    <EditIcon />
                  </IconButton>
                ) : null
              }
            >
              <ListItemIcon>
                {/* 使用专用图标 */}
                {editorInfo ? editorInfo.icon : (isExpandable ? <FolderIcon /> : <DescriptionIcon />)}
              </ListItemIcon>
              <ListItemText 
                primary={key} 
                secondary={
                    editorInfo 
                    ? `Type: ${hevnoType.split('/')[1]}` // 显示更友好的类型名，如 'graph'
                    : !isExpandable 
                        ? (typeof value === 'string' ? value.slice(0, 50) + (value.length > 50 ? '...' : '') : JSON.stringify(value)) 
                        : `${isArray(value) ? 'Array' : 'Object'} (${Object.keys(value).length} items)`
                }
                // 如果是特殊类型，点击文本本身不应该有任何效果
                onClick={isExpandable && !editorInfo ? () => toggleExpand(currentPath) : undefined}
                sx={{ cursor: (isExpandable && !editorInfo) ? 'pointer' : 'default' }}
              />
              {/* 仅在可展开且非特殊类型时显示折叠按钮 */}
              {isExpandable && !editorInfo && (
                <IconButton size="small" onClick={() => toggleExpand(currentPath)}>
                  {expanded[currentPath] ? <ExpandMoreIcon /> : <ChevronRightIcon />}
                </IconButton>
              )}
            </ListItem>
            {/* 仅在可展开且非特殊类型时渲染子树 */}
            {isExpandable && !editorInfo && (
              <Collapse in={expanded[currentPath]} timeout="auto" unmountOnExit>
                <DataTree data={value} path={currentPath} onEdit={onEdit} activeScope={activeScope} />
              </Collapse>
            )}
          </React.Fragment>
        );
      })}
    </List>
  );
}