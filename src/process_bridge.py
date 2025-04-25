"""
Process Bridge - Provides a Process class that uses our C-based fork implementation
while maintaining compatibility with multiprocessing.Process
"""
import os
import sys
import signal
import multiprocessing

# Check if we're on macOS
is_macos = sys.platform == 'darwin'

# Import our C-based process utilities
# Skip importing on macOS due to CoreFoundation fork restrictions
process_utils = None
if not is_macos:
    try:
        import process_utils
        print("Using custom fork()-based process creation")
    except ImportError:
        print("C extension not available, falling back to multiprocessing")
else:
    print("macOS detected, using standard multiprocessing module for compatibility")

class ForkProcess:
    """
    Process class that uses C-based fork() for process creation
    while maintaining compatibility with multiprocessing.Process API
    """
    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self._daemon = daemon
        self.pid = None
        self._started = False
        self._exitcode = None
        
        # For fallback to multiprocessing
        self._process = None
    
    def start(self):
        """Start the process using fork() or multiprocessing"""
        if process_utils and not is_macos:
            # Use our C-based fork implementation
            pid = process_utils.fork()
            if pid == 0:  # Child process
                # We're in the child process
                try:
                    if self.target:
                        self.target(*self.args, **self.kwargs)
                except Exception as e:
                    print(f"Error in process: {e}")
                finally:
                    # Exit child process
                    sys.exit(0)
            else:
                # We're in the parent process
                self.pid = pid
                self._started = True
        else:
            # Fallback to multiprocessing
            self._process = multiprocessing.Process(
                target=self.target,
                args=self.args,
                kwargs=self.kwargs,
                daemon=self._daemon
            )
            self._process.start()
            self.pid = self._process.pid
            self._started = True
    
    def is_alive(self):
        """Check if the process is still running"""
        if not self._started:
            return False
        
        if self._process:
            # Using multiprocessing
            return self._process.is_alive()
        
        # Using fork - check if process exists
        try:
            os.kill(self.pid, 0)  # Sends no signal, just checks if process exists
            return True
        except OSError:
            return False
    
    def join(self, timeout=None):
        """Wait for the process to terminate"""
        if not self._started:
            return
        
        if self._process:
            # Using multiprocessing
            self._process.join(timeout)
            return
        
        # Using fork
        if timeout is not None:
            # With timeout, periodically check if process is alive
            import time
            start_time = time.time()
            while self.is_alive():
                if time.time() - start_time > timeout:
                    return
                time.sleep(0.01)
        else:
            # Without timeout, use waitpid
            try:
                pid, status = process_utils.wait(self.pid)
                self._exitcode = status
            except:
                pass
    
    def terminate(self):
        """Terminate the process"""
        if not self._started:
            return
        
        if self._process:
            # Using multiprocessing
            self._process.terminate()
            return
        
        # Using fork
        try:
            os.kill(self.pid, signal.SIGTERM)
        except OSError:
            pass
    
    @property
    def daemon(self):
        """Get daemon flag"""
        return self._daemon
    
    @daemon.setter
    def daemon(self, value):
        """Set daemon flag"""
        if self._started:
            raise RuntimeError("Cannot set daemon status of active process")
        self._daemon = value

# Use our custom Process class or the standard one based on platform
if is_macos or not process_utils:
    # On macOS or without our C extension, use the standard multiprocessing Process
    Process = multiprocessing.Process
else:
    # On other platforms with our C extension available, use our custom Process
    Process = ForkProcess 