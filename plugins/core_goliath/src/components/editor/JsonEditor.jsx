// plugins/core_goliath/src/components/editor/JsonEditor.jsx

import React, { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextareaAutosize from '@mui/material/TextareaAutosize';
import { styled } from '@mui/material/styles';
import CircularProgress from '@mui/material/CircularProgress';

const StyledTextarea = styled(TextareaAutosize)(({ theme }) => ({
    width: '100%',
    flexGrow: 1,
    padding: theme.spacing(1.5),
    fontFamily: 'monospace',
    fontSize: '0.9rem',
    lineHeight: 1.5,
    backgroundColor: theme.palette.mode === 'dark' ? '#1E1E1E' : '#FFF',
    color: theme.palette.text.primary,
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: theme.shape.borderRadius,
    resize: 'none',
    '&:focus': {
        outline: `2px solid ${theme.palette.primary.main}`,
        borderColor: 'transparent',
    },
}));

export default function JsonEditor({ initialJson, onSave, isMomentScope, loading }) {
    const [jsonString, setJsonString] = useState('');
    const [isValid, setIsValid] = useState(true);

    useEffect(() => {
        try {
            const formattedJson = JSON.stringify(initialJson, null, 2);
            setJsonString(formattedJson);
            setIsValid(true);
        } catch (e) {
            setJsonString("Error formatting JSON.");
            setIsValid(false);
        }
    }, [initialJson]);

    const handleChange = (event) => {
        const newText = event.target.value;
        setJsonString(newText);
        try {
            JSON.parse(newText);
            setIsValid(true);
        } catch (e) {
            setIsValid(false);
        }
    };
    
    const handleSaveClick = () => {
        if (isValid) {
            onSave(jsonString);
        }
    };

    const buttonText = isMomentScope ? 'Apply & Create History' : 'Save Changes';

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <StyledTextarea
                value={jsonString}
                onChange={handleChange}
                aria-label="JSON Editor"
            />
            <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button
                    variant="contained"
                    onClick={handleSaveClick}
                    disabled={!isValid || loading}
                >
                    {loading ? <CircularProgress size={24} color="inherit" /> : buttonText}
                </Button>
                {!isValid && (
                    <Typography variant="caption" color="error">
                        Invalid JSON format.
                    </Typography>
                )}
            </Box>
        </Box>
    );
}