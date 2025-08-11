// plugins/sandbox_explorer/src/components/AddSandboxDialog.jsx
import React, { useState } from 'react';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, CircularProgress, Box, Typography, Tabs, Tab, TextField } from '@mui/material';
import { styled } from '@mui/material/styles';

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

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} id={`simple-tabpanel-${index}`} aria-labelledby={`simple-tab-${index}`} {...other}>
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export function AddSandboxDialog({ open, onClose, onCreateEmpty, onImport }) {
  const [activeTab, setActiveTab] = useState(0);
  
  // State for Import Tab
  const [file, setFile] = useState(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState('');

  // State for Create Empty Tab
  const [name, setName] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };
  
  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile && (selectedFile.type === 'image/png' || selectedFile.type === 'application/json' || selectedFile.name.endsWith('.json'))) {
      setFile(selectedFile);
      setImportError('');
    } else {
      setFile(null);
      setImportError('Please select a valid PNG or JSON file.');
    }
  };

  const handleImport = async () => {
    if (!file) {
      setImportError('A PNG or JSON file is required.');
      return;
    }
    setImportLoading(true);
    setImportError('');
    try {
      await onImport(file);
      handleClose();
    } catch (e) {
      setImportError(e.message || 'Failed to import sandbox.');
    } finally {
      setImportLoading(false);
    }
  };

  const handleCreateEmpty = async () => {
      if (!name.trim()) {
          setCreateError('Sandbox name is required.');
          return;
      }
      setCreateLoading(true);
      setCreateError('');
      try {
          await onCreateEmpty(name.trim());
          handleClose();
      } catch (e) {
          setCreateError(e.message || 'Failed to create sandbox.');
      } finally {
          setCreateLoading(false);
      }
  };
  
  const handleClose = () => {
      if (importLoading || createLoading) return;
      // Reset all states
      setFile(null);
      setImportError('');
      setName('');
      setCreateError('');
      setActiveTab(0);
      const input = document.querySelector('input[type="file"]');
      if (input) {
          input.value = '';
      }
      onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>添加新沙盒</DialogTitle>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="add sandbox options" centered>
          <Tab label="创建空沙盒" />
          <Tab label="从文件导入" />
        </Tabs>
      </Box>

      {/* Create Empty Sandbox Tab */}
      <TabPanel value={activeTab} index={0}>
        <DialogContent sx={{p:0}}>
            <Typography>为你的新沙盒世界命名。</Typography>
            <TextField
                autoFocus
                margin="dense"
                id="name"
                label="沙盒名称"
                type="text"
                fullWidth
                variant="standard"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleCreateEmpty()}
            />
            {createError && <Typography color="error" sx={{mt: 2}}>{createError}</Typography>}
        </DialogContent>
        <DialogActions>
            <Button onClick={handleClose} disabled={createLoading}>取消</Button>
            <Button onClick={handleCreateEmpty} variant="contained" disabled={!name.trim() || createLoading}>
            {createLoading ? <CircularProgress size={24} /> : '创建'}
            </Button>
        </DialogActions>
      </TabPanel>
      
      {/* Import from File Tab */}
      <TabPanel value={activeTab} index={1}>
        <DialogContent sx={{p:0}}>
            <Box sx={{ textAlign: 'center' }}>
                <Typography>从一个 `.png` 或 `.json` 文件导入一个完整的沙盒。</Typography>
                <Button component="label" role={undefined} variant="outlined" tabIndex={-1} sx={{my: 2}}>
                    选择文件
                    <VisuallyHiddenInput type="file" accept="image/png,application/json,.json" onChange={handleFileChange} />
                </Button>
                {file && <Typography>已选择: {file.name}</Typography>}
                {importError && <Typography color="error" sx={{mt: 1}}>{importError}</Typography>}
            </Box>
        </DialogContent>
        <DialogActions>
            <Button onClick={handleClose} disabled={importLoading}>取消</Button>
            <Button onClick={handleImport} variant="contained" disabled={!file || importLoading}>
            {importLoading ? <CircularProgress size={24} /> : '导入'}
            </Button>
        </DialogActions>
      </TabPanel>
    </Dialog>
  );
}