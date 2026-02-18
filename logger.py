import sys
import os
import datetime
import glob
import config

class DualWriter:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.filename = filename
        if config.LOG_LEVEL > 0:
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(f"--- Log Started: {datetime.datetime.now()} (Level {config.LOG_LEVEL}) ---\n")

    def write(self, message, level=None):
        # Handle raw writes (from print/stderr redirection) vs structured logs
        msg_str = str(message)

        # If level is None, it's a raw system write (traceback, etc), always log it
        should_log = True
        if level is not None and level > config.LOG_LEVEL:
            should_log = False

        if should_log:
            # Write to terminal (only if it's not a raw newline)
            if msg_str != "\n":
                self.terminal.write(msg_str + ("\n" if level is not None else ""))

            # Write to file
            if config.LOG_LEVEL > 0:
                try:
                    with open(self.filename, "a", encoding="utf-8") as f:
                        if level is not None:
                            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [LVL {level}] {msg_str}\n")
                        else:
                            f.write(msg_str)
                except: pass

    def flush(self):
        self.terminal.flush()

# Global Instance
_writer = None

def cleanup_old_logs(log_dir):
    """Deletes oldest logs until folder size is under the limit."""
    try:
        files = glob.glob(os.path.join(log_dir, "*.log"))
        # Sort by modification time (Oldest first)
        files.sort(key=os.path.getmtime)

        total_size = sum(os.path.getsize(f) for f in files)

        for f in files:
            if total_size < config.MAX_LOG_FOLDER_BYTES:
                break

            try:
                size = os.path.getsize(f)
                os.remove(f)
                total_size -= size
                # We print to stdout directly because logger isn't ready yet
                print(f"[System] Log limit reached. Deleted old log: {os.path.basename(f)}")
            except: pass
    except Exception as e:
        print(f"[System] Log cleanup failed: {e}")

def setup():
    global _writer
    if not config.ENABLE_LOGGING:
        return

    # 1. Create Log Directory
    log_dir = os.path.join(config.DOWNLOAD_DIR, config.LOG_SUBDIR)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 2. Cleanup Old Logs BEFORE creating a new one
    cleanup_old_logs(log_dir)

    # 3. Generate Timestamped Filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"log_{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)

    # 4. Initialize Writer
    _writer = DualWriter(log_path)

    # Redirect standard outputs to capture crashes
    sys.stdout = _writer
    sys.stderr = _writer

    print(f"[System] Logging enabled. Output saved to: {config.LOG_SUBDIR}/{log_filename}")

def log(level, message):
    """The main logging function."""
    if _writer:
        _writer.write(message, level)
    elif config.LOG_LEVEL >= level:
        print(message)
