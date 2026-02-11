"""
Backend integration module - GUI and backend system integration layer

This module provides integration between GUI and existing backend systems.
"""

__version__ = "0.1.0"

from .gui_orchestrator import GUIOrchestrator
from .signal_handler import SignalHandler
from .chrome_debug_manager import ChromeDebugManager, check_and_start_chrome_debug
from .gui_config_manager import GUIConfigManager

__all__ = [
    "GUIOrchestrator",
    "SignalHandler",
    "ChromeDebugManager",
    "check_and_start_chrome_debug",
    "GUIConfigManager",
]
