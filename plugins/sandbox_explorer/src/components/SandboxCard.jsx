// plugins/sandbox_explorer/src/components/SandboxCard.jsx
import React from 'react';
import { Card, CardActionArea, CardMedia, CardContent, Typography, Box, IconButton, Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import EditIcon from '@mui/icons-material/Edit';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteIcon from '@mui/icons-material/Delete';
import ImageIcon from '@mui/icons-material/Image';
import DataObjectIcon from '@mui/icons-material/DataObject';

const placeholderImage = 'data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22286%22%20height%3D%22180%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20286%20180%22%20preserveAspectRatio%3D%22none%22%3E%3Cdefs%3E%3Cstyle%20type%3D%22text%2Fcss%22%3E%23holder_158bd1d6d70%20text%20%7B%20fill%3A%23AAAAAA%3Bfont-weight%3Anormal%3Bfont-family%3AHelvetica%2C%20monospace%3Bfont-size%3A14pt%20%7D%20%3C%2Fstyle%3E%3C%2Fdefs%3E%3Cg%20id%3D%22holder_158bd1d6d70%22%3E%3Crect%20width%3D%22286%22%20height%3D%22180%22%20fill%3D%22%23EEEEEE%22%3E%3C%2Frect%3E%3Cg%3E%3Ctext%20x%3D%22107.19140625%22%20y%3D%2296.3%22%3ENo%20Image%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E';

export function SandboxCard({ sandbox, onEdit, onRun, onDelete, onSelect, onExportPng, onExportJson }) {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);

  const handleMenuClick = (event) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => setAnchorEl(null);

  const handleAction = (action) => {
    handleMenuClose();
    action();
  };
  
  // --- DEFINITIVE FIX ---
  // The key change is here: We check `has_custom_icon` BEFORE deciding the image source.
  // If it's false, we immediately use the placeholder and AVOID the network request entirely.
  const iconUrl = sandbox.has_custom_icon
    ? `/api/sandboxes/${sandbox.id}/icon?v=${new Date(sandbox.icon_updated_at || sandbox.created_at).getTime()}`
    : placeholderImage;

  return (
    <Card sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <CardActionArea onClick={() => onSelect(sandbox.id)}>
        <CardMedia
          component="img"
          height="140"
          // --- MODIFIED: Use the conditionally determined URL ---
          image={iconUrl}
          alt={`Cover for ${sandbox.name}`}
          // The onError is now just a fallback for the rare case where has_custom_icon is true
          // but the icon fetch still fails for some other reason.
          onError={(e) => { e.target.onerror = null; e.target.src = placeholderImage; }}
        />
        <CardContent sx={{ flexGrow: 1 }}>
          <Typography gutterBottom variant="h5" component="div" noWrap>
            {sandbox.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Created: {new Date(sandbox.created_at).toLocaleDateString()}
          </Typography>
        </CardContent>
      </CardActionArea>
      <Box sx={{ p: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
            <IconButton size="small" onClick={() => onEdit(sandbox.id)} title="Edit Sandbox">
                <EditIcon />
            </IconButton>
            <IconButton size="small" onClick={() => onRun(sandbox.id)} title="Run Sandbox">
                <PlayArrowIcon />
            </IconButton>
        </Box>
        <IconButton size="small" onClick={handleMenuClick} title="More options">
            <MoreVertIcon />
        </IconButton>
        <Menu anchorEl={anchorEl} open={open} onClose={handleMenuClose}>
          <MenuItem onClick={() => handleAction(onExportPng)}>
            <ListItemIcon><ImageIcon fontSize="small" /></ListItemIcon>
            <ListItemText>Export as PNG</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleAction(onExportJson)}>
            <ListItemIcon><DataObjectIcon fontSize="small" /></ListItemIcon>
            <ListItemText>Export as JSON</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleAction(() => onDelete(sandbox.id))} sx={{color: 'error.main'}}>
            <ListItemIcon><DeleteIcon fontSize="small" color="error" /></ListItemIcon>
            <ListItemText>Delete</ListItemText>
          </MenuItem>
        </Menu>
      </Box>
    </Card>
  );
}