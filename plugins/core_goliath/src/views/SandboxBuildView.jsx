// plugins/core_goliath/src/views/SandboxBuildView.jsx
import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { useSandbox } from '../context/SandboxContext';

export default function SandboxBuildView() {
    const { selectedSandbox } = useSandbox();

    return (
        <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
            <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
                Graph Editor: {selectedSandbox?.name}
            </Typography>
            <Card>
                <CardContent>
                    <Typography>This is the Build view.</Typography>
                    <Typography color="text.secondary" sx={{mt: 1}}>A visual graph editor (like React Flow) will be rendered here to edit the sandbox's logic.</Typography>
                </CardContent>
            </Card>
        </Box>
  );
}