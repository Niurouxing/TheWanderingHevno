import React, { useState, useEffect } from 'react';
import { Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Button } from '@mui/material';

export function GlobalConfirmationDialog({ service }) {
  const [state, setState] = useState({ open: false, title: '', message: '' });

  useEffect(() => {
    // 组件挂载时，订阅服务
    service.subscribe(setState);
    // 组件卸载时，取消订阅
    return () => service.unsubscribe();
  }, [service]);

  if (!state.open) {
    return null;
  }

  return (
    <Dialog
      open={state.open}
      onClose={service.handleClose}
    >
      <DialogTitle>{state.title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{state.message}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={service.handleClose}>取消</Button>
        <Button onClick={service.handleConfirm} color="primary" autoFocus>
          确认
        </Button>
      </DialogActions>
    </Dialog>
  );
}
