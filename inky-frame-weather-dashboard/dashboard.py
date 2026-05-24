"""HTML rendering for the device status dashboard, served at /
"""

_PICO_CSS = "https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"
_REFRESH_SECONDS = 5

# Inline ~sun-behind-cloud SVG used as the page favicon (avoids a separate file/endpoint).
_FAVICON = (
    'data:image/svg+xml,'
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
    "<text y='.9em' font-size='90'>%E2%9B%85</text></svg>"
)

_STYLES = """
:root {
  --wx-blue:   #4a6fa5;
  --wx-orange: #c87333;
  --wx-green:  #5fa370;
  --wx-red:    #c66767;
  --wx-muted:  var(--pico-muted-color);
}
.fetch-ok   { color: var(--wx-green); }
.fetch-fail { color: var(--wx-red); }
.muted      { color: var(--wx-muted); }
.dashboard-footer { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; font-size: 0.85rem; }
.dashboard-footer a { white-space: nowrap; }
.dashboard-footer button { padding: 0.2rem 0.7rem; font-size: 0.8rem; margin: 0; width: auto; }
.refresh-badge {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  background: var(--pico-card-sectioning-background-color);
  color: var(--wx-muted);
  font-size: 0.7rem;
  font-weight: 400;
  vertical-align: middle;
  letter-spacing: 0.02em;
}
.location {
  color: var(--wx-blue);
  font-weight: 600;
}
.weather-url {
  font-family: var(--pico-font-family-monospace);
  font-size: 0.8rem;
  word-break: break-all;
}
h1 { margin-bottom: 0.25rem; }
"""

# Reboot via fetch() so the button is just a button (not a full-width form).
# Reloads the page after the device responds to confirm the reboot was accepted.
_REBOOT_JS = (
    "if(confirm('Reboot the device?')){"
    "fetch('/reboot',{method:'POST'})"
    ".then(()=>{document.body.style.opacity='.4';setTimeout(()=>location.reload(),3000)})"
    ".catch(e=>alert('Reboot failed: '+e))"
    "}"
)


def _rssi_label(rssi):
    if rssi is None:
        return "n/a"
    if rssi >= -50: return f"{rssi} dBm (excellent)"
    if rssi >= -65: return f"{rssi} dBm (good)"
    if rssi >= -75: return f"{rssi} dBm (fair)"
    return f"{rssi} dBm (poor)"


def _fmt_duration(seconds):
    if seconds is None:
        return "n/a"
    if seconds < 0:
        seconds = 0
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"


def _fmt_age(age_s):
    if age_s is None:
        return "never"
    return f"{_fmt_duration(age_s)} ago"


def _fmt_bytes(n):
    if n is None:
        return "n/a"
    return f"{n // 1024} KB" if n >= 1024 else f"{n} bytes"


def _esc(s):
    if s is None:
        return ""
    return (str(s)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _render_device(info):
    return (
        '<article>'
        '<header>Device</header>'
        '<table>'
        f'<tr><th>IP</th><td>{_esc(info.get("ip"))}</td></tr>'
        f'<tr><th>Local time</th><td>{_esc(info.get("local_time")) or "n/a"}</td></tr>'
        f'<tr><th>Uptime</th><td>{_fmt_duration(info.get("uptime_s"))}</td></tr>'
        f'<tr><th>WiFi RSSI</th><td>{_rssi_label(info.get("rssi_dbm"))}</td></tr>'
        f'<tr><th>Free heap</th><td>{_fmt_bytes(info.get("free_heap_bytes"))} (alloc: {_fmt_bytes(info.get("alloc_heap_bytes"))})</td></tr>'
        '</table>'
        '</article>'
    )


def _render_weather(info):
    fetch_status = '<span class="muted">never</span>'
    if info.get("last_fetch_ok") is True:
        fetch_status = '<span class="fetch-ok">OK</span>'
    elif info.get("last_fetch_ok") is False:
        err = info.get("last_fetch_error") or "unknown error"
        fetch_status = f'<span class="fetch-fail">FAIL: {_esc(err)}</span>'

    next_in = info.get("next_refresh_in_s")
    if next_in is None:
        next_text = "n/a"
    elif next_in <= 0:
        next_text = "any moment"
    else:
        next_text = f"in {_fmt_duration(next_in)}"

    url = info.get("weather_url")
    url_html = '<span class="muted">n/a</span>'
    if url:
        url_html = f'<a href="{_esc(url)}" target="_blank" rel="noopener" class="weather-url">{_esc(url)}</a>'

    return (
        '<article>'
        '<header>Weather fetch</header>'
        '<table>'
        f'<tr><th>Location</th><td><span class="location">{_esc(info.get("location_name"))}</span></td></tr>'
        f'<tr><th>Last fetch</th><td>{_fmt_age(info.get("last_fetch_age_s"))} &middot; {fetch_status}</td></tr>'
        f'<tr><th>Next refresh</th><td>{next_text}</td></tr>'
        f'<tr><th>Source URL</th><td>{url_html}</td></tr>'
        '</table>'
        '</article>'
    )


def _render_footer():
    return (
        '<footer class="dashboard-footer">'
        '<a href="/status">/status (JSON)</a>'
        '<a href="/logs">/logs</a>'
        '<a href="/ascii">/ascii</a>'
        '<a href="/config">/config</a>'
        f'<button type="button" class="secondary outline" onclick="{_REBOOT_JS}">Reboot</button>'
        '</footer>'
    )


def render_status_html(info):
    """Render the status info dict (same shape as /status JSON) as an HTML page."""
    return (
        '<!DOCTYPE html>'
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="refresh" content="{_REFRESH_SECONDS}">'
        '<title>Inky Frame Weather</title>'
        f'<link rel="icon" href="{_FAVICON}">'
        f'<link rel="stylesheet" href="{_PICO_CSS}">'
        f'<style>{_STYLES}</style>'
        '</head><body><main class="container">'
        '<header>'
        '<h1>Inky Frame Weather'
        f'<span class="refresh-badge" title="page auto-refreshes">&#x21bb; {_REFRESH_SECONDS}s</span>'
        '</h1>'
        '</header>'
        + _render_weather(info)
        + _render_device(info)
        + _render_footer()
        + '</main></body></html>'
    )
