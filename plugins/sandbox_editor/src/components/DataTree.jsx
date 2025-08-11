import React, { useState } from 'react';
import { List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton, Typography, Box } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import EditIcon from '@mui/icons-material/Edit';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline'; // 新增图标
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import HistoryIcon from '@mui/icons-material/History';
import { isObject, isArray } from '../utils/constants';

const HEVNO_TYPE_EDITORS = {
  'hevno/codex': { icon: <AutoStoriesIcon />, tooltip: 'Edit Codex' },
  'hevno/graph': { icon: <AccountTreeIcon />, tooltip: 'Edit Graph' },
  'hevno/memoria': { icon: <HistoryIcon />, tooltip: 'Edit Memoria' },
};

// --- [修改] 添加 onAdd prop ---
export function DataTree({ data, path = '', onEdit, onAdd }) {
  const [expanded, setExpanded] = useState({});
  const toggleExpand = (key) => { setExpanded((prev) => ({ ...prev, [key]: !prev[key] })); };

  if (!data) return null;

  return (
    <List disablePadding sx={{ pl: path.split('/').length > 1 ? 2 : 0 }}>
      {Object.entries(data).map(([key, value]) => {
        if (key === '__hevno_type__') return null;

        const currentPath = path ? `${path}/${key}` : key;
        const isExpandable = isObject(value) || isArray(value);
        
        const hevnoType = isObject(value) ? value.__hevno_type__ : undefined;
        const editorInfo = hevnoType ? HEVNO_TYPE_EDITORS[hevnoType] : null;

        // --- [修改] 定义是否显示通用添加按钮的条件 ---
        const showAddButton = isObject(value) && !isArray(value) && !hevnoType;

        return (
          <React.Fragment key={currentPath}>
            <ListItem
              disablePadding
              secondaryAction={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {/* --- [修改] 条件性地渲染添加按钮 --- */}
                  {showAddButton && (
                    <IconButton edge="end" onClick={() => onAdd(currentPath, Object.keys(value))} title="Add item to this object">
                        <AddCircleOutlineIcon fontSize="small" />
                    </IconButton>
                  )}
                  <IconButton edge="end" onClick={() => onEdit(currentPath, value)} title={editorInfo ? editorInfo.tooltip : 'Edit value'}>
                    <EditIcon />
                  </IconButton>
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
                {/* --- [修改] 向下传递 onAdd prop --- */}
                <DataTree data={value} path={currentPath} onEdit={onEdit} onAdd={onAdd} />
              </Collapse>
            )}
          </React.Fragment>
        );
      })}
    </List>
  );
}