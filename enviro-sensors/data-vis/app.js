/**
 * Enviro Sensor Dashboard
 *
 * Renders interactive Chart.js time-series charts for each device and metric
 * found in data.json (produced by build_data.py).
 */

const SENSOR_META = {
  pressure:          { label: 'Atmospheric Pressure', unit: 'hPa',   beginAtZero: false },
  temperature:       { label: 'Temperature',          unit: '\u00b0C',    beginAtZero: false },
  humidity:          { label: 'Humidity',              unit: '%',     min: 0, max: 100 },
  color_temperature: { label: 'Colour Temperature',   unit: 'K',     beginAtZero: false },
  gas_resistance:    { label: 'Gas Resistance',        unit: '\u03a9',     beginAtZero: false },
  aqi:               { label: 'Air Quality Index',     unit: '',      beginAtZero: true },
  luminance:         { label: 'Luminance',             unit: 'lux',   beginAtZero: true },
  pm1:               { label: 'PM1.0',                 unit: '\u00b5g/m\u00b3', beginAtZero: true },
  pm2_5:             { label: 'PM2.5',                 unit: '\u00b5g/m\u00b3', beginAtZero: true },
  pm10:              { label: 'PM10',                  unit: '\u00b5g/m\u00b3', beginAtZero: true },
  noise:             { label: 'Noise Level',           unit: '',      beginAtZero: true },
};

const COLORS = [
  '#2563eb', '#dc2626', '#16a34a', '#d97706',
  '#7c3aed', '#db2777', '#0891b2', '#65a30d',
];

const charts = {};

function buildUI() {
  const tabsEl = document.getElementById('tabs');
  const chartsEl = document.getElementById('charts');
  const devices = Object.keys(DATA);

  devices.forEach((device, i) => {
    // Tab button
    const btn = document.createElement('button');
    btn.textContent = device;
    btn.dataset.device = device;
    if (i === 0) btn.classList.add('active');
    btn.addEventListener('click', () => switchTab(device));
    tabsEl.appendChild(btn);

    // Panel
    const panel = document.createElement('div');
    panel.className = 'device-panel' + (i === 0 ? ' active' : '');
    panel.id = 'panel-' + device;

    const readings = DATA[device];
    const sensorKeys = Object.keys(readings[0].readings);

    sensorKeys.forEach((key) => {
      const meta = SENSOR_META[key] || { label: key, unit: '', beginAtZero: false };

      const card = document.createElement('div');
      card.className = 'chart-card';

      const heading = document.createElement('h2');
      heading.textContent = meta.label + (meta.unit ? ` (${meta.unit})` : '');
      card.appendChild(heading);

      const canvas = document.createElement('canvas');
      canvas.id = `chart-${device}-${key}`;
      card.appendChild(canvas);
      panel.appendChild(card);
    });

    chartsEl.appendChild(panel);
  });

  // Create charts for first device immediately
  createChartsForDevice(devices[0]);
}

function switchTab(device) {
  document.querySelectorAll('#tabs button').forEach(b =>
    b.classList.toggle('active', b.dataset.device === device)
  );
  document.querySelectorAll('.device-panel').forEach(p =>
    p.classList.toggle('active', p.id === 'panel-' + device)
  );
  // Lazily create charts
  if (!charts[device]) {
    createChartsForDevice(device);
  }
}

function createChartsForDevice(device) {
  const readings = DATA[device];
  const sensorKeys = Object.keys(readings[0].readings);
  charts[device] = {};

  sensorKeys.forEach((key, i) => {
    const meta = SENSOR_META[key] || { label: key, unit: '', beginAtZero: false };
    const canvas = document.getElementById(`chart-${device}-${key}`);

    const dataPoints = readings.map(r => ({
      x: new Date(r.timestamp),
      y: r.readings[key],
    }));

    const yScale = { beginAtZero: meta.beginAtZero };
    if (meta.min !== undefined) yScale.min = meta.min;
    if (meta.max !== undefined) yScale.max = meta.max;
    if (meta.unit) {
      yScale.ticks = {
        callback: v => v + ' ' + meta.unit,
      };
    }

    charts[device][key] = new Chart(canvas, {
      type: 'line',
      data: {
        datasets: [{
          label: meta.label,
          data: dataPoints,
          borderColor: COLORS[i % COLORS.length],
          backgroundColor: COLORS[i % COLORS.length] + '18',
          borderWidth: 1.5,
          pointRadius: 0,
          pointHitRadius: 8,
          fill: true,
          tension: 0.2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'nearest',
          intersect: false,
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: items => {
                const d = new Date(items[0].parsed.x);
                return d.toLocaleString();
              },
              label: item => {
                const v = item.parsed.y;
                return `${meta.label}: ${v}${meta.unit ? ' ' + meta.unit : ''}`;
              },
            },
          },
        },
        scales: {
          x: {
            type: 'time',
            time: {
              tooltipFormat: 'PPpp',
              displayFormats: {
                minute: 'd MMM, HH:mm',
                hour: 'd MMM, HH:mm',
                day: 'd MMM',
              },
            },
            ticks: {
              maxTicksAuto: 8,
              maxRotation: 45,
              minRotation: 0,
            },
          },
          y: yScale,
        },
      },
    });
  });
}

let DATA;

fetch('data.json')
  .then(r => {
    if (!r.ok) throw new Error(`Failed to load data.json (${r.status})`);
    return r.json();
  })
  .then(data => {
    DATA = data;
    buildUI();
  })
  .catch(err => {
    document.getElementById('charts').textContent = 'Error loading sensor data.';
    console.error(err);
  });
