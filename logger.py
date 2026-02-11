import sys
import os
import datetime
import config

class DualWriter:
    """
    A helper class that writes to both the terminal (stdout) 
    and a log file simultaneously.
    """
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.filename = filename
        # Create/Clear the log file on startup
        with open(self.filename, "w", encoding="utf-8") as f:
            f.write(f"--- Log Started: {datetime.datetime.now()} ---\n")

    def write(self, message):
        # Write to terminal
        self.terminal.write(message)
        # Write to file
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(message)
        except Exception:
            pass # Don't crash if logging fails

    def flush(self):
        # Needed for python compatibility
        self.terminal.flush()

def setup():
    """
    Redirects print() and errors to the log file.
    """
    if config.ENABLE_LOGGING:
        log_path = os.path.join(config.DOWNLOAD_DIR, config.LOG_FILE)
        
        # Redirect Standard Output (print)
        sys.stdout = DualWriter(log_path)
        
        # Redirect Errors (Tracebacks)
        sys.stderr = DualWriter(log_path)
        
        print(f"[System] Logging enabled. Output saved to: {log_path}")