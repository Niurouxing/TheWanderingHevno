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

export default function ImportSandboxDialog() {
  const { importSandbox, loading } = useSandbox(); // 只需 importSandbox 和 loading
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
    if (file.type !== 'image/png') {
        setError('Please select a valid PNG file.');
        setSelectedFile(null);
        setFileName('');
        return;
    }
    setError('');
    setSelectedFile(file);
    setFileName(file.name);
  };
  
  const handleImport = async () => {
    if (!selectedFile) {
        setError("Please select a PNG file.");
        return;
    }
    setError('');

    try {
        await importSandbox(selectedFile);
        handleClose();
    } catch (e) {
        setError(e.message || "An unknown error occurred during import.");
    }
  };
  
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
          {fileName && (
              <Typography variant="body2" align="center" sx={{ mt: 1 }}>
                  Selected file: <strong>{fileName}</strong>
              </Typography>
          )}
          {error && (
            <Typography color="error" variant="body2" align="center" sx={{ mt: 1 }}>{error}</Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>Cancel</Button>
        <Button 
            onClick={handleImport} 
            variant="contained"
            disabled={isImportDisabled}
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
        >
          {loading ? 'Importing...' : 'Import'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}