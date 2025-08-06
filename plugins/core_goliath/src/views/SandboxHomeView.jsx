// plugins/core_goliath/src/views/SandboxHomeView.jsx
import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { useSandbox } from '../context/SandboxContext';

export default function SandboxHomeView() {
    const { selectedSandbox } = useSandbox();

    return (
        <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
            <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
                Sandbox Home: {selectedSandbox?.name}
            </Typography>
            <Card>
                <CardContent>
                    <Typography>This is the Home view for the selected sandbox.</Typography>
                    <Typography color="text.secondary" sx={{mt: 1}}>Here you can manage basic information, rename, or export the sandbox.</Typography>
                </CardContent>
            </Card>
        </Box>
  );
}