# Minimal logging with aggressive rotation for MicroPython.
# Replaces phew.logging — same API surface (info, error, debug).

import os

LOG_FILE = "log.txt"
MAX_SIZE = 4096       # rotate when log exceeds 4 KB
KEEP_SIZE = 2048      # after rotation, keep ~last 2 KB
_DEBUG = False        # set True to enable debug-level messages

def _size():
  try:
    return os.stat(LOG_FILE)[6]
  except OSError:
    return 0

def _rotate():
  """Trim log file to KEEP_SIZE bytes (keeping the tail)."""
  size = _size()
  if size <= MAX_SIZE:
    return
  try:
    with open(LOG_FILE, "r") as f:
      f.seek(size - KEEP_SIZE)
      f.readline()  # skip partial line
      tail = f.read()
    with open(LOG_FILE, "w") as f:
      f.write("--- log rotated ---\n")
      f.write(tail)
  except Exception:
    # if rotation fails, just truncate
    try:
      with open(LOG_FILE, "w") as f:
        f.write("--- log reset ---\n")
    except Exception:
      pass

def _write(level, msg):
  from machine import RTC
  dt = RTC().datetime()
  ts = "{0:04d}-{1:02d}-{2:02d} {4:02d}:{5:02d}:{6:02d}".format(*dt)
  line = "[" + ts + "] " + level + " " + str(msg)
  print(line)
  try:
    with open(LOG_FILE, "a") as f:
      f.write(line + "\n")
    _rotate()
  except Exception:
    pass

def info(msg):
  _write("I", msg)

def error(msg):
  _write("E", msg)

def debug(msg):
  if _DEBUG:
    _write("D", msg)

def truncate():
  """Delete log file entirely."""
  try:
    os.remove(LOG_FILE)
  except OSError:
    pass
