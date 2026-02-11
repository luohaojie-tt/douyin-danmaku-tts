"""
Signal Handler - Manages Qt signal-slot connections for GUI

This module provides utilities for connecting GUIOrchestrator signals
to UI widget slots in a thread-safe manner.
"""

import logging
from typing import Optional, Callable

from PyQt5.QtCore import QObject, Qt, pyqtSlot, QMutex, QMutexLocker
from PyQt5.QtWidgets import QWidget

from .gui_orchestrator import GUIOrchestrator

logger = logging.getLogger(__name__)


class SignalHandler(QObject):
    """
    Manages signal-slot connections between backend and frontend
    
    Provides thread-safe connection and disconnection of signals,
    along with automatic cleanup on destruction.
    """
    
    def __init__(self, orchestrator: GUIOrchestrator, parent: Optional[QObject] = None):
        """
        Initialize signal handler
        
        Args:
            orchestrator: GUIOrchestrator instance
            parent: Parent QObject (optional)
        """
        super().__init__(parent)
        
        self.orchestrator = orchestrator
        self._mutex = QMutex()
        self._connections: dict[str, list[tuple[QObject, Callable]]] = {
            "message_received": [],
            "connection_changed": [],
            "error_occurred": [],
            "stats_updated": []
        }
        
        logger.info("SignalHandler initialized")
    
    def connect_message_received(
        self,
        receiver: QObject,
        slot: Callable[[str, str, str], None]
    ) -> bool:
        """
        Connect message_received signal to a slot
        
        Args:
            receiver: QObject receiving the signal
            slot: Slot function with signature (user_name: str, content: str, timestamp: str)
        
        Returns:
            bool: True if connection successful
        """
        try:
            with QMutexLocker(self._mutex):
                # Use Qt.QueuedConnection for thread safety
                self.orchestrator.message_received.connect(
                    slot,
                    Qt.QueuedConnection
                )
                self._connections["message_received"].append((receiver, slot))
            
            logger.debug(f"Connected message_received to {receiver}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect message_received: {e}")
            return False
    
    def connect_connection_changed(
        self,
        receiver: QObject,
        slot: Callable[[bool, str], None]
    ) -> bool:
        """
        Connect connection_changed signal to a slot
        
        Args:
            receiver: QObject receiving the signal
            slot: Slot function with signature (connected: bool, message: str)
        
        Returns:
            bool: True if connection successful
        """
        try:
            with QMutexLocker(self._mutex):
                self.orchestrator.connection_changed.connect(
                    slot,
                    Qt.QueuedConnection
                )
                self._connections["connection_changed"].append((receiver, slot))
            
            logger.debug(f"Connected connection_changed to {receiver}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect connection_changed: {e}")
            return False
    
    def connect_error_occurred(
        self,
        receiver: QObject,
        slot: Callable[[str, str], None]
    ) -> bool:
        """
        Connect error_occurred signal to a slot
        
        Args:
            receiver: QObject receiving the signal
            slot: Slot function with signature (error_type: str, error_message: str)
        
        Returns:
            bool: True if connection successful
        """
        try:
            with QMutexLocker(self._mutex):
                self.orchestrator.error_occurred.connect(
                    slot,
                    Qt.QueuedConnection
                )
                self._connections["error_occurred"].append((receiver, slot))
            
            logger.debug(f"Connected error_occurred to {receiver}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect error_occurred: {e}")
            return False
    
    def connect_stats_updated(
        self,
        receiver: QObject,
        slot: Callable[[dict], None]
    ) -> bool:
        """
        Connect stats_updated signal to a slot
        
        Args:
            receiver: QObject receiving the signal
            slot: Slot function with signature (stats: dict)
        
        Returns:
            bool: True if connection successful
        """
        try:
            with QMutexLocker(self._mutex):
                self.orchestrator.stats_updated.connect(
                    slot,
                    Qt.QueuedConnection
                )
                self._connections["stats_updated"].append((receiver, slot))
            
            logger.debug(f"Connected stats_updated to {receiver}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect stats_updated: {e}")
            return False
    
    def disconnect_all(self) -> bool:
        """
        Disconnect all signals
        
        Returns:
            bool: True if disconnection successful
        """
        try:
            with QMutexLocker(self._mutex):
                # Disconnect message_received
                for receiver, slot in self._connections["message_received"]:
                    try:
                        self.orchestrator.message_received.disconnect(slot)
                    except Exception as e:
                        logger.warning(f"Failed to disconnect message_received: {e}")
                self._connections["message_received"].clear()
                
                # Disconnect connection_changed
                for receiver, slot in self._connections["connection_changed"]:
                    try:
                        self.orchestrator.connection_changed.disconnect(slot)
                    except Exception as e:
                        logger.warning(f"Failed to disconnect connection_changed: {e}")
                self._connections["connection_changed"].clear()
                
                # Disconnect error_occurred
                for receiver, slot in self._connections["error_occurred"]:
                    try:
                        self.orchestrator.error_occurred.disconnect(slot)
                    except Exception as e:
                        logger.warning(f"Failed to disconnect error_occurred: {e}")
                self._connections["error_occurred"].clear()
                
                # Disconnect stats_updated
                for receiver, slot in self._connections["stats_updated"]:
                    try:
                        self.orchestrator.stats_updated.disconnect(slot)
                    except Exception as e:
                        logger.warning(f"Failed to disconnect stats_updated: {e}")
                self._connections["stats_updated"].clear()
            
            logger.info("All signals disconnected")
            return True
        
        except Exception as e:
            logger.error(f"Failed to disconnect signals: {e}")
            return False
    
    def get_connection_count(self) -> dict[str, int]:
        """
        Get count of active connections
        
        Returns:
            Dictionary with connection counts per signal
        """
        with QMutexLocker(self._mutex):
            return {
                signal_name: len(connections)
                for signal_name, connections in self._connections.items()
            }


class AsyncioEventLoopBridge(QObject):
    """
    Bridge between asyncio event loop and Qt event loop
    
    Uses QTimer to periodically process asyncio tasks within Qt event loop.
    """
    
    def __init__(self, loop: asyncio.AbstractEventLoop, parent: Optional[QObject] = None):
        """
        Initialize bridge
        
        Args:
            loop: asyncio event loop
            parent: Parent QObject (optional)
        """
        super().__init__(parent)
        
        self._loop = loop
        self._timer = None
        self._is_running = False
        
        logger.info("AsyncioEventLoopBridge initialized")
    
    def start_integration(self, interval_ms: int = 10):
        """
        Start processing asyncio events in Qt event loop
        
        Args:
            interval_ms: Timer interval in milliseconds (default: 10ms)
        """
        if self._is_running:
            logger.warning("Bridge already running")
            return
        
        from PyQt5.QtCore import QTimer
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_asyncio_events)
        self._timer.start(interval_ms)
        
        self._is_running = True
        logger.info(f"Asyncio-Qt integration started (interval: {interval_ms}ms)")
    
    def stop_integration(self):
        """Stop asyncio event processing"""
        if not self._is_running:
            return
        
        if self._timer:
            self._timer.stop()
            self._timer = None
        
        self._is_running = False
        logger.info("Asyncio-Qt integration stopped")
    
    def _process_asyncio_events(self):
        """Process pending asyncio events (called by QTimer)"""
        if self._loop and not self._loop.is_closed():
            # Process one iteration of asyncio event loop
            self._loop.call_soon(self._loop.stop)
            self._loop.run_forever()
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_integration()
