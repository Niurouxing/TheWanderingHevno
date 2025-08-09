// plugins/sandbox_explorer/src/components/CreateSandboxDialog.jsx
import React, { useState } from 'react';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField, CircularProgress, Box, Typography } from '@mui/material';
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


export function CreateSandboxDialog({ open, onClose, onCreate }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile && selectedFile.type === 'image/png') {
      setFile(selectedFile);
      setError('');
    } else {
      setError('Please select a valid PNG file.');
    }
  };

  const handleCreate = async () => {
    if (!file) {
      setError('A PNG file is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await onCreate(file);
      handleClose();
    } catch (e) {
      setError(e.message || 'Failed to import sandbox.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleClose = () => {
      if(loading) return;
      setFile(null);
      setError('');
      onClose();
  }

  return (
    <Dialog open={open} onClose={handleClose}>
      <DialogTitle>Import New Sandbox</DialogTitle>
      <DialogContent>
        <Box sx={{ my: 2, textAlign: 'center' }}>
            <Button
                component="label"
                role={undefined}
                variant="contained"
                tabIndex={-1}
            >
                Select PNG File
                <VisuallyHiddenInput type="file" accept="image/png" onChange={handleFileChange} />
            </Button>
            {file && <Typography sx={{mt: 1}}>Selected: {file.name}</Typography>}
            {error && <Typography color="error" sx={{mt: 1}}>{error}</Typography>}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>Cancel</Button>
        <Button onClick={handleCreate} variant="contained" disabled={!file || loading}>
          {loading ? <CircularProgress size={24} /> : 'Import'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}