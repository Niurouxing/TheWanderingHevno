// plugins/core_goliath/src/views/SandboxRunView.jsx
import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { useSandbox } from '../context/SandboxContext';

export default function SandboxRunView() {
    const { selectedSandbox } = useSandbox();

    return (
        <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
            <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
                Runner: {selectedSandbox?.name}
            </Typography>
            <Card>
                <CardContent>
                    <Typography>This is the Run view.</Typography>
                    <Typography color="text.secondary" sx={{mt: 1}}>A chat-like interface for interacting with the running sandbox will be implemented here.</Typography>
                </CardContent>
            </Card>
        </Box>
  );
}