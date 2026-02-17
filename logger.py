import sys
import os
import datetime
import config

class DualWriter:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.filename = filename
        if config.LOG_LEVEL > 0:
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(f"--- Log Started: {datetime.datetime.now()} (Level {config.LOG_LEVEL}) ---\n")

    def write(self, message, level):
        # Only output if the message level is <= our configured level
        if level <= config.LOG_LEVEL:
            # Write to terminal
            self.terminal.write(message + "\n")
            # Write to file
            if config.LOG_LEVEL > 0:
                try:
                    with open(self.filename, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [LVL {level}] {message}\n")
                except: pass

    def flush(self):
        self.terminal.flush()

# Global Instance
_writer = None

def setup():
    global _writer
    log_path = os.path.join(config.DOWNLOAD_DIR, config.LOG_FILE)
    _writer = DualWriter(log_path)

def log(level, message):
    """The main logging function to be used in all files."""
    if _writer:
        _writer.write(str(message), level)
    elif config.LOG_LEVEL >= level:
        # Fallback if setup hasn't run
        print(message)
