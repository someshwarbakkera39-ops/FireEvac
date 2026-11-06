"""
Physical QR Code Testing Kit Generator
Generates printable, high-contrast, camera-scannable QR test badges for all stationary indoor checkpoints.
Blueprint Section 14 Deliverable
"""

import os
import json
import sqlite3
import qrcode
import qrcode.image.svg
import io

def generate_svg_qr(code_id, host="http://localhost:5000"):
    """Generates a genuine standards-compliant vector SVG QR code encoding the public navigation URL."""
    scan_url = f"{host.rstrip('/')}/public?qr={code_id}"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
        image_factory=qrcode.image.svg.SvgPathImage
    )
    qr.add_data(scan_url)
    qr.make(fit=True)
    img = qr.make_image()
    svg_str = img.to_string(encoding="unicode")
    # Add responsive sizing attributes
    svg_str = svg_str.replace('<svg ', '<svg class="scannable-qr" style="width:140px; height:140px; display:block; margin:0 auto;" ')
    return svg_str, scan_url

def generate_png_qr(code_id, output_path, host="http://localhost:5000"):
    """Generates and saves a high-contrast PNG QR image for physical badge printing."""
    scan_url = f"{host.rstrip('/')}/public?qr={code_id}"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3
    )
    qr.add_data(scan_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, format="PNG")
    return output_path

def build_printable_html(host="http://localhost:5000"):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "database", "digital_twin.db")
    output_html_path = os.path.join(base_dir, "static", "qr_testkit.html")
    png_dir = os.path.join(base_dir, "static", "qr_codes")
    os.makedirs(png_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT qr.*, n.x_coord, n.y_coord, n.name as node_name FROM qr_codes qr JOIN nodes n ON qr.node_id = n.id ORDER BY qr.floor_id ASC, qr.id ASC")
    rows = cur.fetchall()
    conn.close()

    cards_html = ""
    for r in rows:
        code_id = r["code_id"]
        svg, scan_url = generate_svg_qr(code_id, host=host)
        png_path = os.path.join(png_dir, f"{code_id}.png")
        generate_png_qr(code_id, png_path, host=host)

        cards_html += f"""
        <div class="qr-card" id="card_{code_id}">
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
            <code>SCAN: {code_id}</code>
          </div>

          <div class="meta-footer">
            <div style="font-family: monospace; font-size: 10px; color: #2563eb; margin-bottom: 4px; word-break: break-all;">
              <a href="{scan_url}" target="_blank" style="color: #2563eb; text-decoration: none;">{scan_url}</a>
            </div>
            <div><strong>Waypoint Node:</strong> {r['node_id']}</div>
            <div><strong>Map Coordinate:</strong> ({r['x_coord']}, {r['y_coord']})</div>
            <div style="color: #16a34a; font-weight: 800; margin-top: 6px;">
              ⚡ Scan with phone camera for instant safe evacuation guidance
            </div>
          </div>

          <div style="margin-top: 8px; display: flex; gap: 6px;">
            <a href="/public?qr={code_id}" target="_blank" class="test-btn">Test Route</a>
            <a href="/api/qr/image/{code_id}" download="{code_id}.png" class="test-btn download-btn">Download PNG</a>
          </div>
        </div>
        """

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Physical QR Code Testing Kit | Block A Facility Evacuation System</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 8mm;
    }}
    body {{
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: #0f172a;
      color: #0f172a;
      margin: 0;
      padding: 20px;
    }}
    .print-bar {{
      max-width: 960px;
      margin: 0 auto 20px auto;
      background: #1e293b;
      color: #fff;
      padding: 16px 24px;
      border-radius: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }}
    .btn-print {{
      background: #16a34a;
      color: #fff;
      border: none;
      padding: 10px 18px;
      font-weight: 800;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      transition: background 0.15s;
    }}
    .btn-print:hover {{
      background: #15803d;
    }}
    .sheet-grid {{
      max-width: 960px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }}
    .qr-card {{
      background: #ffffff;
      border: 2px solid #cbd5e1;
      border-radius: 10px;
      padding: 16px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      break-inside: avoid;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
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
      font-size: 10px;
      font-weight: 800;
      background: #2563eb;
      color: #fff;
      padding: 3px 8px;
      border-radius: 4px;
    }}
    .card-title {{
      font-size: 15px;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 2px;
    }}
    .card-sub {{
      font-size: 11px;
      color: #64748b;
      margin-bottom: 8px;
    }}
    .qr-svg-wrap {{
      background: #ffffff;
      padding: 8px;
      border: 2px solid #e2e8f0;
      border-radius: 8px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .payload-box {{
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 11px;
      font-family: monospace;
      font-weight: bold;
      color: #1e293b;
      margin-bottom: 6px;
    }}
    .meta-footer {{
      font-size: 10px;
      color: #64748b;
      line-height: 1.4;
      width: 100%;
    }}
    .test-btn {{
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #0f172a;
      font-size: 11px;
      font-weight: 700;
      padding: 5px 10px;
      border-radius: 4px;
      text-decoration: none;
      cursor: pointer;
    }}
    .test-btn:hover {{
      background: #e2e8f0;
    }}
    .download-btn {{
      background: #eff6ff;
      border-color: #bfdbfe;
      color: #1d4ed8;
    }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .print-bar {{ display: none; }}
      .test-btn {{ display: none; }}
      .sheet-grid {{ max-width: 100%; gap: 10px; }}
      .qr-card {{ border: 1.5px solid #000; page-break-inside: avoid; box-shadow: none; }}
    }}
  </style>
</head>
<body>
  <div class="print-bar">
    <div>
      <h2 style="margin: 0; font-size: 17px; font-weight: 800;">📷 Physical QR Code Testing Kit — Block A Digital Twin</h2>
      <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">
        15 camera-scannable QR checkpoints encoding direct mobile navigation links (Floors 0 to 4).
      </div>
    </div>
    <div style="display: flex; gap: 8px;">
      <a href="/admin" style="background: #334155; color: #fff; padding: 10px 14px; font-size: 13px; font-weight: 700; border-radius: 6px; text-decoration: none;">← Admin Portal</a>
      <button class="btn-print" onclick="window.print()">🖨️ Print Test Kit (A4)</button>
    </div>
  </div>

  <div class="sheet-grid">
    {cards_html}
  </div>
</body>
</html>
"""

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"[+] Successfully generated physical QR test kit with {len(rows)} real badges at: {output_html_path}")

if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    build_printable_html(host)
