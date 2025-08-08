// plugins/core_goliath/src/components/editor/fields/CollapsibleObjectField.jsx
import React, { useState } from 'react';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import Box from '@mui/material/Box';

export default function CollapsibleObjectField(props) {
  const { title, properties, uiSchema } = props;
  const startCollapsed = uiSchema['ui:options']?.startCollapsed ?? false;
  const [expanded, setExpanded] = useState(!startCollapsed);

  return (
    <Accordion expanded={expanded} onChange={() => setExpanded(!expanded)} sx={{ my: 1 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="h6">{title}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Box>
          {properties.map(element => (
            <div key={element.name} className="property-wrapper">
              {element.content}
            </div>
          ))}
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}