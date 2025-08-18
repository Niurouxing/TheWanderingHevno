import React, { useState } from 'react';
import { List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton, Typography, Box } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import EditIcon from '@mui/icons-material/Edit';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import HistoryIcon from '@mui/icons-material/History';
// --- [新增] 导入新图标 ---
import DriveFileRenameOutlineIcon from '@mui/icons-material/DriveFileRenameOutline';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';

import { isObject, isArray } from '../utils/constants';

const HEVNO_TYPE_EDITORS = {
  'hevno/codex': { icon: <AutoStoriesIcon />, tooltip: '编辑 Codex' },
  'hevno/graph': { icon: <AccountTreeIcon />, tooltip: '编辑 Graph' },
  'hevno/memoria': { icon: <HistoryIcon />, tooltip: '编辑 Memoria' },
};

// --- [修改] 添加 onRename 和 onDelete props ---
export function DataTree({ data, path = '', onEdit, onAdd, onRename, onDelete }) {
  const [expanded, setExpanded] = useState({});
  const toggleExpand = (key) => { setExpanded((prev) => ({ ...prev, [key]: !prev[key] })); };

  if (!data) return null;

  // --- [新增] 获取当前层级的所有键，用于重命名时的冲突检查 ---
  const siblingKeys = Object.keys(data);

  return (
    <List disablePadding sx={{ pl: path.split('/').length > 1 ? 2 : 0 }}>
      {Object.entries(data).map(([key, value]) => {
        if (key === '__hevno_type__') return null;

        const currentPath = path ? `${path}/${key}` : key;
        const isExpandable = isObject(value) || isArray(value);
        
        const hevnoType = isObject(value) ? value.__hevno_type__ : undefined;
        const editorInfo = hevnoType ? HEVNO_TYPE_EDITORS[hevnoType] : null;

        // --- 定义是否显示通用添加按钮的条件 ---
        const showAddButton = isObject(value) && !isArray(value) && !hevnoType;
        // --- [新增] 仅当父级是对象时（即有path），才允许重命名和删除 ---
        const allowModify = path !== '';

        return (
          <React.Fragment key={currentPath}>
            <ListItem
              disablePadding
              secondaryAction={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {showAddButton && (
                    <IconButton edge="end" onClick={() => onAdd(currentPath, Object.keys(value))} title="在此对象中添加项">
                        <AddCircleOutlineIcon fontSize="small" />
                    </IconButton>
                  )}
                  {/* --- [修改] 添加重命名和删除按钮 --- */}
                  {allowModify && (
                     <IconButton edge="end" onClick={() => onRename(currentPath, value, siblingKeys)} title="重命名">
                        <DriveFileRenameOutlineIcon fontSize="small" />
                    </IconButton>
                  )}
                  <IconButton edge="end" onClick={() => onEdit(currentPath, value)} title={editorInfo ? editorInfo.tooltip : '编辑值'}>
                    <EditIcon />
                  </IconButton>
                   {allowModify && (
                     <IconButton edge="end" onClick={() => onDelete(currentPath)} title="删除" sx={{color: 'error.main'}}>
                        <DeleteForeverIcon fontSize="small" />
                    </IconButton>
                  )}
                </Box>
              }
            >
              <ListItemIcon sx={{minWidth: '40px'}}>
                {editorInfo ? editorInfo.icon : (isExpandable ? <FolderIcon /> : <DescriptionIcon />)}
              </ListItemIcon>
              <ListItemText 
                primary={key} 
                secondary={
                    editorInfo 
                    ? `Type: ${hevnoType.split('/')[1]}`
                    : !isExpandable 
                        ? (typeof value === 'string' ? value.slice(0, 50) + (value.length > 50 ? '...' : '') : JSON.stringify(value)) 
                        : `${isArray(value) ? 'Array' : 'Object'} (${Object.keys(value).length} items)`
                }
                onClick={isExpandable && !editorInfo ? () => toggleExpand(currentPath) : undefined}
                sx={{ cursor: (isExpandable && !editorInfo) ? 'pointer' : 'default' }}
              />
              {isExpandable && !editorInfo && (
                <IconButton size="small" onClick={() => toggleExpand(currentPath)}>
                  {expanded[currentPath] ? <ExpandMoreIcon /> : <ChevronRightIcon />}
                </IconButton>
              )}
            </ListItem>
            {isExpandable && !editorInfo && (
              <Collapse in={expanded[currentPath]} timeout="auto" unmountOnExit>
                {/* --- [修改] 递归传递新的 props --- */}
                <DataTree data={value} path={currentPath} onEdit={onEdit} onAdd={onAdd} onRename={onRename} onDelete={onDelete} />
              </Collapse>
            )}
          </React.Fragment>
        );
      })}
    </List>
  );
}