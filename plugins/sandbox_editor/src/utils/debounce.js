/**
 * @fileoverview 防抖工具函数.
 * 在事件触发后延迟执行函数，如果在该延迟时间内再次触发，则重置计时器。
 */

export const debounce = (func, delay) => {
  let timeout;
  return function(...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), delay);
  };
};
