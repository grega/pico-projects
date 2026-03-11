# Battery Life Estimates

Estimates for 2× AAA alkaline batteries (~1200 mAh at 3V) using the battery power-off sleep path (RTC alarm wake).

## Indoor

Assuming `reading_frequency = 15` minutes, `upload_frequency = 12` readings (~3 hour upload cycle).

| Component | Per reading | Notes |
|---|---|---|
| Pico W active | ~2s × 50mA = 0.03 mAh | Boot, I2C, read BME688 + BH1745 |
| WiFi upload | ~20s × 120mA = 0.67 mAh | ~8 uploads/day |
| Sleep (power off) | ~0.01 mA | RTC only |

**~8–9 mAh/day → ~4–5 months**

## Urban

Assuming `reading_frequency = 15` minutes, `upload_frequency = 12` readings (~3 hour upload cycle).

| Component | Per reading | Notes |
|---|---|---|
| Pico W active | ~10s × 50mA = 0.14 mAh | Boot, I2C, read BME280 |
| PMS5003 fan + sensor | ~5.5s × 100mA = 0.15 mAh | 5s warm-up + read; biggest draw |
| Microphone | ~3s × 5mA = 0.004 mAh | ADC sampling, negligible |
| WiFi upload | ~20s × 120mA = 0.67 mAh | ~8 uploads/day |
| Sleep (power off) | ~0.01 mA | RTC only |

**~35–40 mAh/day → ~1 month**

## Tips

- The **PMS5003 fan motor** (~100mA for 5+ seconds) dominates Urban's power budget.

