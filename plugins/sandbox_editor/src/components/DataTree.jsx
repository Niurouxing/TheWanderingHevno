import React, { useState } from 'react';
import { List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton, Typography } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import EditIcon from '@mui/icons-material/Edit';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import HistoryIcon from '@mui/icons-material/History';
import { isObject, isArray } from '../utils/constants';

const HEVNO_TYPE_EDITORS = {
  'hevno/codex': { icon: <AutoStoriesIcon />, tooltip: '编辑 Codex' },
  'hevno/graph': { icon: <AccountTreeIcon />, tooltip: '编辑 Graph' },
  'hevno/memoria': { icon: <HistoryIcon />, tooltip: '编辑 Memoria' },
};

export function DataTree({ data, path = '', onEdit }) {
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

        return (
          <React.Fragment key={currentPath}>
            <ListItem
              disablePadding
              secondaryAction={
                // --- [修改] 为所有条目统一提供编辑按钮 ---
                <IconButton edge="end" onClick={() => onEdit(currentPath, value)} title={editorInfo ? editorInfo.tooltip : '编辑值'}>
                  <EditIcon />
                </IconButton>
              }
            >
              <ListItemIcon sx={{minWidth: '40px'}}>
                {editorInfo ? editorInfo.icon : (isExpandable ? <FolderIcon /> : <DescriptionIcon />)}
              </ListItemIcon>
              <ListItemText 
                primary={key} 
                secondary={
                    editorInfo 
                    ? `类型: ${hevnoType.split('/')[1]}`
                    : !isExpandable 
                        ? (typeof value === 'string' ? value.slice(0, 50) + (value.length > 50 ? '...' : '') : JSON.stringify(value)) 
                        : `${isArray(value) ? '数组' : '对象'} (${Object.keys(value).length} 项)`
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
                <DataTree data={value} path={currentPath} onEdit={onEdit} />
              </Collapse>
            )}
          </React.Fragment>
        );
      })}
    </List>
  );
}