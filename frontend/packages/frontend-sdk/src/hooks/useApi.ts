import { useState, useCallback, useEffect } from 'react';

/**
 * useApi Hook 的状态结构。
 */
export interface UseApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
}

/**
 * useApi Hook 的配置选项。
 */
export interface UseApiOptions {
  /**
   * 如果为 `true`，则在组件首次挂载时立即执行API调用。
   * @default true
   */
  immediate?: boolean;
}

/**
 * useApi Hook 的返回值。
 */
export interface UseApiReturn<T, TArgs extends any[]> extends UseApiState<T> {
  /**
   * 手动执行API调用的函数。
   * @param args 传递给原始apiCall函数的参数。
   * @returns 返回一个Promise，该Promise在API调用成功时解析为数据，在失败时拒绝。
   */
  execute: (...args: TArgs) => Promise<T>;
}

/**
 * 一个用于与后端API交互的通用React Hook。
 * 它抽象了数据获取过程中的加载状态、错误处理和数据存储。
 *
 * @template T - API调用成功时返回的数据类型。
 * @template TArgs - 原始API调用函数所接受的参数类型数组。
 *
 * @param apiCall - 一个返回Promise的函数，通常是调用APIService的方法。
 *   **最佳实践**: 为了防止不必要的重新渲染，请使用 `useCallback` 包装传递给此处的 `apiCall` 函数。
 * @param options - 配置Hook行为的选项对象。
 *
 * @returns 返回一个包含 `data`, `isLoading`, `error` 状态和 `execute` 函数的对象。
 */
export function useApi<T, TArgs extends any[] = []>(
  apiCall: (...args: TArgs) => Promise<T>,
  options: UseApiOptions = {}
): UseApiReturn<T, TArgs> {
  const { immediate = true } = options;

  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    isLoading: immediate, // 如果立即执行，初始状态就是加载中
    error: null,
  });

  const execute = useCallback(
    async (...args: TArgs): Promise<T> => {
      setState(prevState => ({ ...prevState, isLoading: true, error: null }));
      try {
        const result = await apiCall(...args);
        setState(prevState => ({ ...prevState, data: result, isLoading: false }));
        return result;
      } catch (err) {
        // 确保错误是一个 Error 对象
        const error = err instanceof Error ? err : new Error(String(err));
        setState(prevState => ({ ...prevState, error, isLoading: false, data: null }));
        throw error; // 将错误重新抛出，以便调用者可以进一步处理
      }
    },
    [apiCall] // 依赖于 apiCall 函数的引用
  );

  useEffect(() => {
    if (immediate) {
      // 当立即执行时，我们假设它不需要参数。
      // 如果需要带参数的立即执行，调用者应使用 useEffect 和 execute 手动处理。
      (execute as () => Promise<T>)();
    }
  }, [execute, immediate]);

  return { ...state, execute };
}