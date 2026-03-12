# Enviro Sensor Dashboard

A lightweight web dashboard for visualising environmental data collected by the
Enviro sensor boards. It reads the individual JSON reading files produced by
the [Cloudflare Worker](../worker.js) (stored in R2) and renders interactive
time-series charts with [Chart.js](https://www.chartjs.org/).

## Data flow

```
Enviro boards  ──►  Cloudflare Worker  ──►  R2 bucket
                                                │
                            download JSON files │
                                                ▼
                    device reading directories ({nickname}-{uid}/)
                                                │
                              build_data.py     │
                                                ▼
                                           data.json
                                                │
                           index.html + app.js  │
                                                ▼
                                       Browser dashboard
```

## Prerequisites

Install Python with [asdf](https://asdf-vm.com/):

```bash
asdf plugin add python
asdf install
```

## Quick start

1. **Download readings** from your R2 bucket into this directory. Each device
   should have its own folder named `{nickname}-{uid}/` containing one JSON
   file per reading (this is the layout the Worker creates).

2. **Aggregate the data:**

   ```bash
   python3 build_data.py
   ```

   This produces `data.json`, combining all readings keyed by device nickname.
   Run `python3 build_data.py --help` for options.

3. **Serve the dashboard** (any static file server works):

   ```bash
   python3 -m http.server 8000
   ```

   Open <http://localhost:8000> in your browser.

## Supported sensors

The dashboard auto-detects metrics from each device's readings. Currently
recognised metrics with display labels and units:

| Key                | Label                 | Unit   |
|--------------------|-----------------------|--------|
| `temperature`      | Temperature           | °C     |
| `humidity`         | Humidity              | %      |
| `pressure`         | Atmospheric Pressure  | hPa    |
| `aqi`              | Air Quality Index     | —      |
| `gas_resistance`   | Gas Resistance        | Ω      |
| `luminance`        | Luminance             | lux    |
| `color_temperature`| Colour Temperature    | K      |
| `noise`            | Noise Level           | —      |
| `pm1`              | PM1.0                 | µg/m³  |
| `pm2_5`            | PM2.5                 | µg/m³  |
| `pm10`             | PM10                  | µg/m³  |

Unrecognised keys still render — they just use the raw key name as the label.
