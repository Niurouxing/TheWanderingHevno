# plugins/core_diagnostics/contracts.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class Reportable(ABC):
    @property
    @abstractmethod
    def report_key(self) -> str: pass
    
    @property
    def is_static(self) -> bool: return True
    
    @abstractmethod
    async def generate_report(self) -> Any: pass

class AuditorInterface(ABC):
    @abstractmethod
    async def generate_full_report(self) -> Dict[str, Any]: raise NotImplementedError
    @abstractmethod
    def set_reporters(self, reporters: List['Reportable']) -> None: raise NotImplementedError