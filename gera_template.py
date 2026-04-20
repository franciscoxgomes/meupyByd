import datetime
from datetime import datetime, timezone
import json
import html as _html

# ==================== FUNÇÕES AUXILIARES ====================
def _non_empty(v):
    return v is not None and v != "" and (not (isinstance(v, str) and v.strip() == ""))

def _as_number(v):
    try:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        n = float(v)
        return None if n != n else n
    except:
        return None

def _fmt_percent(v):
    n = _as_number(v)
    if n is None: return "-"
    return f"{int(n)}%" if float(n).is_integer() else f"{n:.1f}%"

def _fmt_distance(v):
    n = _as_number(v)
    if n is None: return "-"
    return f"{int(n)} km" if float(n).is_integer() else f"{n:.1f} km"

def _map_online_state(v):
    n = _as_number(v)
    if n == 1: return "online"
    if n == 2: return "offline"
    if n == 0: return "unknown"
    return str(v) if _non_empty(v) else "-"

def _escape(text):
    return _html.escape("" if text is None else str(text))

def _format_timestamp_ms(val):
    if val is None: return None
    if isinstance(val, str):
        s = val.strip()
        if s.isdigit():
            try: return int(s)
            except: pass
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except: pass
        return None
    try:
        num = int(val)
    except:
        try: num = int(float(val))
        except: return None
    if num > 9999999999999: return None
    if num > 9999999999: return int(round(num))
    if num > 1000000000: return int(round(num * 1000))
    return None


def funcaoTemplate(data, generated_at):
    vehicle_info = data.get("vehicleInfo", {}) or {}
    vehicles = data.get("vehicles", []) or []
    target_vin = str(data.get("vin", ""))

    primary = next((v for v in vehicles if isinstance(v, dict) and str(v.get("vin", "")) == target_vin), None)
    if primary is None and vehicles:
        primary = vehicles[0]
    if primary is None:
        primary = {}

    # Dados principais
    car_name = primary.get("modelName") or primary.get("outModelType") or primary.get("autoAlias") or "BYD Vehicle"
    brand = primary.get("brandName", "")
    plate = primary.get("autoPlate", "")
    car_image = (primary.get("picMainUrl") or 
                 (primary.get("cfPic") or {}).get("picMainUrl") or 
                 vehicle_info.get("picMainUrl") or "")

    battery_raw = next((vehicle_info.get(k) for k in ("elecPercent", "powerBattery") if _non_empty(vehicle_info.get(k))), None)
    range_raw = next((vehicle_info.get(k) for k in ("enduranceMileage", "evEndurance") if _non_empty(vehicle_info.get(k))), None)
    charge_state = vehicle_info.get("chargingState") or vehicle_info.get("chargeState")
    connect_state = vehicle_info.get("connectState")
    online_label = _map_online_state(vehicle_info.get("onlineState"))

    charge_eta = ""
    if _non_empty(vehicle_info.get("remainingHours")) or _non_empty(vehicle_info.get("remainingMinutes")):
        charge_eta = f"{vehicle_info.get('remainingHours') or 0}h {vehicle_info.get('remainingMinutes') or 0}m"

    realtime_ms = _format_timestamp_ms(vehicle_info.get("time"))
    gps_wrap = data.get("gps", {}) or {}
    gps_info = gps_wrap.get("gpsInfo") or {}
    gps_data = (gps_info.get("data") if isinstance(gps_info, dict) else gps_info) or {}

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    freshness_diff = (now_ms - realtime_ms) if realtime_ms else None

    def tone_for_online(v):
        t = str(v or "").lower()
        if t == "online": return "ok"
        if t == "offline": return "bad"
        return "neutral"

    def tone_for_battery(v):
        n = _as_number(v)
        if n is None: return "neutral"
        if n >= 55: return "ok"
        if n >= 25: return "warn"
        return "bad"

    def tone_for_charging(v):
        if not _non_empty(v): return "neutral"
        s = str(v).lower()
        if "error" in s or "fault" in s: return "bad"
        if s == "1" or "charging" in s or "charge" in s: return "ok"
        return "warn"

    def tone_for_age(msdiff):
        if msdiff is None: return "neutral"
        if msdiff < 0: return "warn"
        if msdiff <= 5 * 60 * 1000: return "ok"
        if msdiff <= 30 * 60 * 1000: return "warn"
        return "bad"

    # Status Strip
    status_items = [
        {"label": "Connectivity", "value": online_label, "detail": f"Connect state: {connect_state}" if _non_empty(connect_state) else "", "tone": tone_for_online(online_label)},
        {"label": "Battery", "value": _fmt_percent(battery_raw), "detail": f"Range: {_fmt_distance(range_raw)}" if _non_empty(range_raw) else "", "tone": tone_for_battery(battery_raw)},
        {"label": "Charging", "value": _escape(charge_state or "-"), "detail": f"ETA: {charge_eta}" if charge_eta else "No ETA reported", "tone": tone_for_charging(charge_state)},
        {"label": "GPS", "value": _escape(gps_wrap.get("message") or "unavailable"), "detail": "", "tone": "ok" if gps_wrap.get("ok") else "warn"},
        {"label": "Data Age", "value": f"{int((freshness_diff/1000)//60)}m ago" if freshness_diff is not None else "unknown", "detail": "Source: vehicle realtime", "tone": tone_for_age(freshness_diff)}
    ]

    status_html = "".join(
        f'<article class="status-chip tone-{it["tone"]}">'
        f'<span class="status-label">{_escape(it["label"])}</span>'
        f'<strong class="status-value">{_escape(it["value"])}</strong>'
        f'<div class="status-detail">{_escape(it.get("detail") or " ")}</div></article>'
        for it in status_items
    )

    # Badges
    badges = [
        ("User ID", data.get("userId"), True),
        ("VIN", target_vin, True),
        ("Plate", plate, True),
        ("Model", primary.get("modelName") or primary.get("outModelType"), False),
        ("Alias", primary.get("autoAlias"), False),
        ("Energy type", primary.get("energyType"), False),
        ("Vehicle state", vehicle_info.get("vehicleState"), False),
    ]

    badges_html = ""
    for item in badges:
        k, v, sensitive = item if len(item) == 3 else (*item, False)
        if not _non_empty(v): continue
        sens = ' class="sensitive-value"' if sensitive else ''
        badges_html += f'<span class="badge">{_escape(k)}: <span{sens}>{_escape(v)}</span></span>'

    # Raw JSONs
    raw_full = _html.escape(json.dumps(data, ensure_ascii=False, indent=2))
    raw_vehicle = _html.escape(json.dumps(vehicle_info, ensure_ascii=False, indent=2))
    raw_gps = _html.escape(json.dumps(gps_info, ensure_ascii=False, indent=2))

    # ====================== HTML FINAL ======================
    html_out = f'''<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BYD Live Status</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #ebf1f3;
      --bg-accent: #d3e2e8;
      --surface: rgba(255, 255, 255, 0.9);
      --surface-strong: rgba(255, 255, 255, 0.97);
      --ink: #0f2530;
      --muted: #5b727e;
      --line: #c9d8df;
      --accent: #007da0;
      --accent-soft: #e6f4f8;
      --ok: #1f8c63;
      --warn: #b57a12;
      --bad: #b14137;
      --neutral: #4a6778;
      --shadow: 0 16px 36px rgba(18, 42, 55, 0.14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Space Grotesk", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 12% 0, var(--bg-accent) 0, transparent 35%),
                  radial-gradient(circle at 92% 0, #efe3cc 0, transparent 30%),
                  linear-gradient(145deg, #f7fafb 0%, var(--bg) 55%, #e4edf0 100%);
      padding: 14px 14px 20px;
    }}
    .page {{ max-width: 1460px; margin: 0 auto; display: grid; gap: 14px; }}
    .card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); }}
    .card-pad {{ padding: 14px; }}
    .topbar {{ display: flex; align-items: center; justify-content: space-between; background: var(--surface-strong); }}
    .kicker {{ margin:0 0 6px; color:var(--accent); text-transform:uppercase; letter-spacing:0.11em; font-size:0.72rem; font-weight:700; }}
    .status-strip {{ display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:10px; }}
    .status-chip {{ border-radius:15px; border:1px solid var(--line); padding:10px 11px; background:var(--surface-strong); box-shadow:0 8px 18px rgba(16,38,53,0.1); }}
    .tone-ok {{ border-color:rgba(31,140,99,0.35); background:linear-gradient(150deg,rgba(217,244,233,0.82),#fff); }}
    .tone-warn {{ border-color:rgba(181,122,18,0.32); background:linear-gradient(150deg,rgba(251,239,218,0.84),#fff); }}
    .tone-bad {{ border-color:rgba(177,65,55,0.36); background:linear-gradient(150deg,rgba(253,227,222,0.82),#fff); }}
    .tone-neutral {{ border-color:rgba(74,103,120,0.3); background:linear-gradient(150deg,rgba(231,240,245,0.86),#fff); }}
    .hero {{ display:grid; grid-template-columns:0.95fr 1.05fr; min-height:290px; overflow:hidden; }}
    .hero-visual {{ background:linear-gradient(145deg,#d8e9f0,#edf4f7); border-right:1px solid var(--line); }}
    .hero-visual img {{ width:100%; height:100%; object-fit:contain; padding:18px; }}
    .badge-row {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .badge {{ background:linear-gradient(180deg,var(--accent-soft),#f6fbfd); border:1px solid #bfd8e4; border-radius:999px; padding:5px 10px; font-size:0.77rem; }}
    .metric-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; }}
    .metric {{ border:1px solid var(--line); border-radius:12px; padding:10px; background:#f8fbfd; }}
    .kv-row {{ display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed #d8e4eb; }}
    details {{ border:1px solid var(--line); border-radius:12px; margin-bottom:9px; background:#f7fafc; }}
    summary {{ cursor:pointer; padding:10px 12px; font-weight:600; }}
    pre {{ margin:0; padding:12px; font-size:0.73rem; font-family:"JetBrains Mono",monospace; overflow:auto; background:#fdfefe; }}
    @media (max-width:1220px) {{ .status-strip {{ grid-template-columns:repeat(3,minmax(0,1fr)); }} .hero {{ grid-template-columns:1fr; }} }}
    @media (max-width:860px) {{ .status-strip {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class="page">

    <header class="card card-pad topbar">
      <div>
        <p class="kicker">BYD Telemetry Snapshot</p>
        <h1>Vehicle Live Status</h1>
        <p class="subtitle">Gerado no servidor a partir da API</p>
      </div>
      <div style="text-align:right;color:var(--muted);">
        Gerado em: {_escape(generated_at)}
      </div>
    </header>

    <section class="status-strip">
      {status_html}
    </section>

    <main class="hero card">
      <div class="hero-visual">
        {f'<img src="{_escape(car_image)}" alt="{_escape(car_name)}">' if car_image else '<div style="height:100%;display:grid;place-items:center;color:#4f6d7d;padding:20px;">Sem imagem do veículo disponível</div>'}
      </div>
      <div class="card-pad">
        <h2 style="margin:0 0 8px;">{_escape(car_name)}</h2>
        <p style="margin:0;color:var(--muted);">{_escape(brand)}{" · " + _escape(plate) if plate else ""}</p>
        <div class="badge-row" style="margin-top:14px;">
          {badges_html or '<span class="badge">Sem detalhes de identidade</span>'}
        </div>
      </div>
    </main>

    <section class="card card-pad raw">
      <details open>
        <summary>Full output JSON</summary>
        <pre>{raw_full}</pre>
      </details>
      <details>
        <summary>vehicleInfo JSON</summary>
        <pre>{raw_vehicle}</pre>
      </details>
      <details>
        <summary>gpsInfo JSON</summary>
        <pre>{raw_gps}</pre>
      </details>
    </section>

  </div>
</body>
</html>'''

    return html_out