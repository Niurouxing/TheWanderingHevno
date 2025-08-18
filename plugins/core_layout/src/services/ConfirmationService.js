/**
 * 一个用于管理全局确认对话框状态的无UI服务。
 * 使用发布-订阅模式来通知UI组件进行更新。
 */
export class ConfirmationService {
  constructor() {
    this.state = {
      open: false,
      title: '',
      message: '',
    };
    this.resolvePromise = null;
    this.listener = null; // 用于通知React组件更新的订阅者
  }

  /**
   * 供React组件订阅状态变化。
   * @param {Function} listener - 当状态改变时要调用的回调函数。
   */
  subscribe(listener) {
    this.listener = listener;
  }
  
  /**
   * 取消订阅。
   */
  unsubscribe() {
    this.listener = null;
  }

  /**
   * 触发一个确认流程。
   * @param {object} options - { title: string, message: string }
   * @returns {Promise<boolean>} - 用户确认时解析为 true，否则为 false。
   */
  confirm(options) {
    return new Promise((resolve) => {
      this.state = {
        open: true,
        title: options.title || '请确认',
        message: options.message || '您确定要执行此操作吗？',
      };
      this.resolvePromise = resolve;
      this.notify(); // 通知UI更新
    });
  }

  handleConfirm = () => {
    if (this.resolvePromise) {
      this.resolvePromise(true);
    }
    this.state.open = false;
    this.notify();
  };

  handleClose = () => {
    if (this.resolvePromise) {
      this.resolvePromise(false);
    }
    this.state.open = false;
    this.notify();
  };
  
  /**
   * 通知订阅者状态已改变。
   */
  notify() {
    if (this.listener) {
      this.listener({ ...this.state });
    }
  }
}
