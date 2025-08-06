// plugins/core_goliath/src/views/WelcomeView.jsx
import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import SelectAllRoundedIcon from '@mui/icons-material/SelectAllRounded';
import Box from '@mui/material/Box';

export default function WelcomeView() {
  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
        <Card sx={{ mt: 2, p: 4, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <SelectAllRoundedIcon sx={{ fontSize: 60, color: 'text.secondary' }} />
            <CardContent>
                <Typography variant="h5" component="div" align="center">
                    Welcome to Hevno Engine
                </Typography>
                <Typography sx={{ mt: 1.5 }} color="text.secondary" align="center">
                    Please select a sandbox from the top-left menu to get started, or create a new one.
                </Typography>
            </CardContent>
        </Card>
    </Box>
  );
}