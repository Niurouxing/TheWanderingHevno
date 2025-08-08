import React from 'react';
import Form from '@rjsf/mui';
import validator from '@rjsf/validator-ajv8';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';

// Import our custom components
import CollapsibleObjectField from './fields/CollapsibleObjectField';
import CodeEditorWidget from './widgets/CodeEditorWidget';


const customFields = {
    CollapsibleObjectField: CollapsibleObjectField,
};

const customWidgets = {
    CodeEditor: CodeEditorWidget,
};

export default function SchemaFormEditor({ schema, formData, onSave, isMomentScope, loading }) {
  
  const handleSubmit = ({ formData }) => {
      if (onSave) {
          onSave(formData);
      }
  };

  const buttonText = isMomentScope ? 'Apply & Create History' : 'Save Changes';

  return (
    <Form
      schema={schema}
      formData={formData}
      validator={validator}
      onSubmit={handleSubmit}
      fields={customFields}
      widgets={customWidgets}
      // This removes the default RJSF submit button
      // We will provide our own button as a child
      slots={{
          SubmitButton: () => null 
      }}
    >
        <Box sx={{ mt: 2 }}>
            <Button
                type="submit"
                variant="contained"
                disabled={loading}
            >
                {loading ? <CircularProgress size={24} color="inherit" /> : buttonText}
            </Button>
        </Box>
    </Form>
  );
}