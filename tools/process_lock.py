import os
import sys
import tempfile
import psutil
from typing import Optional

class ProcessLock:
    def __init__(self, lock_name: str = "aura_shell_update"):
        self.lock_name = lock_name
        self.lockfile: Optional[object] = None
        self.lockfile_path = os.path.join(
            tempfile.gettempdir(),
            f"{lock_name}.lock"
        )
    
    def _is_process_running(self, pid: int) -> bool:
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    
    def _clean_stale_lock(self) -> bool:
        if not os.path.exists(self.lockfile_path):
            return True
        
        try:
            with open(self.lockfile_path, 'r') as f:
                pid_str = f.read().strip()
                if not pid_str or not pid_str.isdigit():
                    os.remove(self.lockfile_path)
                    return True
                
                pid = int(pid_str)
                if not self._is_process_running(pid):
                    os.remove(self.lockfile_path)
                    return True
        except (IOError, OSError, ValueError):
            try:
                os.remove(self.lockfile_path)
            except:
                pass
            return True
        
        return False
    
    def acquire(self) -> bool:
        try:
            self._clean_stale_lock()
            
            if os.name == 'nt':
                return self._acquire_windows()
            else:
                return self._acquire_unix()
        except Exception:
            return False
    
    def _acquire_windows(self) -> bool:
        try:
            import msvcrt
            self.lockfile = open(self.lockfile_path, 'w')
            msvcrt.locking(self.lockfile.fileno(), msvcrt.LK_NBLCK, 1)
            self.lockfile.write(str(os.getpid()))
            self.lockfile.flush()
            return True
        except (IOError, OSError, ImportError):
            if self.lockfile:
                try:
                    self.lockfile.close()
                except:
                    pass
                self.lockfile = None
            return False
    
    def _acquire_unix(self) -> bool:
        try:
            import fcntl
            self.lockfile = open(self.lockfile_path, 'w')
            fcntl.flock(self.lockfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lockfile.write(str(os.getpid()))
            self.lockfile.flush()
            return True
        except (IOError, OSError, ImportError):
            if self.lockfile:
                try:
                    self.lockfile.close()
                except:
                    pass
                self.lockfile = None
            return False
    
    def release(self):
        if self.lockfile:
            try:
                if os.name == 'nt':
                    import msvcrt
                    try:
                        msvcrt.locking(self.lockfile.fileno(), msvcrt.LK_UNLCK, 1)
                    except:
                        pass
                self.lockfile.close()
            except:
                pass
            finally:
                self.lockfile = None
        
        if os.path.exists(self.lockfile_path):
            try:
                os.remove(self.lockfile_path)
            except:
                pass
    
    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"无法获取进程锁: {self.lock_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False
    
    def __del__(self):
        self.release()