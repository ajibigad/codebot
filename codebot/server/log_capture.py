"""Log capture and storage system for task execution logs."""

import sys
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from codebot.core.storage import TaskStorage


class LogStorage:
    """Thread-safe log storage for in-memory (running tasks) and database persistence."""
    
    def __init__(self, storage: Optional[TaskStorage] = None, max_log_lines: int = 10000):
        """
        Initialize log storage.
        
        Args:
            storage: Optional TaskStorage instance for persistence
            max_log_lines: Maximum number of log lines per task
        """
        self.storage = storage
        self.max_log_lines = max_log_lines
        self._logs: Dict[str, List[Dict[str, str]]] = {}
        self._lock = threading.Lock()
    
    def add_log(self, task_id: str, source: str, message: str) -> None:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "message": message
        }
        
        with self._lock:
            if task_id not in self._logs:
                self._logs[task_id] = []
            
            logs = self._logs[task_id]
            logs.append(log_entry)
            
            if len(logs) > self.max_log_lines:
                logs.pop(0)
    
    def get_logs(self, task_id: str, source_filter: Optional[str] = None) -> List[Dict[str, str]]:
        with self._lock:
            logs = self._logs.get(task_id, [])
            if source_filter:
                return [log for log in logs if log["source"] == source_filter]
            return logs.copy()
    
    def persist_logs(self, task_id: str) -> None:
        """
        Persist logs to database and remove from memory.
        
        Args:
            task_id: Task ID
        """
        if not self.storage:
            return
        
        with self._lock:
            logs = self._logs.get(task_id, [])
            if not logs:
                return
            
            if hasattr(self.storage, 'update_task_logs'):
                self.storage.update_task_logs(task_id, logs)
            
            if task_id in self._logs:
                del self._logs[task_id]
    
    def has_logs(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._logs and len(self._logs[task_id]) > 0
    
    def cleanup_old_logs(self, retention_days: int = 30) -> None:
        """
        Clean up old logs from database.
        
        Args:
            retention_days: Number of days to retain logs
        """
        if not self.storage or not hasattr(self.storage, 'cleanup_old_logs'):
            return
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        self.storage.cleanup_old_logs(cutoff_date)


class LogStreamWriter:
    """File-like object that writes directly to log storage in real-time."""
    
    def __init__(self, log_storage: LogStorage, task_id: str, source: str, original_stream):
        self.log_storage = log_storage
        self.task_id = task_id
        self.source = source
        self.original_stream = original_stream
        self._buffer = ""
    
    def write(self, message: str) -> int:
        if not message:
            return 0
        
        self.original_stream.write(message)
        self.original_stream.flush()
        
        self._buffer += message
        lines = self._buffer.split('\n')
        self._buffer = lines[-1]
        
        for line in lines[:-1]:
            if line.strip():
                self.log_storage.add_log(self.task_id, self.source, line)
        
        return len(message)
    
    def flush(self) -> None:
        self.original_stream.flush()
        if self._buffer.strip():
            self.log_storage.add_log(self.task_id, self.source, self._buffer.rstrip('\n\r'))
            self._buffer = ""


class LogCapture:
    """Context manager for capturing stdout/stderr and routing to log storage."""
    
    def __init__(self, log_storage: LogStorage, task_id: str, source: str):
        self.log_storage = log_storage
        self.task_id = task_id
        self.source = source
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._stdout_writer = None
        self._stderr_writer = None
    
    def __enter__(self):
        self._stdout_writer = LogStreamWriter(self.log_storage, self.task_id, self.source, self._original_stdout)
        self._stderr_writer = LogStreamWriter(self.log_storage, self.task_id, self.source, self._original_stderr)
        sys.stdout = self._stdout_writer
        sys.stderr = self._stderr_writer
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        
        if self._stdout_writer:
            self._stdout_writer.flush()
        if self._stderr_writer:
            self._stderr_writer.flush()
        
        return False
    
    def write(self, message: str) -> None:
        if message:
            for line in message.splitlines():
                if line.strip():
                    self.log_storage.add_log(self.task_id, self.source, line)


global_log_storage: Optional[LogStorage] = None


def get_log_storage(storage: Optional[TaskStorage] = None) -> LogStorage:
    """
    Get or create global log storage instance.
    
    Args:
        storage: Optional TaskStorage instance (only used on first call)
        
    Returns:
        LogStorage instance
    """
    global global_log_storage
    if global_log_storage is None:
        global_log_storage = LogStorage(storage=storage)
    return global_log_storage

