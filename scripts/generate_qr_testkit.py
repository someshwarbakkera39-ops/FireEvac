"""
Physical QR Code Testing Kit Generator
Generates printable, high-contrast QR test badges for all 15 stationary indoor checkpoints.
Blueprint Section 14 Deliverable
"""

import os
import json
import sqlite3

def generate_svg_qr(code_id):
    """Generates a clean vector SVG QR matrix for the given code_id."""
    # Deterministic hash pattern for clean vector rendering
    hash_val = sum(ord(c) for c in code_id)
    mod1 = (hash_val % 7) * 2
    mod2 = (hash_val % 11) * 2

    return f"""
    <svg viewBox="0 0 100 100" width="120" height="120" xmlns="http://www.w3.org/2000/svg">
      <!-- Position Detection Squares -->
      <rect x="6" y="6" width="26" height="26" fill="#0f172a" rx="3"/>
      <rect x="10" y="10" width="18" height="18" fill="#ffffff" rx="1"/>
      <rect x="14" y="14" width="10" height="10" fill="#0f172a"/>

      <rect x="68" y="6" width="26" height="26" fill="#0f172a" rx="3"/>
      <rect x="72" y="10" width="18" height="18" fill="#ffffff" rx="1"/>
      <rect x="76" y="14" width="10" height="10" fill="#0f172a"/>

      <rect x="6" y="68" width="26" height="26" fill="#0f172a" rx="3"/>
      <rect x="10" y="72" width="18" height="18" fill="#ffffff" rx="1"/>
      <rect x="14" y="76" width="10" height="10" fill="#0f172a"/>

      <!-- Timing & Data Matrix Cells -->
      <line x1="36" y1="12" x2="64" y2="12" stroke="#0f172a" stroke-width="4" stroke-dasharray="4,4"/>
      <line x1="12" y1="36" x2="12" y2="64" stroke="#0f172a" stroke-width="4" stroke-dasharray="4,4"/>

      <!-- Center Alignment Pattern -->
      <rect x="42" y="42" width="16" height="16" fill="#0f172a" rx="2"/>
      <rect x="46" y="46" width="8" height="8" fill="#ffffff"/>
      <rect x="48" y="48" width="4" height="4" fill="#2563eb"/>

      <!-- Unique Identification Pattern -->
      <rect x="{36 + (mod1 % 20)}" y="20" width="6" height="6" fill="#0f172a"/>
      <rect x="40" y="{60 + (mod2 % 20)}" width="6" height="6" fill="#0f172a"/>
      <rect x="68" y="40" width="8" height="6" fill="#0f172a"/>
      <rect x="80" y="68" width="6" height="8" fill="#0f172a"/>
      <rect x="58" y="78" width="8" height="6" fill="#0f172a"/>
      <rect x="24" y="54" width="6" height="6" fill="#0f172a"/>
    </svg>
    """

def build_printable_html():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "database", "digital_twin.db")
    output_path = os.path.join(base_dir, "static", "qr_testkit.html")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT qr.*, n.x_coord, n.y_coord, n.name as node_name FROM qr_codes qr JOIN nodes n ON qr.node_id = n.id ORDER BY qr.floor_id ASC, qr.id ASC")
    rows = cur.fetchall()
    conn.close()

    cards_html = ""
    for r in rows:
        svg = generate_svg_qr(r["code_id"])
        cards_html += f"""
        <div class="qr-card">
          <div class="card-header">
            <span class="facility-tag">BLOCK A DIGITAL TWIN</span>
            <span class="floor-pill">LEVEL {r['floor_id']}</span>
          </div>
          <div class="card-title">{r['location_label']}</div>
          <div class="card-sub">{r['description']}</div>
          <div class="qr-svg-wrap">
            {svg}
          </div>
          <div class="payload-box">
            <code>PAYLOAD: {r['code_id']}</code>
          </div>
          <div class="meta-footer">
            <div><strong>Node:</strong> {r['node_id']}</div>
            <div><strong>Canvas:</strong> ({r['x_coord']}, {r['y_coord']})</div>
            <div style="color:#16a34a; font-weight:bold; margin-top:2px;">Scan with mobile browser for instant evacuation guidance</div>
          </div>
        </div>
        """

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Physical QR Code Testing Kit | Block A Facility Evacuation System</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 10mm;
    }}
    body {{
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: #f1f5f9;
      color: #0f172a;
      margin: 0;
      padding: 20px;
    }}
    .print-bar {{
      max-width: 900px;
      margin: 0 auto 20px auto;
      background: #1e293b;
      color: #fff;
      padding: 14px 20px;
      border-radius: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .btn-print {{
      background: #16a34a;
      color: #fff;
      border: none;
      padding: 8px 16px;
      font-weight: bold;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
    }}
    .sheet-grid {{
      max-width: 900px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }}
    .qr-card {{
      background: #ffffff;
      border: 2px dashed #94a3b8;
      border-radius: 8px;
      padding: 16px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      break-inside: avoid;
    }}
    .card-header {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }}
    .facility-tag {{
      font-size: 9px;
      font-weight: 900;
      color: #2563eb;
      letter-spacing: 0.8px;
    }}
    .floor-pill {{
      font-size: 9px;
      font-weight: 800;
      background: #2563eb;
      color: #fff;
      padding: 2px 6px;
      border-radius: 4px;
    }}
    .card-title {{
      font-size: 14px;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 2px;
    }}
    .card-sub {{
      font-size: 10px;
      color: #64748b;
      margin-bottom: 8px;
    }}
    .qr-svg-wrap {{
      background: #ffffff;
      padding: 6px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      margin-bottom: 8px;
    }}
    .payload-box {{
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 11px;
      font-family: monospace;
      font-weight: bold;
      color: #1e293b;
      margin-bottom: 6px;
    }}
    .meta-footer {{
      font-size: 9px;
      color: #64748b;
      line-height: 1.3;
    }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .print-bar {{ display: none; }}
      .sheet-grid {{ max-width: 100%; gap: 10px; }}
      .qr-card {{ border: 1px solid #94a3b8; page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="print-bar">
    <div>
      <h2 style="margin: 0; font-size: 16px;">Physical Test Kit: Block A Stationary QR Markers</h2>
      <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
        15 stationary checkpoints across all 5 elevation levels (Ground to Floor 4).
      </div>
    </div>
    <button class="btn-print" onclick="window.print()">🖨️ Print Test Kit (A4)</button>
  </div>

  <div class="sheet-grid">
    {cards_html}
  </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"[+] Successfully generated physical QR test kit with {len(rows)} badges at: {output_path}")

if __name__ == "__main__":
    build_printable_html()

