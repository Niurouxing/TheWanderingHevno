# tests/test_platform_core.py

import pytest
import asyncio
from unittest.mock import MagicMock

from backend.container import Container
from backend.core.hooks import HookManager

class TestContainer:
    """对 DI 容器的单元测试。"""
    
    def test_register_and_resolve_singleton(self):
        """测试单例服务的注册和解析。"""
        container = Container()
        
        # 使用 MagicMock 来追踪工厂函数的调用
        mock_factory = MagicMock(return_value="service_instance")
        
        container.register("my_service", mock_factory, singleton=True)
        
        # 第一次解析
        instance1 = container.resolve("my_service")
        assert instance1 == "service_instance"
        mock_factory.assert_called_once() # 工厂只应被调用一次

        # 第二次解析
        instance2 = container.resolve("my_service")
        assert instance2 == "service_instance"
        assert instance1 is instance2 # 应该是同一个实例
        mock_factory.assert_called_once() # 工厂仍然只被调用一次

    def test_register_and_resolve_transient(self):
        """测试非单例（瞬态）服务的注册和解析。"""
        container = Container()
        mock_factory = MagicMock(side_effect=["instance1", "instance2"])
        
        container.register("my_service", mock_factory, singleton=False)

        instance1 = container.resolve("my_service")
        assert instance1 == "instance1"
        assert mock_factory.call_count == 1

        instance2 = container.resolve("my_service")
        assert instance2 == "instance2"
        assert instance1 is not instance2 # 应该是不同的实例
        assert mock_factory.call_count == 2
        
    def test_resolve_nonexistent_service(self):
        """测试解析一个未注册的服务时应抛出异常。"""
        container = Container()
        with pytest.raises(ValueError, match="Service 'nonexistent' not found"):
            container.resolve("nonexistent")

    def test_factory_with_container_dependency(self):
        """测试工厂函数可以接收容器本身作为依赖。"""
        container = Container()
        
        def dependent_factory(c: Container):
            # 这个工厂依赖于 'base_service'
            base = c.resolve("base_service")
            return f"dependent_on_{base}"
            
        container.register("base_service", lambda: "base_instance")
        container.register("dependent_service", dependent_factory)
        
        result = container.resolve("dependent_service")
        assert result == "dependent_on_base_instance"


@pytest.mark.asyncio
class TestHookManager:
    """对事件总线 HookManager 的单元测试。"""

    async def test_filter_hook(self):
        """测试 filter 钩子的链式处理和优先级。"""
        hook_manager = HookManager()
        
        # 定义两个钩子实现
        async def low_priority_filter(data: list, **kwargs):
            data.append("low")
            return data

        async def high_priority_filter(data: list, **kwargs):
            data.append("high")
            return data

        # 以错误的优先级顺序注册
        hook_manager.add_implementation("test_filter", low_priority_filter, priority=20)
        hook_manager.add_implementation("test_filter", high_priority_filter, priority=10)
        
        initial_data = ["start"]
        result = await hook_manager.filter("test_filter", initial_data)
        
        # 因为 high_priority_filter 的优先级更高(10 < 20)，它应该先执行
        assert result == ["start", "high", "low"]

    async def test_trigger_hook(self):
        """测试 trigger 钩子的并发执行。"""
        hook_manager = HookManager()
        
        # 使用一个列表来记录调用顺序（尽管是并发的）
        call_log = []
        
        async def hook1(**kwargs):
            await asyncio.sleep(0.02)
            call_log.append("hook1")

        async def hook2(**kwargs):
            call_log.append("hook2")

        hook_manager.add_implementation("test_trigger", hook1)
        hook_manager.add_implementation("test_trigger", hook2)

        await hook_manager.trigger("test_trigger")

        # 因为是并发执行，我们只关心它们是否都被调用了
        assert "hook1" in call_log
        assert "hook2" in call_log
        assert len(call_log) == 2

    async def test_hooks_with_no_implementations(self):
        """测试在没有实现的情况下调用钩子不会出错。"""
        hook_manager = HookManager()
        
        # Filter 应该原样返回数据
        result = await hook_manager.filter("nonexistent_filter", "data")
        assert result == "data"
        
        # Trigger 应该什么都不做
        try:
            await hook_manager.trigger("nonexistent_trigger")
        except Exception:
            pytest.fail("Triggering a hook with no implementations should not raise an error.")