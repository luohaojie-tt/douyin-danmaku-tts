"""
Chrome Debug Mode Manager - Automatically manage Chrome debug mode startup

This module provides utilities to check if Chrome is running in debug mode
and automatically start it if needed.
"""

import logging
import socket
import subprocess
import time
import sys
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ChromeDebugManager:
    """
    Manages Chrome debug mode lifecycle
    
    Automatically checks if Chrome is running with remote debugging enabled
    and starts it if necessary.
    """
    
    DEFAULT_DEBUG_PORT = 9222
    DEFAULT_CHROME_PATHS = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe",
    ]
    
    def __init__(
        self,
        debug_port: int = DEFAULT_DEBUG_PORT,
        chrome_path: Optional[str] = None,
        user_data_dir: str = "C:\\chrome_debug_temp"
    ):
        """
        Initialize Chrome debug manager
        
        Args:
            debug_port: Chrome remote debugging port (default: 9222)
            chrome_path: Path to Chrome executable (auto-detected if None)
            user_data_dir: Chrome user data directory for debug session
        """
        self.debug_port = debug_port
        self.chrome_path = chrome_path or self._find_chrome()
        self.user_data_dir = user_data_dir
        
        if not self.chrome_path:
            logger.warning("Chrome executable not found")
        else:
            logger.debug(f"Chrome path: {self.chrome_path}")
    
    def _find_chrome(self) -> Optional[str]:
        """
        Auto-detect Chrome executable path
        
        Returns:
            Chrome path if found, None otherwise
        """
        # Try default paths
        for path in self.DEFAULT_CHROME_PATHS:
            # Format path with current username if needed
            if "{}" in path:
                path = path.format(getattr(Path, 'home')() or Path.home())
            
            if Path(path).exists():
                logger.debug(f"Found Chrome at: {path}")
                return path
        
        # Try using 'where' command on Windows
        if sys.platform == 'win32':
            try:
                result = subprocess.run(
                    ['where', 'chrome.exe'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout:
                    chrome_path = result.stdout.strip().split('\n')[0]
                    if Path(chrome_path).exists():
                        logger.debug(f"Found Chrome via 'where': {chrome_path}")
                        return chrome_path
            except Exception as e:
                logger.debug(f"Failed to find Chrome via 'where': {e}")
        
        return None
    
    def is_chrome_debug_running(self) -> bool:
        """
        Check if Chrome is running with remote debugging enabled
        
        Returns:
            True if Chrome debug port is accessible
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', self.debug_port))
                is_running = result == 0
                
                if is_running:
                    logger.debug(f"Chrome debug port {self.debug_port} is open")
                else:
                    logger.debug(f"Chrome debug port {self.debug_port} is not accessible")
                
                return is_running
        
        except Exception as e:
            logger.error(f"Error checking Chrome debug port: {e}")
            return False
    
    def kill_existing_chrome(self) -> bool:
        """
        Kill all Chrome processes
        
        WARNING: This will close ALL Chrome windows!
        
        Returns:
            True if successful
        """
        try:
            logger.info("正在关闭所有Chrome进程...")
            
            if sys.platform == 'win32':
                # Windows: use taskkill
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'chrome.exe'],
                    capture_output=True,
                    timeout=10
                )
            else:
                # Unix-like: use pkill
                subprocess.run(
                    ['pkill', '-f', 'chrome'],
                    capture_output=True,
                    timeout=10
                )
            
            # Wait for processes to terminate
            time.sleep(2)
            
            logger.info("Chrome进程已关闭")
            return True
        
        except Exception as e:
            logger.error(f"关闭Chrome进程失败: {e}")
            return False
    
    def start_chrome_debug_mode(
        self,
        kill_existing: bool = False,
        wait_timeout: int = 10
    ) -> Tuple[bool, str]:
        """
        Start Chrome in debug mode
        
        Args:
            kill_existing: Whether to kill existing Chrome processes first
            wait_timeout: Maximum seconds to wait for Chrome to start
        
        Returns:
            Tuple of (success, message)
        """
        if not self.chrome_path:
            return False, "Chrome未安装或路径未找到"
        
        # Check if already running
        if self.is_chrome_debug_running():
            logger.info("Chrome调试模式已在运行")
            return True, "Chrome调试模式已在运行"
        
        # Kill existing Chrome if requested
        if kill_existing:
            if not self.kill_existing_chrome():
                logger.warning("关闭Chrome进程失败，继续尝试启动...")
        
        # Start Chrome
        try:
            logger.info(f"正在启动Chrome调试模式 (端口: {self.debug_port})...")
            logger.info(f"用户数据目录: {self.user_data_dir}")
            
            # Build command
            cmd = [
                self.chrome_path,
                f'--remote-debugging-port={self.debug_port}',
                f'--user-data-dir={self.user_data_dir}'
            ]
            
            # Start Chrome (non-blocking)
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for Chrome to start
            logger.info("等待Chrome启动...")
            start_time = time.time()
            
            while time.time() - start_time < wait_timeout:
                time.sleep(0.5)
                if self.is_chrome_debug_running():
                    elapsed = time.time() - start_time
                    logger.info(f"✓ Chrome调试模式启动成功 (耗时: {elapsed:.1f}秒)")
                    return True, f"Chrome调试模式启动成功 (耗时: {elapsed:.1f}秒)"
            
            # Timeout
            logger.error(f"Chrome启动超时 ({wait_timeout}秒)")
            return False, f"Chrome启动超时 ({wait_timeout}秒)"
        
        except Exception as e:
            error_msg = f"启动Chrome失败: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def ensure_chrome_debug_mode(
        self,
        kill_existing: bool = False,
        wait_timeout: int = 10
    ) -> Tuple[bool, str]:
        """
        Ensure Chrome debug mode is running (start if not)
        
        Args:
            kill_existing: Whether to kill existing Chrome processes first
            wait_timeout: Maximum seconds to wait for Chrome to start
        
        Returns:
            Tuple of (success, message)
        """
        if self.is_chrome_debug_running():
            return True, "Chrome调试模式已在运行"
        
        return self.start_chrome_debug_mode(
            kill_existing=kill_existing,
            wait_timeout=wait_timeout
        )
    
    def get_chrome_version(self) -> Optional[str]:
        """
        Get Chrome version
        
        Returns:
            Chrome version string if found, None otherwise
        """
        if not self.chrome_path:
            return None
        
        try:
            result = subprocess.run(
                [self.chrome_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.debug(f"Chrome version: {version}")
                return version
        
        except Exception as e:
            logger.debug(f"Failed to get Chrome version: {e}")
        
        return None


def check_and_start_chrome_debug(
    debug_port: int = 9222,
    kill_existing: bool = False,
    wait_timeout: int = 10
) -> Tuple[bool, str]:
    """
    Convenience function to check and start Chrome debug mode
    
    Args:
        debug_port: Chrome remote debugging port
        kill_existing: Whether to kill existing Chrome processes
        wait_timeout: Maximum seconds to wait for Chrome to start
    
    Returns:
        Tuple of (success, message)
    
    Example:
        success, message = check_and_start_chrome_debug()
        if success:
            print(f"Chrome ready: {message}")
        else:
            print(f"Chrome error: {message}")
    """
    manager = ChromeDebugManager(debug_port=debug_port)
    return manager.ensure_chrome_debug_mode(
        kill_existing=kill_existing,
        wait_timeout=wait_timeout
    )
