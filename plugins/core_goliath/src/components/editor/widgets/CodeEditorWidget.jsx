// plugins/core_goliath/src/components/editor/widgets/CodeEditorWidget.jsx
import React from 'react';
import Editor from '@monaco-editor/react';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import FormLabel from '@mui/material/FormLabel';

export default function CodeEditorWidget(props) {
  const { id, value, label, onChange, uiSchema } = props;
  const theme = useTheme();
  const options = uiSchema['ui:options'] || {};

  return (
    <Box sx={{ my: 2 }}>
        <FormLabel htmlFor={id}>{label}</FormLabel>
        <Box 
            sx={{ 
                mt: 1, 
                border: '1px solid', 
                borderColor: 'divider', 
                borderRadius: 1, 
                overflow: 'hidden',
                height: options.height || 200 
            }}
        >
            <Editor
                language={options.language || 'javascript'}
                value={value}
                onChange={(newValue) => onChange(newValue)}
                theme={theme.palette.mode === 'dark' ? 'vs-dark' : 'light'}
                options={{
                    minimap: { enabled: false },
                    fontSize: '14px',
                    ...options
                }}
            />
        </Box>
    </Box>
  );
}