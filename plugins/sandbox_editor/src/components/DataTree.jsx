import React, { useState } from 'react';
import { List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import EditIcon from '@mui/icons-material/Edit';
import { isObject, isArray } from '../utils/constants';

export function DataTree({ data, path = '', onEdit, activeScope }) {
  const [expanded, setExpanded] = useState({});
  const toggleExpand = (key) => { setExpanded((prev) => ({ ...prev, [key]: !prev[key] })); };
  if (!data) return null;
  return (
    <List disablePadding sx={{ pl: path ? 2 : 0 }}>
      {Object.entries(data).map(([key, value]) => {
        const currentPath = path ? `${path}.${key}` : key;
        const isExpandable = isObject(value) || isArray(value);
        const isCodex = key === 'codices' || (isObject(value) && value.entries && Array.isArray(value.entries));
        return (
          <React.Fragment key={currentPath}>
            <ListItem 
              button 
              onClick={isExpandable ? () => toggleExpand(currentPath) : undefined}
              secondaryAction={isCodex ? (<IconButton edge="end" onClick={() => onEdit(currentPath, value, key, activeScope)}><EditIcon /></IconButton>) : null}
            >
              <ListItemIcon>{isExpandable ? <FolderIcon /> : <DescriptionIcon />}</ListItemIcon>
              <ListItemText 
                primary={key} 
                secondary={!isExpandable ? (typeof value === 'string' ? value.slice(0, 50) + (value.length > 50 ? '...' : '') : JSON.stringify(value)) : `${isArray(value) ? 'Array' : 'Object'} (${Object.keys(value).length} items)`} 
              />
              {isExpandable && (<IconButton size="small" onClick={() => toggleExpand(currentPath)}>{expanded[currentPath] ? <ExpandMoreIcon /> : <ChevronRightIcon />}</IconButton>)}
            </ListItem>
            {isExpandable && (
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