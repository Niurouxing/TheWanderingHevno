// plugins/core_goliath/src/views/SandboxHomeView.jsx
import React, { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';

import { useSandbox } from '../context/SandboxContext';
import ImageUploader from '../components/ImageUploader';

export default function SandboxHomeView() {
    const { 
        selectedSandbox, 
        loading, 
        updateSandboxIcon, 
        updateSandboxName,
        deleteSandbox,
    } = useSandbox();

    const [name, setName] = useState(selectedSandbox?.name || '');
    const [isNameDirty, setIsNameDirty] = useState(false);
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

    useEffect(() => {
        setName(selectedSandbox?.name || '');
        setIsNameDirty(false);
    }, [selectedSandbox]);

    const handleIconChange = async (file) => {
        if (!selectedSandbox) return;
        try {
            await updateSandboxIcon(selectedSandbox.id, file);
        } catch (error) {
            console.error("Failed to update icon:", error);
            // 可以在这里添加一个 toast 通知用户失败
        }
    };

    const handleNameChange = (event) => {
        setName(event.target.value);
        setIsNameDirty(event.target.value !== selectedSandbox?.name);
    };

    const handleSaveName = async () => {
        if (!selectedSandbox || !isNameDirty) return;
        try {
            await updateSandboxName(selectedSandbox.id, name);
            setIsNameDirty(false);
        } catch (error) {
            console.error("Failed to update name:", error);
        }
    };
    
    const handleExport = () => {
        if (!selectedSandbox) return;
        const link = document.createElement('a');
        link.href = `/api/sandboxes/${selectedSandbox.id}/export`;
        link.setAttribute('download', `${selectedSandbox.name || 'sandbox'}.png`); 
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleDelete = async () => {
        if (!selectedSandbox) return;
        await deleteSandbox(selectedSandbox.id);
        setDeleteConfirmOpen(false); // 对话框会在沙盒被删除后自动关闭
    };

    if (!selectedSandbox) {
        // 通常不会在这里渲染，因为 Dashboard 会显示 WelcomeView
        return null; 
    }

    return (
        <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
            <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
                Sandbox Home: {selectedSandbox.name}
            </Typography>
            
            <Grid container spacing={3}>
                <Grid xs={12} md={4}>
                    <Card>
                        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <Typography variant="subtitle1">Cover Image</Typography>
                            <ImageUploader
                                onFileSelect={handleIconChange}
                                currentImageUrl={selectedSandbox.icon_url}
                                sx={{ height: 220, width: '100%' }}
                            />
                            <Button 
                                variant="contained" 
                                onClick={handleExport}
                                disabled={loading}
                            >
                                Export to PNG
                            </Button>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid xs={12} md={8}>
                    <Card>
                        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                            <Box>
                                <Typography variant="subtitle1" gutterBottom>Sandbox Name</Typography>
                                <TextField
                                    fullWidth
                                    variant="outlined"
                                    value={name}
                                    onChange={handleNameChange}
                                    disabled={loading}
                                />
                                <Button
                                    sx={{ mt: 1 }}
                                    variant="outlined"
                                    onClick={handleSaveName}
                                    disabled={!isNameDirty || loading}
                                >
                                    {loading && isNameDirty ? <CircularProgress size={24} /> : 'Save Name'}
                                </Button>
                            </Box>
                            
                            <Box>
                                <Typography variant="subtitle1" gutterBottom>Danger Zone</Typography>
                                <Button
                                    variant="outlined"
                                    color="error"
                                    onClick={() => setDeleteConfirmOpen(true)}
                                    disabled={loading}
                                >
                                    Delete Sandbox
                                </Button>
                                <Typography variant="caption" display="block" color="text.secondary" sx={{mt: 1}}>
                                    This action is permanent and cannot be undone.
                                </Typography>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            <Dialog
                open={deleteConfirmOpen}
                onClose={() => setDeleteConfirmOpen(false)}
            >
                <DialogTitle>Are you sure?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        You are about to permanently delete the sandbox "{selectedSandbox.name}".
                        This action cannot be undone.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteConfirmOpen(false)} disabled={loading}>Cancel</Button>
                    <Button onClick={handleDelete} color="error" autoFocus>
                        {loading ? <CircularProgress size={24} color="inherit" /> : 'Delete'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}