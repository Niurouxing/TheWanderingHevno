// plugins/core_goliath/src/components/ImportSandboxDialog.jsx

import React, { useState, useEffect, useMemo } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useSandbox } from '../context/SandboxContext';
import ImageUploader from './ImageUploader';

// 假设我们有一个PNG解析工具
// import { extractDataFromPng } from '../utils/pngUtils'; // 如果需要前端解析预览

export default function ImportSandboxDialog() {
  const { importSandbox, selectSandbox, loading } = useSandbox();
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const hookManager = window.Hevno.services.get('hookManager');
    if (!hookManager) return;

    const showDialog = () => {
      setOpen(true);
      setSelectedFile(null);
      setFileName('');
      setError('');
    };

    hookManager.addImplementation('ui.show.importSandboxDialog', showDialog);

    return () => {
      hookManager.removeImplementation('ui.show.importSandboxDialog', showDialog);
    };
  }, []);

  const handleClose = () => {
    if (loading) return;
    setOpen(false);
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setFileName(file.name);
    // 可选：在这里可以尝试用PNG库解析文件，如果解析失败可以提前报错
    // const data = await extractDataFromPng(file);
    // if (!data) { setError("This PNG does not contain valid sandbox data."); }
  };
  
  const handleImport = async () => {
    if (!selectedFile) {
        setError("Please select a PNG file.");
        return;
    }
    setError('');

    try {
        // ✨ 关键修复：现在只需调用 importSandbox。
        // 它会处理导入、刷新列表和选择新项的所有逻辑。
        await importSandbox(selectedFile);
        
        // 成功后直接关闭对话框
        handleClose();
        
    } catch (e) {
        setError(e.message || "An unknown error occurred during import.");
    }
  };
  
  
  // 使用 useMemo 来确定按钮是否应该被禁用
  const isImportDisabled = useMemo(() => {
      return !selectedFile || loading;
  }, [selectedFile, loading]);

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Import Sandbox from PNG</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <ImageUploader 
            onFileSelect={handleFileSelect} 
            sx={{ height: 200 }} 
          />
          {/* 显示已选择的文件名，给用户一个反馈 */}
          {fileName && (
              <Typography variant="body2" align="center" sx={{ mt: 1 }}>
                  Selected file: <strong>{fileName}</strong>
              </Typography>
          )}
          {error && (
            <Typography color="error" variant="body2" sx={{ mt: 1 }}>{error}</Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>Cancel</Button>
        <Button 
            onClick={handleImport} 
            variant="contained"
            disabled={isImportDisabled}
            // 使用 startIcon 来显示加载指示器
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
        >
          {/* 在加载时可以改变按钮文本以提供更明确的反馈 */}
          {loading ? 'Importing...' : 'Import'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}