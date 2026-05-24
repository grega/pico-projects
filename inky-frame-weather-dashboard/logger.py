"""Persistent log capture for the Inky Frame.

Every print() goes through a monkey-patch that mirrors to:
  1. An always-on ~4KB RAM ring buffer (fast, served by /logs when no SD)
  2. A rotating pair of files on SD (`/sd/logs/current.log` + `previous.log`,
     ~64KB each), once `attach_sd()` has been called.

Logs survive reboots, so we can see what happened on the previous run - which
is exactly what we need when the device fails mid-boot (WiFi, fetch, parse).

Usage from main.py:
    import logger
    logger.install()                  # at module load - patches builtins.print
    ...
    _mount_sd()                       # mount /sd first
    logger.attach_sd("/sd/logs")      # then start writing to disk
    ...
    ntptime.settime()
    logger.mark_ntp_synced()          # switch from [+12.345s] to wall-clock timestamps
"""

import builtins
import os
import sys
import time

_RAM_BUFFER_BYTES = 4096
_MAX_LOG_FILE_BYTES = 64 * 1024  # rotate at 64KB; two files = 128KB max on SD

_ram = bytearray()
_fh = None  # open append-mode handle to current.log (None when SD not attached)
_current_path = None
_previous_path = None
_current_size = 0
_ntp_synced = False
_boot_ticks = time.ticks_ms()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def install():
    """Replace builtins.print so every print also feeds the RAM ring and SD file."""
    original = builtins.print

    def wrapped(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        try:
            line = _timestamp() + " " + sep.join(str(a) for a in args) + end
            _write(line.encode())
        except Exception:
            pass # never let log capture break a print
        return original(*args, **kwargs)

    builtins.print = wrapped


def attach_sd(log_dir):
    """Start mirroring future prints to a rotating file under `log_dir`.

    Called after SD is mounted. Creates the directory if missing, flushes any
    RAM-buffered boot lines to disk so we don't lose them, and writes a
    '--- boot ---' marker so each session is visually separable in the file.
    """
    global _fh, _current_path, _previous_path, _current_size
    try:
        try:
            os.mkdir(log_dir)
        except OSError:
            pass # already exists - fine
        _current_path = log_dir + "/current.log"
        _previous_path = log_dir + "/previous.log"
        try:
            _current_size = os.stat(_current_path)[6]
        except OSError:
            _current_size = 0
        _fh = open(_current_path, "ab")
        # Flush early-boot RAM contents to disk so the boot sequence isn't lost.
        if _ram:
            _fh.write(b"--- pre-SD buffer flush ---\n")
            _fh.write(bytes(_ram))
        _fh.write(b"--- boot ---\n")
        _fh.flush()
    except Exception as e:
        _fh = None
        # Print bypasses _write's SD branch since _fh is None now.
        print(f"logger: SD attach failed: {e}")


def mark_ntp_synced():
    """Tell the logger to switch from boot-relative to wall-clock timestamps."""
    global _ntp_synced
    _ntp_synced = True


def get_logs():
    """Return concatenated previous.log + current.log bytes, or the RAM ring
    if SD was never attached. Used by the /logs HTTP handler."""
    if _fh is None:
        return bytes(_ram)
    try:
        _fh.flush()
    except OSError:
        pass
    out = bytearray()
    for path in (_previous_path, _current_path):
        try:
            with open(path, "rb") as f:
                out.extend(f.read())
        except OSError:
            pass
    return bytes(out)


def log_exception(e, label=None):
    """Write a full traceback for `e` through the log pipeline.
    MicroPython's sys.print_exception accepts a file-like object - we pass a
    tiny collector and then re-emit the captured text via print so it lands in
    both RAM and SD with the usual timestamp prefix on each line.
    """
    collector = _Collector()
    try:
        sys.print_exception(e, collector)
    except Exception:
        # Fallback if the build doesn't accept a file argument.
        inline_prefix = (label + ": ") if label else ""
        print(inline_prefix + type(e).__name__ + ": " + str(e))
        return
    text = "".join(collector.parts)
    block_prefix = (label + ":\n") if label else ""
    for line in (block_prefix + text).split("\n"):
        if line:
            print(line)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

class _Collector:
    """File-like object that just accumulates writes - used by log_exception."""
    def __init__(self):
        self.parts = []
    def write(self, s):
        self.parts.append(s)


def _timestamp():
    if _ntp_synced:
        try:
            lt = time.localtime()
            return "[{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]".format(
                lt[0], lt[1], lt[2], lt[3], lt[4], lt[5]
            )
        except Exception:
            pass
    secs = time.ticks_diff(time.ticks_ms(), _boot_ticks) / 1000
    return "[+{:9.3f}s]".format(secs)


def _write(data):
    # RAM ring always - cheap, bounded, useful even if SD goes away
    _ram.extend(data)
    overflow = len(_ram) - _RAM_BUFFER_BYTES
    if overflow > 0:
        del _ram[:overflow]

    if _fh is not None:
        _append_to_sd(data)


def _append_to_sd(data):
    global _fh, _current_size
    try:
        _fh.write(data)
        _fh.flush() # keep the on-disk copy current in case we crash
        _current_size += len(data)
        if _current_size >= _MAX_LOG_FILE_BYTES:
            _rotate()
    except OSError:
        # SD removed or filesystem error - disable SD logging silently.
        try:
            _fh.close()
        except Exception:
            pass
        _fh = None


def _rotate():
    global _fh, _current_size
    try:
        _fh.close()
    except Exception:
        pass
    _fh = None
    try:
        try:
            os.remove(_previous_path)
        except OSError:
            pass
        os.rename(_current_path, _previous_path)
    except OSError:
        pass
    try:
        _fh = open(_current_path, "ab")
        _current_size = 0
    except OSError:
        _fh = None
