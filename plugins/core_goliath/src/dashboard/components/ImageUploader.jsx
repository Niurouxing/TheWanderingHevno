// plugins/core_goliath/src/components/ImageUploader.jsx

import React, { useState, useRef, useEffect } from 'react';
import Box from '@mui/material/Box';
import Avatar from '@mui/material/Avatar';
import Typography from '@mui/material/Typography';
import { styled } from '@mui/material/styles';
import AddPhotoAlternateRoundedIcon from '@mui/icons-material/AddPhotoAlternateRounded';

// 1. 创建一个隐藏的 input[type=file]
const VisuallyHiddenInput = styled('input')({
  clip: 'rect(0 0 0 0)',
  clipPath: 'inset(50%)',
  height: 1,
  overflow: 'hidden',
  position: 'absolute',
  bottom: 0,
  left: 0,
  whiteSpace: 'nowrap',
  width: 1,
});

// 2. 设计上传区域的主体样式
const UploadArea = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  border: `2px dashed ${theme.palette.divider}`,
  borderRadius: theme.shape.borderRadius,
  transition: 'border-color 300ms ease-in-out, background-color 300ms ease-in-out',
  backgroundColor: theme.palette.action.hover,
  '&:hover': {
    borderColor: theme.palette.primary.main,
    backgroundColor: alpha(theme.palette.primary.main, 0.05),
  },
}));

/**
 * 一个可复用的图片上传和预览组件。
 * @param {object} props
 * @param {function(File, string): void} props.onFileSelect - 用户选择文件后的回调，返回File对象和预览URL。
 * @param {string} [props.currentImageUrl] - 当前显示的图片URL。
 * @param {React.ReactNode} [props.defaultIcon] - 在没有图片时显示的默认图标。
 * @param {object} [props.sx] - 允许外部传入sx样式来控制大小等。
 */
export default function ImageUploader({ onFileSelect, currentImageUrl, defaultIcon, sx }) {
  const [preview, setPreview] = useState(null);
  const fileInputRef = useRef(null);

  // 3. 当外部传入的 currentImageUrl 变化时，更新预览
  useEffect(() => {
    setPreview(currentImageUrl || null);
  }, [currentImageUrl]);

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (file && file.type.startsWith('image/')) {
      // 4. 创建本地预览URL
      const previewUrl = URL.createObjectURL(file);
      setPreview(previewUrl);
      
      // 5. 调用回调函数，将文件和预览URL传出
      if (onFileSelect) {
        onFileSelect(file, previewUrl);
      }
    }
    // 清空input的值，确保下次选择相同文件时也能触发onChange
    if(event.target) {
        event.target.value = null;
    }
  };

  const handleAreaClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <UploadArea sx={{ p: 2, ...sx }} onClick={handleAreaClick}>
      <VisuallyHiddenInput
        ref={fileInputRef}
        type="file"
        accept="image/png" // 限制只能上传png
        onChange={handleFileChange}
      />
      {preview ? (
        // 6. 如果有预览图，则显示图片
        <Avatar
          src={preview}
          alt="Preview"
          variant="rounded" // 使用圆角矩形，更通用
          sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
        >
          {/* Avatar的子元素作为src加载失败时的fallback */}
           {defaultIcon}
        </Avatar>
      ) : (
        // 7. 如果没有预览图，则显示默认上传提示
        <Box sx={{ textAlign: 'center', color: 'text.secondary' }}>
          {defaultIcon || <AddPhotoAlternateRoundedIcon sx={{ fontSize: 40, mb: 1 }} />}
          <Typography variant="body2">
            Click to upload
          </Typography>
          <Typography variant="caption">
            PNG only
          </Typography>
        </Box>
      )}
    </UploadArea>
  );
}

// 补全 alpha 函数的定义，因为它在上面的 styled-component 中用到了
function alpha(color, value) {
    // 简单的实现，实际项目中可能从 @mui/material/styles 导入
    if (color.startsWith('#')) {
        const [r, g, b] = [parseInt(color.slice(1, 3), 16), parseInt(color.slice(3, 5), 16), parseInt(color.slice(5, 7), 16)];
        return `rgba(${r}, ${g}, ${b}, ${value})`;
    }
    if (color.startsWith('rgba')) return color; // no-op
    // This is a very basic fallback.
    return color; 
}