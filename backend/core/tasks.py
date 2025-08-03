# backend/core/tasks.py

import asyncio
import logging
from typing import Callable, Coroutine, Any, List

# 从核心契约中导入 Container 接口
from backend.core.contracts import Container, BackgroundTaskManager as BackgroundTaskManagerInterface

logger = logging.getLogger(__name__)

class BackgroundTaskManager(BackgroundTaskManagerInterface):
    """一个简单的、通用的后台任务管理器。"""
    def __init__(self, container: Container, max_workers: int = 3):
        self._container = container
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._max_workers = max_workers
        self._is_running = False

    def start(self):
        """启动工作者协程。"""
        if self._is_running:
            logger.warning("BackgroundTaskManager is already running.")
            return
            
        logger.info(f"正在启动 {self._max_workers} 个后台工作者...")
        for i in range(self._max_workers):
            worker_task = asyncio.create_task(self._worker(f"后台工作者-{i}"))
            self._workers.append(worker_task)
        self._is_running = True

    async def stop(self):
        """优雅地停止所有工作者。"""
        if not self._is_running:
            return
            
        logger.info("正在停止后台工作者...")
        # 等待队列中的所有任务被处理完毕
        await self._queue.join()
        
        # 取消所有工作者协程
        for worker in self._workers:
            worker.cancel()
            
        # 等待所有工作者协程完全停止
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._is_running = False
        logger.info("所有后台工作者已安全停止。")

    def submit_task(self, coro_func: Callable[..., Coroutine], *args: Any, **kwargs: Any):
        """
        向队列提交一个任务。
        
        :param coro_func: 要在后台执行的协程函数。
        :param args, kwargs: 传递给协程函数的参数。
        """
        if not self._is_running:
            logger.error("无法提交任务：后台任务管理器尚未启动。")
            return
            
        # 我们将协程函数本身和它的参数一起放入队列
        self._queue.put_nowait((coro_func, args, kwargs))
        logger.debug(f"任务 '{coro_func.__name__}' 已提交到后台队列。")

    async def _worker(self, name: str):
        """
        工作者协程，它会持续从队列中获取并执行任务。
        """
        logger.info(f"后台工作者 '{name}' 已启动。")
        while True:
            try:
                # 从队列中阻塞式地获取任务
                coro_func, args, kwargs = await self._queue.get()
                
                logger.debug(f"工作者 '{name}' 获取到任务: {coro_func.__name__}")
                try:
                    # 【关键】执行协程函数。
                    # 我们将容器实例作为第一个参数注入，以便后台任务能解析它需要的任何服务。
                    await coro_func(self._container, *args, **kwargs)
                except Exception:
                    logger.exception(f"工作者 '{name}' 在执行任务 '{coro_func.__name__}' 时遇到错误。")
                finally:
                    # 标记任务完成，以便 queue.join() 可以正确工作
                    self._queue.task_done()
            
            except asyncio.CancelledError:
                logger.info(f"后台工作者 '{name}' 正在关闭。")
                break