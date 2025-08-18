// plugins/sandbox_explorer/src/components/SandboxCard.jsx
import React, { useRef } from 'react';
import { Card, CardActionArea, CardMedia, CardContent, Typography, Box, IconButton, Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import EditIcon from '@mui/icons-material/Edit';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteIcon from '@mui/icons-material/Delete';
import ImageIcon from '@mui/icons-material/Image';
import DataObjectIcon from '@mui/icons-material/DataObject';
// ---导入新图标 ---
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera';

const placeholderImage = 'data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22286%22%20height%3D%22180%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20286%20180%22%20preserveAspectRatio%3D%22none%22%3E%3Cdefs%3E%3Cstyle%20type%3D%22text%2Fcss%22%3E%23holder_158bd1d6d70%20text%20%7B%20fill%3A%23AAAAAA%3Bfont-weight%3Anormal%3Bfont-family%3AHelvetica%2C%20monospace%3Bfont-size%3A14pt%20%7D%20%3C%2Fstyle%3E%3C%2Fdefs%3E%3Cg%20id%3D%22holder_158bd1d6d70%22%3E%3Crect%20width%3D%22286%22%20height%3D%22180%22%20fill%3D%22%23EEEEEE%22%3E%3C%2Frect%3E%3Cg%3E%3Ctext%20x%3D%22107.19140625%22%20y%3D%2296.3%22%3ENo%20Image%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E';

// ---接收 onUploadIcon prop ---
export function SandboxCard({ sandbox, onEdit, onRun, onDelete, onSelect, onExportPng, onExportJson, onUploadIcon }) {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);
  // ---为隐藏的文件输入框创建一个引用 ---
  const fileInputRef = useRef(null);

  const handleMenuClick = (event) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => setAnchorEl(null);

  const handleAction = (action) => {
    handleMenuClose();
    action();
  };

  // ---当“更换封面”菜单项被点击时，触发隐藏的文件输入框 ---
  const handleUploadClick = () => {
    fileInputRef.current?.click();
    handleMenuClose();
  };

  // ---当用户选择文件后，此函数被调用 ---
  const handleFileSelect = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      // 调用从父组件传入的处理器
      await onUploadIcon(sandbox.id, file);
    }
    // 重置输入框的值，以确保即使用户再次选择相同的文件也能触发 onChange 事件
    if (event.target) {
      event.target.value = null;
    }
  };
  
  const iconUrl = sandbox.has_custom_icon
    ? `/api/sandboxes/${sandbox.id}/icon?v=${new Date(sandbox.icon_updated_at || sandbox.created_at).getTime()}`
    : placeholderImage;

  return (
    <Card sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept="image/png"
        style={{ display: 'none' }}
      />
      
      <CardActionArea onClick={() => onSelect(sandbox.id)}>
        <CardMedia
          component="img"
          height="140"
          image={iconUrl}
          alt={`Cover for ${sandbox.name}`}
          onError={(e) => { e.target.onerror = null; e.target.src = placeholderImage; }}
        />
        <CardContent sx={{ flexGrow: 1 }}>
          <Typography gutterBottom variant="h5" component="div" noWrap>
            {sandbox.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            创建于: {new Date(sandbox.created_at).toLocaleDateString()}
          </Typography>
        </CardContent>
      </CardActionArea>
      <Box sx={{ p: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
            <IconButton size="small" onClick={() => onEdit(sandbox.id)} title="编辑沙盒">
                <EditIcon />
            </IconButton>
            <IconButton size="small" onClick={() => onRun(sandbox.id)} title="运行沙盒">
                <PlayArrowIcon />
            </IconButton>
        </Box>
        <IconButton size="small" onClick={handleMenuClick} title="更多选项">
            <MoreVertIcon />
        </IconButton>
        <Menu anchorEl={anchorEl} open={open} onClose={handleMenuClose}>
          <MenuItem onClick={handleUploadClick}>
            <ListItemIcon><PhotoCameraIcon fontSize="small" /></ListItemIcon>
            <ListItemText>更换封面</ListItemText>
          </MenuItem>

          <MenuItem onClick={() => handleAction(onExportPng)}>
            <ListItemIcon><ImageIcon fontSize="small" /></ListItemIcon>
            <ListItemText>导出为PNG</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleAction(onExportJson)}>
            <ListItemIcon><DataObjectIcon fontSize="small" /></ListItemIcon>
            <ListItemText>导出为JSON</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleAction(() => onDelete(sandbox.id))} sx={{color: 'error.main'}}>
            <ListItemIcon><DeleteIcon fontSize="small" color="error" /></ListItemIcon>
            <ListItemText>删除</ListItemText>
          </MenuItem>
        </Menu>
      </Box>
    </Card>
  );
}