// plugins/core_goliath/src/components/editor/ScopeSelector.jsx

import React from 'react';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Tooltip from '@mui/material/Tooltip';

const scopes = [
    { value: 'definition', label: 'Blueprint', tooltip: "Edit the sandbox's initial template. Changes are permanent and do not create history." },
    { value: 'lore', label: 'Codex', tooltip: 'Edit core world rules, graphs, and knowledge. Changes are permanent and do not create history.' },
    { value: 'moment', label: 'History', tooltip: 'View and edit the world state at specific moments. Changes will create new history branches.' },
];

export default function ScopeSelector({ activeScope, onChange }) {
    
    const handleChange = (event, newScope) => {
        if (newScope !== null) {
            onChange(newScope);
        }
    };

    return (
        <ToggleButtonGroup
            color="primary"
            value={activeScope}
            exclusive
            onChange={handleChange}
            aria-label="Editor Scope"
        >
            {scopes.map(scope => (
                <Tooltip key={scope.value} title={scope.tooltip} arrow>
                    <ToggleButton value={scope.value}>
                        {scope.label}
                    </ToggleButton>
                </Tooltip>
            ))}
        </ToggleButtonGroup>
    );
}