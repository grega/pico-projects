#!/usr/bin/env python3
"""Push code/config to the Inky Frame's webserver, and round-trip its config.

The device is the source of truth for its own per-device config; this script
fetches it into _device/config.py (gitignored), and pushes that local working
copy back when you've edited it.

Examples:
    ./push.py code                      # push main.py and reboot
    ./push.py file <a>.py [<b>.py ...]  # push one or more .py files, reboot once at the end
    ./push.py config fetch              # download device's config.py to _device/config.py
    ./push.py config push               # upload _device/config.py and reboot
    ./push.py reboot                    # just reboot

Host can be set via --host, the INKY_HOST env var, or a .push_host file next to
this script.

secrets.py is intentionally not pushable - WiFi credentials are bootstrapped
once over USB and never traverse the LAN.
"""

import argparse
import os
import sys
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
DEVICE_DIR = os.path.join(HERE, "_device")
LOCAL_CONFIG = os.path.join(DEVICE_DIR, "config.py")
HOST_FILE = os.path.join(HERE, ".push_host")

MAIN_SRC = os.path.join(HERE, "main.py")


def resolve_host(cli_host):
    if cli_host:
        return cli_host
    env = os.environ.get("INKY_HOST")
    if env:
        return env
    if os.path.exists(HOST_FILE):
        with open(HOST_FILE) as f:
            value = f.read().strip()
        if value:
            return value
    sys.exit(
        "No host. Pass --host, set INKY_HOST, or write the IP/hostname to "
        f"{os.path.relpath(HOST_FILE, HERE)}"
    )


def _http(method, host, path, body=None, timeout=60):
    # Default timeout has to comfortably exceed the e-ink redraw (~30s) since
    # the webserver can't service requests while graphics.update() is running.
    url = f"http://{host}{path}"
    req = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("Content-Length", str(len(body)))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        reason = e.reason
        hint = ""
        # socket.timeout / TimeoutError surface here as URLError.reason
        if isinstance(reason, (TimeoutError,)) or "timed out" in str(reason):
            hint = " (device may be mid-render; e-ink redraws take ~30s and block the webserver - try again in a moment)"
        sys.exit(f"{method} {url} failed: {reason}{hint}")


def _upload_file(host, src_path, remote_name):
    if not os.path.exists(src_path):
        sys.exit(f"Source file not found: {src_path}")
    with open(src_path, "rb") as f:
        body = f.read()
    status, response = _http("POST", host, f"/upload?path={remote_name}", body)
    print(f"upload {os.path.basename(src_path)} -> {remote_name}: HTTP {status} {response.decode(errors='replace').strip()}")
    if status != 200:
        sys.exit(1)


def _reboot(host):
    # /reboot is fire-and-forget by nature: the device sends "Rebooting" and
    # immediately resets. There's an inherent race between the FIN reaching us
    # and the chip going offline, so a ConnectionResetError or TimeoutError
    # here is expected behaviour rather than a real failure. (Python 3.10+
    # raises TimeoutError on socket read timeout rather than letting the older
    # socket.timeout escape; both forms are benign here.)
    try:
        status, response = _http("POST", host, "/reboot", b"", timeout=5)
        print(f"reboot: HTTP {status} {response.decode(errors='replace').strip()}")
    except (ConnectionResetError, ConnectionAbortedError, TimeoutError):
        print("reboot: connection lost (expected - device is rebooting)")


def cmd_code(args):
    host = resolve_host(args.host)
    _upload_file(host, MAIN_SRC, "main.py")
    _reboot(host)


def cmd_file(args):
    host = resolve_host(args.host)
    # Resolve + validate every path up-front so we don't half-push a batch and
    # then bail out because of a typo on the last filename.
    resolved = []
    for path in args.paths:
        src_path = path if os.path.isabs(path) else os.path.join(HERE, path)
        if not os.path.exists(src_path):
            sys.exit(f"Source file not found: {src_path}")
        remote_name = os.path.basename(src_path)
        if remote_name == "secrets.py":
            sys.exit("Refusing to push secrets.py - bootstrap credentials over USB instead.")
        resolved.append((src_path, remote_name))

    for src_path, remote_name in resolved:
        _upload_file(host, src_path, remote_name)
    _reboot(host)


def cmd_config_fetch(args):
    host = resolve_host(args.host)
    status, body = _http("GET", host, "/config")
    if status != 200:
        sys.exit(f"GET /config returned HTTP {status}: {body.decode(errors='replace')}")
    os.makedirs(DEVICE_DIR, exist_ok=True)
    with open(LOCAL_CONFIG, "wb") as f:
        f.write(body)
    print(f"Wrote {len(body)} bytes to {os.path.relpath(LOCAL_CONFIG, HERE)}")


def cmd_config_push(args):
    host = resolve_host(args.host)
    if not os.path.exists(LOCAL_CONFIG):
        sys.exit(
            f"No local config at {os.path.relpath(LOCAL_CONFIG, HERE)} - "
            "run `./push.py config fetch` first."
        )
    _upload_file(host, LOCAL_CONFIG, "config.py")
    _reboot(host)


def cmd_reboot(args):
    _reboot(resolve_host(args.host))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", help="IP or hostname of the Inky Frame (overrides INKY_HOST and .push_host)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("code", help="push main.py and reboot").set_defaults(func=cmd_code)
    file_parser = sub.add_parser("file", help="push one or more local .py files (eg. webserver.py dashboard.py) under their same names and reboot once at the end")
    file_parser.add_argument("paths", nargs="+", help="one or more paths to local .py files (relative to this script, or absolute)")
    file_parser.set_defaults(func=cmd_file)
    sub.add_parser("reboot", help="reboot the device").set_defaults(func=cmd_reboot)

    config = sub.add_parser("config", help="manage device config").add_subparsers(dest="config_cmd", required=True)
    config.add_parser("fetch", help="download device config into _device/").set_defaults(func=cmd_config_fetch)
    config.add_parser("push",  help="upload _device/config.py and reboot").set_defaults(func=cmd_config_push)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
