// plugins/sandbox_explorer/src/components/SandboxCard.jsx
import React from 'react';
import { Card, CardActionArea, CardMedia, CardContent, Typography, Box, IconButton, Menu, MenuItem } from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import EditIcon from '@mui/icons-material/Edit';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteIcon from '@mui/icons-material/Delete';

// 一个占位符图片，以防沙盒没有图标
const placeholderImage = 'data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22286%22%20height%3D%22180%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20286%20180%22%20preserveAspectRatio%3D%22none%22%3E%3Cdefs%3E%3Cstyle%20type%3D%22text%2Fcss%22%3E%23holder_158bd1d6d70%20text%20%7B%20fill%3A%23AAAAAA%3Bfont-weight%3Anormal%3Bfont-family%3AHelvetica%2C%20monospace%3Bfont-size%3A14pt%20%7D%20%3C%2Fstyle%3E%3C%2Fdefs%3E%3Cg%20id%3D%22holder_158bd1d6d70%22%3E%3Crect%20width%3D%22286%22%20height%3D%22180%22%20fill%3D%22%23EEEEEE%22%3E%3C%2Frect%3E%3Cg%3E%3Ctext%20x%3D%22107.19140625%22%20y%3D%2296.3%22%3ENo%20Image%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E';

export function SandboxCard({ sandbox, onEdit, onRun, onDelete, onSelect }) {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);

  const handleMenuClick = (event) => {
    event.stopPropagation(); // 防止触发卡片点击
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => setAnchorEl(null);

  const handleDelete = () => {
    onDelete(sandbox.id);
    handleMenuClose();
  };

  return (
    <Card sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <CardActionArea onClick={() => onSelect(sandbox.id)}>
        <CardMedia
          component="img"
          height="140"
          image={sandbox.icon_url || placeholderImage}
          alt={`Cover for ${sandbox.name}`}
          // onError可以处理图片加载失败的情况
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
            <MenuItem onClick={handleDelete}><DeleteIcon fontSize="small" sx={{mr: 1}}/> Delete</MenuItem>
        </Menu>
      </Box>
    </Card>
  );
}