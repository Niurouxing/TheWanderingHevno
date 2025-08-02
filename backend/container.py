# backend/container.py

import os
from dotenv import load_dotenv

from backend.core.hooks import HookManager
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry
from backend.core.state import SnapshotStore
from backend.persistence.service import PersistenceService
from backend.llm.manager import KeyPoolManager, CredentialManager
from backend.llm.registry import provider_registry
from backend.core.services import service_registry
from backend.core.reporting import auditor_registry, Auditor, Reportable
from backend.runtimes.reporters import RuntimeReporter
from backend.llm.reporters import LLMProviderReporter
from backend.api.reporters import SandboxStatsReporter

# 这是一个简单的依赖注入容器类
# 我们可以使用现成的库如 `dependency-injector`，但为了清晰，我们手动实现一个
class Container:
    def __init__(self):
        # 延迟加载，只有在被访问时才创建实例
        self._execution_engine = None
        self._persistence_service = None
        self._snapshot_store = None
        self._sandbox_store = None
        self._auditor = None
        self._hook_manager = None

    @property
    def hook_manager(self) -> HookManager:
        if self._hook_manager is None:
            self._hook_manager = HookManager()
        return self._hook_manager

    @property
    def snapshot_store(self) -> SnapshotStore:
        if self._snapshot_store is None:
            self._snapshot_store = SnapshotStore()
        return self._snapshot_store

    @property
    def sandbox_store(self) -> dict:
        if self._sandbox_store is None:
            self._sandbox_store = {}
        return self._sandbox_store

    @property
    def persistence_service(self) -> PersistenceService:
        if self._persistence_service is None:
            assets_dir = os.getenv("HEVNO_ASSETS_DIR", "hevno_project/assets")
            self._persistence_service = PersistenceService(assets_base_dir=assets_dir)
        return self._persistence_service
    
    def _create_llm_service(self):
        """
        这个函数现在是容器的私有方法，与 app.py 完全解耦。
        """
        is_debug_mode = os.getenv("HEVNO_LLM_DEBUG_MODE", "false").lower() == "true"
        
        if is_debug_mode:
            MockLLMServiceClass = service_registry.get_class("mock_llm")
            if not MockLLMServiceClass: raise RuntimeError("MockLLMService not registered!")
            return MockLLMServiceClass()

        LLMServiceClass = service_registry.get_class("llm")
        if not LLMServiceClass: raise RuntimeError("LLMService not registered!")
        
        provider_registry.instantiate_all()
        cred_manager = CredentialManager()
        key_manager = KeyPoolManager(credential_manager=cred_manager)
        
        for name, info in provider_registry.get_all_provider_info().items():
            key_manager.register_provider(name, info.key_env_var)

        return LLMServiceClass(
            key_manager=key_manager,
            provider_registry=provider_registry,
            max_retries=3
        )

    @property
    def execution_engine(self) -> ExecutionEngine:
        if self._execution_engine is None:
            services = {"llm": self._create_llm_service()}
            self._execution_engine = ExecutionEngine(
                registry=runtime_registry,
                services=services,
                hook_manager=self.hook_manager 
            )
        return self._execution_engine

    @property
    def auditor(self) -> Auditor:
        if self._auditor is None:
            # 确保报告者只被注册一次
            if not auditor_registry.get_all():
                auditor_registry.register(RuntimeReporter())
                auditor_registry.register(LLMProviderReporter())
                # 注意：这里我们传递了对容器属性的引用
                auditor_registry.register(SandboxStatsReporter(self.sandbox_store, self.snapshot_store))
            self._auditor = Auditor(auditor_registry)
        return self._auditor

# 加载环境变量，以便容器可以访问它们
load_dotenv()

# 创建一个全局的容器实例，供应用和测试使用
container = Container()