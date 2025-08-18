// plugins/sandbox_editor/src/components/DataTree.jsx
import React, { useState } from 'react';
import { List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton, Menu, MenuItem } from '@mui/material'; // [修改] 移除了 Box, Typography
import DescriptionIcon from '@mui/icons-material/Description';
import EditIcon from '@mui/icons-material/Edit';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import HistoryIcon from '@mui/icons-material/History';
import DriveFileRenameOutlineIcon from '@mui/icons-material/DriveFileRenameOutline';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import MoreVertIcon from '@mui/icons-material/MoreVert';
// [新增] 导入用于视觉指示的箭头图标
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';


import { isObject, isArray } from '../utils/constants';

const HEVNO_TYPE_EDITORS = {
  'hevno/codex': { icon: <AutoStoriesIcon />, tooltip: '编辑 Codex' },
  'hevno/graph': { icon: <AccountTreeIcon />, tooltip: '编辑 Graph' },
  'hevno/memoria': { icon: <HistoryIcon />, tooltip: '编辑 Memoria' },
};

export function DataTree({ data, path = '', onEdit, onAdd, onRename, onDelete }) {
  const [expanded, setExpanded] = useState({});
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [currentItem, setCurrentItem] = useState(null);

  const toggleExpand = (key) => { setExpanded((prev) => ({ ...prev, [key]: !prev[key] })); };

  const handleMenuOpen = (event, itemData) => {
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
    setCurrentItem(itemData);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setCurrentItem(null);
  };

  const handleMenuAction = (action) => {
    if (!currentItem) return;
    const { currentPath, value, siblingKeys } = currentItem;
    action(currentPath, value, siblingKeys);
    handleMenuClose();
  };

  if (!data) return null;
  const siblingKeys = Object.keys(data);

  return (
    <>
      <List disablePadding sx={{ pl: path.split('/').length > 1 ? 2 : 0 }}>
        {Object.entries(data).map(([key, value]) => {
          if (key === '__hevno_type__') return null;

          const currentPath = path ? `${path}/${key}` : key;
          const isExpandable = isObject(value) || isArray(value);
          const hevnoType = isObject(value) ? value.__hevno_type__ : undefined;
          const editorInfo = hevnoType ? HEVNO_TYPE_EDITORS[hevnoType] : undefined;
          
          return (
            <React.Fragment key={currentPath}>
              <ListItem
                // --- [核心修改 1/3] ---
                // 当条目可展开时，为其添加 button 属性和 onClick 事件处理器
                // 这使得整个条目行（除了右侧按钮）都可点击以进行展开/折叠
                button={isExpandable && !editorInfo}
                onClick={isExpandable && !editorInfo ? () => toggleExpand(currentPath) : undefined}
                disablePadding
                secondaryAction={
                  <IconButton 
                    edge="end" 
                    title="更多操作"
                    onClick={(e) => handleMenuOpen(e, { currentPath, value, siblingKeys })}
                  >
                    <MoreVertIcon />
                  </IconButton>
                }
              >
                <ListItemIcon sx={{minWidth: '40px'}}>
                  {/* --- [核心修改 2/3] ---
                      - 如果是可展开的对象，显示一个非交互的箭头作为视觉指示器。
                      - 否则，显示其对应的特殊图标或通用文件图标。
                  */}
                  { (isExpandable && !editorInfo) ? (
                      expanded[currentPath] ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />
                    ) : editorInfo ? editorInfo.icon : <DescriptionIcon />
                  }
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
                />
                {/* --- [核心修改 3/3] 独立的箭头 IconButton 已被完全移除 --- */}
              </ListItem>
              {isExpandable && !editorInfo && (
                <Collapse in={expanded[currentPath]} timeout="auto" unmountOnExit>
                  <DataTree data={value} path={currentPath} onEdit={onEdit} onAdd={onAdd} onRename={onRename} onDelete={onDelete} />
                </Collapse>
              )}
            </React.Fragment>
          );
        })}
      </List>
      
      {/* 上下文菜单组件保持不变 */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleMenuAction(onEdit)}>
          <ListItemIcon><EditIcon fontSize="small" /></ListItemIcon>
          <ListItemText>{currentItem && HEVNO_TYPE_EDITORS[currentItem.value?.__hevno_type__] ? '打开专用编辑器' : '编辑值'}</ListItemText>
        </MenuItem>
        {currentItem && isObject(currentItem.value) && !isArray(currentItem.value) && !currentItem.value.__hevno_type__ && (
          <MenuItem onClick={() => handleMenuAction((path, val) => onAdd(path, Object.keys(val)))}>
             <ListItemIcon><AddCircleOutlineIcon fontSize="small" /></ListItemIcon>
             <ListItemText>添加项</ListItemText>
          </MenuItem>
        )}
        {currentItem && path !== '' && (
             <MenuItem onClick={() => handleMenuAction(onRename)}>
                <ListItemIcon><DriveFileRenameOutlineIcon fontSize="small" /></ListItemIcon>
                <ListItemText>重命名</ListItemText>
            </MenuItem>
        )}
        {currentItem && path !== '' && (
            <MenuItem onClick={() => handleMenuAction(onDelete)} sx={{ color: 'error.main' }}>
                <ListItemIcon sx={{ color: 'error.main' }}><DeleteForeverIcon fontSize="small" /></ListItemIcon>
                <ListItemText>删除</ListItemText>
            </MenuItem>
        )}
      </Menu>
    </>
  );
}