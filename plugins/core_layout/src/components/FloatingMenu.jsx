// plugins/core_layout/src/components/FloatingMenu.jsx
import React, { useState, useRef, useMemo, useEffect } from 'react';
import Draggable from 'react-draggable';
import { useLayout } from '../context/LayoutContext';
import { Box, IconButton, Tooltip } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import * as MuiIcons from '@mui/icons-material';

const DynamicIcon = ({ name }) => {
  const Icon = MuiIcons[name];
  // A simple fallback to avoid rendering errors if an icon name is invalid
  return Icon ? <Icon /> : <div/>;
};

// --- Constants for styling and layout ---
const COLLAPSED_SIZE = 40;
const ICON_SIZE = 40;
const GAP = 10; // The space between icons and from the border
const COLUMNS = 3; // Defines the grid layout

export function FloatingMenu() {
  const { pages, activePageId, setActivePageId } = useLayout();
  const draggableRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  
  // A ref to distinguish between a click and a drag action
  const dragState = useRef({ isDragging: false });

  // Focus the container when it opens to enable the onBlur event for closing
  useEffect(() => {
    if (isOpen) {
      draggableRef.current?.focus({ preventScroll: true });
    }
  }, [isOpen]);

  const actions = useMemo(() => [
    { id: null, title: 'Home', icon: <HomeRoundedIcon /> },
    ...pages
      .filter(page => page.menu) 
      .map(page => ({
        id: page.id,
        title: page.menu.title,
        icon: <DynamicIcon name={page.menu.icon} />
      }))
  ], [pages]);

  // Dynamically calculate the expanded size based on content
  const rows = Math.ceil(actions.length / COLUMNS);
  const EXPANDED_WIDTH = (ICON_SIZE * COLUMNS) + (GAP * (COLUMNS + 1));
  const EXPANDED_HEIGHT = (ICON_SIZE * rows) + (GAP * (rows + 1));

  const handleActionClick = (pageId) => {
    setActivePageId(pageId);
    setIsOpen(false);
  };
  
  // This handler closes the menu if the user clicks outside of it
  const handleBlur = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setIsOpen(false);
    }
  };

  // The stop handler for the drag action, which now decides whether to open the menu
  const handleDragStop = () => {
    if (!dragState.current.isDragging && !isOpen) {
      setIsOpen(true);
    }
    // Reset dragging state after every stop
    dragState.current.isDragging = false;
  };

  const containerSx = {
    width: isOpen ? EXPANDED_WIDTH : COLLAPSED_SIZE,
    height: isOpen ? EXPANDED_HEIGHT : COLLAPSED_SIZE,
    backgroundColor: '#29344B',
    color: '#E7C296',
    borderRadius: isOpen ? '16px' : '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    boxShadow: '0 0 0 0.6px #000, 0 14px 50px -2px rgba(0,0,0,0.95)',
    cursor: isOpen ? 'default' : 'grab',
    overflow: 'hidden',
    transition: `all 0.45s cubic-bezier(0.4, 0, 0.2, 1)`,
    outline: 'none', // Remove focus ring
    '&:active': {
      cursor: isOpen ? 'default' : 'grabbing',
    }
  };

  return (
    <Draggable
      nodeRef={draggableRef}
      bounds="parent"
      disabled={isOpen} // Disable dragging when the menu is open
      onStart={() => { dragState.current.isDragging = false; }}
      onDrag={() => { dragState.current.isDragging = true; }}
      onStop={handleDragStop}
    >
      <Box
        ref={draggableRef}
        sx={{ position: 'absolute', bottom: 24, left: 24, zIndex: 1300 }}
        tabIndex={-1} // Makes the Box focusable for the onBlur event
        onBlur={handleBlur}
      >
        <Box sx={containerSx}>
          {/* Central Menu Icon (only visible when collapsed) */}
          <MenuIcon sx={{
            fontSize: 25,
            opacity: isOpen ? 0 : 1,
            transition: 'opacity 0.2s linear',
          }}/>
          
          {/* Icons Grid */}
          {actions.map((action, index) => {
            const row = Math.floor(index / COLUMNS);
            const col = index % COLUMNS;

            // Cleanly calculate the target position for each icon
            const targetTop = GAP + row * (ICON_SIZE + GAP);
            const targetLeft = GAP + col * (ICON_SIZE + GAP);

            return (
              <Box
                key={action.id || 'home'}
                sx={{
                  position: 'absolute',
                  width: ICON_SIZE,
                  height: ICON_SIZE,
                  // Animate from the center to the grid position
                  top: isOpen ? targetTop : '50%',
                  left: isOpen ? targetLeft : '50%',
                  transform: isOpen ? 'none' : 'translate(-50%, -50%)',
                  opacity: isOpen ? 1 : 0,
                  transition: `all 0.35s cubic-bezier(0.4, 0, 0.2, 1)`,
                  transitionDelay: isOpen ? `${index * 0.03}s` : '0s',
                  pointerEvents: isOpen ? 'all' : 'none',
                }}
              >
                <Tooltip title={action.title} placement="top">
                  <IconButton
                    onClick={() => handleActionClick(action.id)}
                    sx={{
                      width: '100%',
                      height: '100%',
                      color: '#E7C296',
                      backgroundColor: activePageId === action.id ? 'rgba(231, 194, 150, 0.15)' : 'transparent',
                      transform: activePageId === action.id ? 'scale(1.1)' : 'scale(1)',
                      transition: 'background-color 0.2s, transform 0.2s',
                      '&:hover': {
                        backgroundColor: 'rgba(231, 194, 150, 0.25)',
                        transform: 'scale(1.15)'
                      }
                    }}
                  >
                    {action.icon}
                  </IconButton>
                </Tooltip>
              </Box>
            );
          })}
        </Box>
      </Box>
    </Draggable>
  );
}