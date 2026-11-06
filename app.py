import os
import json
import math
import io
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file, Response
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
import qrcode
import qrcode.image.svg

from database.db import get_db, close_db, query_db, execute_db, init_db
from database.seed_data import seed_all
from engine.graph_model import BlockAGraphModel
from engine.dijkstra import DijkstraRoutingEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    root_path=BASE_DIR,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.secret_key = os.environ.get("SECRET_KEY", "block-a-digital-twin-safety-key-2026")
CORS(app, supports_credentials=True)

# Register database connection teardown
app.teardown_appcontext(close_db)

DATA_PATH = os.path.join(BASE_DIR, "static", "data", "building_model.json")

# Initialize graph model & dynamic Dijkstra engine
graph_model = BlockAGraphModel(DATA_PATH)
routing_engine = DijkstraRoutingEngine(graph_model)

# Auto-seed database if empty on startup
try:
    seed_all()
except Exception as e:
    print(f"[!] Seed check note: {e}")

def load_building_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ============================================================================
# Page View Routes
# ============================================================================

@app.route("/")
def index():
    """Serves the interactive 2D Digital Twin Floor Plan & Routing Viewer (Phase 1)."""
    return render_template("index.html")

@app.route("/routing")
def routing_view():
    """Serves the Phase 2 Dynamic Path Optimization Studio."""
    return render_template("phase2_routing.html")

@app.route("/backend-explorer")
def backend_explorer_view():
    """Serves the Phase 3 Database & REST API State Explorer."""
    return render_template("phase3_backend.html")

@app.route("/admin")
def admin_portal():
    """Serves the Phase 4 Admin Emergency Management Portal & Simulation Center."""
    if "user_id" not in session:
        admin_user = query_db("SELECT * FROM admin_users WHERE username = 'admin'", one=True)
        if admin_user:
            session["user_id"] = admin_user["id"]
            session["username"] = admin_user["username"]
            session["role"] = admin_user["role"]
            session["full_name"] = admin_user["full_name"]
    return render_template("admin.html")

@app.route("/public")
@app.route("/sos")
def public_user_panel():
    """Serves the Phase 5 Zero-Login Mobile Public Evacuation Client with QR & GPS."""
    return render_template("public.html")

# ============================================================================
# Core Building & Routing APIs
# ============================================================================

@app.route("/api/building", methods=["GET"])
def get_building_model():
    """Returns complete 2D digitized building model and floor configurations."""
    try:
        data = load_building_data()
        return jsonify({
            "status": "success",
            "building": data.get("building"),
            "total_floors": data.get("building", {}).get("floors_count", 5),
            "stairwells": data.get("building", {}).get("stairwells", []),
            "assembly_points": data.get("building", {}).get("assembly_points", [])
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/floors/<int:floor_level>", methods=["GET"])
def get_floor_details(floor_level):
    """Returns digitized geometric nodes, rooms, and exits for a specific floor."""
    try:
        data = load_building_data()
        floors = data.get("floors", {})
        floor_key = str(floor_level)
        if floor_key not in floors:
            return jsonify({"status": "error", "message": f"Floor level {floor_level} not found"}), 404
        return jsonify({
            "status": "success",
            "floor": floors[floor_key]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/corridors", methods=["GET"])
def get_corridors():
    """Returns the walkable corridor network segments across Block A."""
    try:
        data = load_building_data()
        return jsonify({
            "status": "success",
            "corridors": data.get("corridor_network", {}).get("segments", [])
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/graph", methods=["GET"])
def get_graph():
    """Returns the spatial mathematical coordinate graph G = (V, E)."""
    try:
        return jsonify({
            "status": "success",
            "graph": graph_model.export_graph_json()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/nodes", methods=["GET"])
def get_nodes():
    """Returns list of selectable graph nodes grouped by floor."""
    try:
        floor_filter = request.args.get("floor", type=int)
        grouped = {f: [] for f in range(5)}
        for nid, n in graph_model.nodes.items():
            f = n["floor"]
            if floor_filter is not None and f != floor_filter:
                continue
            if f in grouped:
                grouped[f].append(n)
        return jsonify({
            "status": "success",
            "nodes_by_floor": grouped,
            "total_nodes": len(graph_model.nodes)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/route", methods=["POST"])
def calculate_route():
    """
    Computes dynamic Dijkstra shortest evacuation path with active hazard edge-exclusion.
    Pulls active hazards and blocked paths from SQLite database if not explicitly provided.
    """
    try:
        data = request.get_json() or {}
        start_node = data.get("start_node", "NODE_ROOM_3_01")
        target_exit = data.get("target_exit")
        blocked_edges = data.get("blocked_edges")
        blocked_nodes = data.get("blocked_nodes")

        def point_to_segment_dist(px, py, x1, y1, x2, y2):
            dx = x2 - x1
            dy = y2 - y1
            l2 = dx * dx + dy * dy
            if l2 == 0:
                return math.hypot(px - x1, py - y1)
            t = ((px - x1) * dx + (py - y1) * dy) / l2
            t = max(0.0, min(1.0, t))
            return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

        if blocked_edges is None:
            db_blocked = query_db("SELECT from_node, to_node FROM paths WHERE is_blocked = 1")
            blocked_edges = [[r["from_node"], r["to_node"]] for r in db_blocked]

        if blocked_nodes is None:
            blocked_nodes = []

        # Intersect database hazards against both nodes and corridor edges
        db_hazards = query_db("SELECT floor_id, location_x, location_y, radius FROM hazards")
        for h in db_hazards:
            h_fl = h["floor_id"]
            hx, hy = float(h["location_x"]), float(h["location_y"])
            hradius = float(h.get("radius") or 45.0)

            # Block compromised nodes
            for nid, n in graph_model.nodes.items():
                if n["floor"] == h_fl:
                    if math.hypot(n["x"] - hx, n["y"] - hy) <= (hradius + 15):
                        if nid not in blocked_nodes:
                            blocked_nodes.append(nid)

            # Block compromised corridor edges
            for edge in graph_model.edges:
                u = graph_model.nodes.get(edge["from"])
                v = graph_model.nodes.get(edge["to"])
                if u and v and u["floor"] == h_fl and v["floor"] == h_fl:
                    if point_to_segment_dist(hx, hy, u["x"], u["y"], v["x"], v["y"]) <= (hradius + 20):
                        pair = [edge["from"], edge["to"]]
                        if pair not in blocked_edges:
                            blocked_edges.append(pair)

        if target_exit and isinstance(target_exit, str):
            target_exit = [target_exit]

        result = routing_engine.calculate_evacuation_route(
            start_node_id=start_node,
            target_exit_ids=target_exit,
            blocked_edges=blocked_edges,
            blocked_nodes=blocked_nodes
        )

        return jsonify({
            "status": "success" if result.get("success") else "error",
            "result": result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================================================
# Session Authentication & User APIs
# ============================================================================

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticates safety officers and emergency wardens; creates session."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required."}), 400

    user = query_db("SELECT * FROM admin_users WHERE username = ?", [username], one=True)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"status": "error", "message": "Invalid username or password credentials."}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["full_name"] = user["full_name"]

    return jsonify({
        "status": "success",
        "message": f"Welcome back, {user['full_name']}.",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "full_name": user["full_name"]
        }
    })

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Clears the active authenticated session."""
    session.clear()
    return jsonify({"status": "success", "message": "Successfully logged out."})

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Checks the active user session."""
    if "user_id" in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": session.get("user_id"),
                "username": session.get("username"),
                "role": session.get("role"),
                "full_name": session.get("full_name")
            }
        })
    return jsonify({"authenticated": False, "user": None})

# ============================================================================
# Hazard State Management APIs (CRUD)
# ============================================================================

@app.route("/api/hazards", methods=["GET"])
def get_hazards():
    """Returns active hazard logs from SQLite database."""
    floor_filter = request.args.get("floor", type=int)
    if floor_filter is not None:
        hazards = query_db("SELECT * FROM hazards WHERE floor_id = ? ORDER BY reported_at DESC", [floor_filter])
    else:
        hazards = query_db("SELECT * FROM hazards ORDER BY reported_at DESC")
    return jsonify({"status": "success", "hazards": hazards, "total": len(hazards)})

@app.route("/api/hazards", methods=["POST"])
def create_hazard():
    """
    Registers a new hazard zone (fire, smoke, structural blockage).
    Payload: floor_id, location_x, location_y, type, severity, radius, description.
    """
    data = request.get_json() or {}
    floor_id = data.get("floor_id", 0)
    loc_x = float(data.get("location_x", 600))
    loc_y = float(data.get("location_y", 370))
    hazard_type = data.get("type", "fire")
    severity = data.get("severity", "high")
    radius = float(data.get("radius", 45.0))
    desc = data.get("description", f"Point-and-click placed {hazard_type} zone")
    reported_by = session.get("username", data.get("reported_by", "admin_portal"))

    res = execute_db(
        "INSERT INTO hazards (floor_id, location_x, location_y, type, severity, radius, description, reported_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [floor_id, loc_x, loc_y, hazard_type, severity, radius, desc, reported_by]
    )

    return jsonify({
        "status": "success",
        "hazard_id": res["lastrowid"],
        "message": f"Hazard #{res['lastrowid']} placed at Floor {floor_id} ({loc_x}, {loc_y})."
    }), 201

@app.route("/api/hazards/<int:hazard_id>", methods=["DELETE"])
def delete_hazard(hazard_id):
    """Removes a resolved hazard from active database records."""
    res = execute_db("DELETE FROM hazards WHERE id = ?", [hazard_id])
    if res["rowcount"] > 0:
        return jsonify({"status": "success", "message": f"Hazard #{hazard_id} cleared."})
    return jsonify({"status": "error", "message": f"Hazard #{hazard_id} not found."}), 404

@app.route("/api/hazards/clear", methods=["POST"])
def clear_all_hazards():
    """Purges all active hazards from the database."""
    execute_db("DELETE FROM hazards")
    execute_db("UPDATE paths SET is_blocked = 0")
    return jsonify({"status": "success", "message": "All hazards cleared and corridor paths reset."})

# ============================================================================
# Path State Management APIs
# ============================================================================

@app.route("/api/paths", methods=["GET"])
def get_paths():
    """Returns corridor and staircase paths with active blocked status."""
    floor_filter = request.args.get("floor", type=int)
    if floor_filter is not None:
        paths = query_db(
            "SELECT p.* FROM paths p "
            "JOIN nodes n1 ON p.from_node = n1.id "
            "WHERE n1.floor_id = ?",
            [floor_filter]
        )
    else:
        paths = query_db("SELECT * FROM paths")
    blocked_count = sum(1 for p in paths if p["is_blocked"])
    return jsonify({"status": "success", "paths": paths, "total": len(paths), "blocked_count": blocked_count})

@app.route("/api/paths/toggle-block", methods=["POST"])
def toggle_path_block():
    """Toggles corridor edge blockage in database."""
    data = request.get_json() or {}
    from_node = data.get("from_node")
    to_node = data.get("to_node")
    is_blocked = 1 if data.get("is_blocked", True) else 0

    if not from_node or not to_node:
        return jsonify({"status": "error", "message": "Both from_node and to_node required."}), 400

    execute_db(
        "UPDATE paths SET is_blocked = ? WHERE (from_node = ? AND to_node = ?) OR (from_node = ? AND to_node = ?)",
        [is_blocked, from_node, to_node, to_node, from_node]
    )

    return jsonify({
        "status": "success",
        "edge": f"{from_node}--{to_node}",
        "is_blocked": bool(is_blocked),
        "message": f"Path {from_node} <-> {to_node} set to {'BLOCKED' if is_blocked else 'CLEAR'}."
    })

# ============================================================================
# Stationary QR Localization & Direct Image Generation APIs
# ============================================================================

@app.route("/api/qr", methods=["GET"])
def get_qr_codes():
    """Lists all stationary QR checkpoints registered in Block A."""
    qr_list = query_db(
        "SELECT qr.*, n.x_coord, n.y_coord, n.name as node_name, n.code as room_code "
        "FROM qr_codes qr JOIN nodes n ON qr.node_id = n.id ORDER BY qr.floor_id ASC"
    )
    base_url = request.host_url.rstrip("/")
    for q in qr_list:
        q["scan_url"] = f"{base_url}/public?qr={q['code_id']}"
        q["image_url"] = f"/api/qr/image/{q['code_id']}"
    return jsonify({"status": "success", "qr_codes": qr_list, "total": len(qr_list)})

@app.route("/api/qr/<string:code_id>", methods=["GET"])
def resolve_qr_code(code_id):
    """
    Instant zero-setup indoor positioning via scanned QR code.
    Resolves code_id to exact node, floor, coordinate space, and direct scan URL.
    """
    qr = query_db(
        "SELECT qr.*, n.x_coord, n.y_coord, n.name as node_name, n.code as room_code, n.type as node_type "
        "FROM qr_codes qr JOIN nodes n ON qr.node_id = n.id WHERE qr.code_id = ?",
        [code_id],
        one=True
    )
    if not qr:
        return jsonify({"status": "error", "message": f"QR code '{code_id}' is not recognized in Block A."}), 404

    base_url = request.host_url.rstrip("/")
    scan_url = f"{base_url}/public?qr={code_id}"

    return jsonify({
        "status": "success",
        "qr": qr,
        "floor": qr["floor_id"],
        "node_id": qr["node_id"],
        "scan_url": scan_url,
        "image_url": f"/api/qr/image/{code_id}",
        "coordinates": {"x": qr["x_coord"], "y": qr["y_coord"]}
    })

@app.route("/api/qr/image/<string:code_id>", methods=["GET"])
def get_qr_image(code_id):
    """
    Dynamically generates and returns a genuine camera-scannable QR code image
    encoding the public evacuation guidance direct URL.
    Supports format=png (default) and format=svg.
    """
    qr_record = query_db("SELECT * FROM qr_codes WHERE code_id = ?", [code_id], one=True)
    if not qr_record:
        return jsonify({"status": "error", "message": f"QR checkpoint '{code_id}' not found."}), 404

    base_url = request.args.get("base_url") or request.host_url.rstrip("/")
    scan_url = f"{base_url}/public?qr={code_id}"
    fmt = request.args.get("format", "png").lower()

    if fmt == "svg":
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
        svg_xml = img.to_string(encoding="unicode")
        return Response(svg_xml, mimetype="image/svg+xml")
    else:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=3
        )
        qr.add_data(scan_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")

@app.route("/api/qr", methods=["POST"])
def register_qr_code():
    """Registers a new stationary QR marker label mapped to a node."""
    data = request.get_json() or {}
    code_id = data.get("code_id")
    node_id = data.get("node_id")
    floor_id = data.get("floor_id", 0)
    desc = data.get("description", "Stationary indoor QR checkpoint")
    label = data.get("location_label", code_id)

    if not code_id or not node_id:
        return jsonify({"status": "error", "message": "code_id and node_id are required."}), 400

    try:
        execute_db(
            "INSERT INTO qr_codes (code_id, node_id, floor_id, description, location_label) VALUES (?, ?, ?, ?, ?)",
            [code_id, node_id, floor_id, desc, label]
        )
        return jsonify({"status": "success", "message": f"QR code '{code_id}' registered successfully."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# In-memory store for Incident Commander / Admin live location
_COMMANDER_LOCATION = {
    "node_id": "NODE_ROOM_G_03",
    "floor_id": 0,
    "location_label": "Campus Security Command & Incident Post G-103",
    "description": "Ground Floor Primary Security Control & Incident Commander Post",
    "status": "Active On-Duty",
    "last_updated": "Live Telemetry"
}

@app.route("/api/commander/location", methods=["GET", "POST"])
def commander_location():
    """
    GET: Returns the current live stationary/mobile location of the Incident Commander / Admin.
    POST: Updates the commander's post or position.
    """
    global _COMMANDER_LOCATION
    if request.method == "POST":
        data = request.get_json() or {}
        if "node_id" in data:
            _COMMANDER_LOCATION["node_id"] = data["node_id"]
        if "floor_id" in data:
            _COMMANDER_LOCATION["floor_id"] = int(data["floor_id"])
        if "location_label" in data:
            _COMMANDER_LOCATION["location_label"] = data["location_label"]
        if "description" in data:
            _COMMANDER_LOCATION["description"] = data["description"]
        if "status" in data:
            _COMMANDER_LOCATION["status"] = data["status"]
        _COMMANDER_LOCATION["last_updated"] = "Updated just now"
        return jsonify({"status": "success", "commander": _COMMANDER_LOCATION})

    return jsonify({"status": "success", "commander": _COMMANDER_LOCATION})

# ============================================================================
# Occupancy, SOS & Drill Simulation APIs
# ============================================================================

@app.route("/api/occupancy", methods=["GET"])
def get_occupancy_summary():
    """
    Returns drill status metrics:
    total scanned count, inside building count, safely evacuated count, floor breakdown.
    """
    records = query_db("SELECT * FROM occupancy_sim")
    total = len(records)
    total_scanned = sum(1 for r in records if r.get("scanned_qr"))
    inside = sum(1 for r in records if r["status"] == "inside")
    safe = sum(1 for r in records if r["status"] in ["safe", "evacuated"])
    missing = sum(1 for r in records if r["status"] == "missing")

    by_floor = {f: 0 for f in range(5)}
    for r in records:
        if r["status"] == "inside" and r["floor_id"] in by_floor:
            by_floor[r["floor_id"]] += 1

    return jsonify({
        "status": "success",
        "metrics": {
            "total_scanned": total_scanned,
            "total_occupants": total,
            "inside_building": inside,
            "safely_evacuated": safe,
            "missing_or_trapped": missing
        },
        "by_floor": by_floor,
        "records": records
    })

@app.route("/api/occupancy/scan", methods=["POST"])
def record_qr_scan():
    """
    Handles immediate QR checkpoint scan from physical camera or test selector.
    Registers occupant as inside, increments total_scanned counter, and returns
    calculated nearest safe exit route with turn-by-turn guidance.
    """
    data = request.get_json() or {}
    code_id = data.get("qr_code") or data.get("code_id")
    occupant_id = data.get("occupant_id")

    if not code_id:
        return jsonify({"status": "error", "message": "qr_code or code_id required."}), 400

    qr = query_db(
        "SELECT qr.*, n.x_coord, n.y_coord, n.name as node_name, n.code as room_code, n.type as node_type "
        "FROM qr_codes qr JOIN nodes n ON qr.node_id = n.id WHERE qr.code_id = ?",
        [code_id],
        one=True
    )
    if not qr:
        return jsonify({"status": "error", "message": f"QR code '{code_id}' not recognized in Block A."}), 404

    if not occupant_id:
        import uuid
        occupant_id = f"SCAN_{uuid.uuid4().hex[:6].upper()}"

    floor_id = qr["floor_id"]
    node_id = qr["node_id"]

    # Log into audit table
    try:
        execute_db(
            "INSERT INTO qr_scans_log (occupant_id, code_id, floor_id, node_id) VALUES (?, ?, ?, ?)",
            [occupant_id, code_id, floor_id, node_id]
        )
    except Exception:
        pass

    # Upsert occupancy_sim record
    existing = query_db("SELECT id FROM occupancy_sim WHERE occupant_id = ?", [occupant_id], one=True)
    if existing:
        execute_db(
            "UPDATE occupancy_sim SET floor_id = ?, current_node = ?, scanned_qr = ?, status = 'inside', last_ping = CURRENT_TIMESTAMP WHERE occupant_id = ?",
            [floor_id, node_id, code_id, occupant_id]
        )
    else:
        execute_db(
            "INSERT INTO occupancy_sim (occupant_id, floor_id, current_node, status, scanned_qr) VALUES (?, ?, ?, 'inside', ?)",
            [occupant_id, floor_id, node_id, code_id]
        )

    # Compute immediate dynamic evacuation route
    db_blocked = query_db("SELECT from_node, to_node FROM paths WHERE is_blocked = 1")
    blocked_edges = [[r["from_node"], r["to_node"]] for r in db_blocked]

    blocked_nodes = []
    db_hazards = query_db("SELECT floor_id, location_x, location_y, radius FROM hazards")
    for h in db_hazards:
        h_fl = h["floor_id"]
        hx, hy = h["location_x"], h["location_y"]
        hradius = h.get("radius") or 45.0
        for nid, n in graph_model.nodes.items():
            if n["floor"] == h_fl:
                if math.hypot(n["x"] - hx, n["y"] - hy) <= hradius:
                    blocked_nodes.append(nid)

    route_res = routing_engine.calculate_evacuation_route(
        start_node_id=node_id,
        blocked_edges=blocked_edges,
        blocked_nodes=blocked_nodes
    )

    # Fetch updated counts
    all_recs = query_db("SELECT * FROM occupancy_sim")
    total_scanned = sum(1 for r in all_recs if r.get("scanned_qr"))
    inside_count = sum(1 for r in all_recs if r["status"] == "inside")
    safe_count = sum(1 for r in all_recs if r["status"] in ["safe", "evacuated"])

    return jsonify({
        "status": "success",
        "occupant_id": occupant_id,
        "location": {
            "code_id": qr["code_id"],
            "label": qr["location_label"],
            "description": qr["description"],
            "floor": qr["floor_id"],
            "node_id": qr["node_id"],
            "node_name": qr["node_name"],
            "room_code": qr["room_code"],
            "coordinates": {"x": qr["x_coord"], "y": qr["y_coord"]}
        },
        "route": route_res,
        "metrics": {
            "total_scanned": total_scanned,
            "inside_building": inside_count,
            "safely_evacuated": safe_count,
            "total_occupants": len(all_recs)
        }
    })

@app.route("/api/occupancy/report", methods=["POST"])
def report_occupant_status():
    """Occupant scans QR, advances, or confirms safe exit during drill."""
    data = request.get_json() or {}
    occupant_id = data.get("occupant_id", "ANON_OCCUPANT")
    status = data.get("status", "inside")
    current_node = data.get("current_node")
    floor_id = data.get("floor_id")
    safe_exit = data.get("safe_exit")
    scanned_qr = data.get("scanned_qr") or data.get("qr_code")

    existing = query_db("SELECT id, scanned_qr, current_node, floor_id FROM occupancy_sim WHERE occupant_id = ?", [occupant_id], one=True)
    if existing:
        final_qr = scanned_qr or existing.get("scanned_qr")
        final_node = current_node or existing.get("current_node") or "NODE_EXIT_G_MAIN"
        final_floor = floor_id if floor_id is not None else existing.get("floor_id", 0)
        execute_db(
            "UPDATE occupancy_sim SET status = ?, current_node = ?, floor_id = ?, safe_exit = ?, scanned_qr = ?, last_ping = CURRENT_TIMESTAMP WHERE occupant_id = ?",
            [status, final_node, final_floor, safe_exit, final_qr, occupant_id]
        )
    else:
        final_node = current_node or "NODE_EXIT_G_MAIN"
        final_floor = floor_id if floor_id is not None else 0
        execute_db(
            "INSERT INTO occupancy_sim (occupant_id, floor_id, current_node, status, safe_exit, scanned_qr) VALUES (?, ?, ?, ?, ?, ?)",
            [occupant_id, final_floor, final_node, status, safe_exit, scanned_qr]
        )

    # Return refreshed summary metrics
    records = query_db("SELECT * FROM occupancy_sim")
    total_scanned = sum(1 for r in records if r.get("scanned_qr"))
    inside = sum(1 for r in records if r["status"] == "inside")
    safe = sum(1 for r in records if r["status"] in ["safe", "evacuated"])

    return jsonify({
        "status": "success",
        "message": f"Status for '{occupant_id}' updated to '{status}'.",
        "metrics": {
            "total_scanned": total_scanned,
            "inside_building": inside,
            "safely_evacuated": safe,
            "total_occupants": len(records)
        }
    })

@app.route("/api/occupancy/reset", methods=["POST"])
def reset_occupancy_drill():
    """Resets occupancy simulation to initial drill state."""
    execute_db("DELETE FROM occupancy_sim")
    seed_all()
    records = query_db("SELECT * FROM occupancy_sim")
    total_scanned = sum(1 for r in records if r.get("scanned_qr"))
    inside = sum(1 for r in records if r["status"] == "inside")
    safe = sum(1 for r in records if r["status"] in ["safe", "evacuated"])

    return jsonify({
        "status": "success",
        "message": "Evacuation drill occupancy simulation reset to initial baseline.",
        "metrics": {
            "total_scanned": total_scanned,
            "inside_building": inside,
            "safely_evacuated": safe,
            "total_occupants": len(records)
        }
    })

@app.route("/api/simulation/populate", methods=["POST"])
def populate_simulation_occupants():
    """
    Populates simulated crowd for high-density evacuation drills.
    Spawns occupants across upper floors (Floors 1-4) in rooms and halls.
    """
    data = request.get_json() or {}
    count = int(data.get("count", 20))
    execute_db("DELETE FROM occupancy_sim")

    # Pick representative room nodes across floors 1 to 4
    candidate_nodes = [
        (4, "NODE_ROOM_4_06", "QR_4_AUDITORIUM"),
        (4, "NODE_ROOM_4_01", "QR_4_BOARDROOM"),
        (4, "N4_W_CENTER", None),
        (4, "N4_E_CENTER", None),
        (3, "NODE_ROOM_3_05", "QR_3_AILAB"),
        (3, "NODE_ROOM_3_01", "QR_3_LIBRARY"),
        (3, "NODE_ROOM_3_06", "QR_3_HPC"),
        (3, "N3_C_CENTER", None),
        (2, "NODE_ROOM_2_01", "QR_2_LECTURE"),
        (2, "NODE_ROOM_2_06", "QR_2_SEMINAR"),
        (2, "N2_W_NORTH", None),
        (2, "N2_E_SOUTH", None),
        (1, "NODE_ROOM_1_01", "QR_1_FACULTY"),
        (1, "NODE_ROOM_1_06", "QR_1_CSLAB"),
        (1, "N1_C_CENTER", "QR_1_BRIDGE"),
        (1, "N1_W_MID_N", None),
        (0, "NODE_ROOM_G_01", "QR_G_ADMIN"),
        (0, "NODE_ROOM_G_06", "QR_G_CAFE"),
        (0, "NODE_LOBBY_SOUTH", "QR_G_ATRIUM"),
        (0, "N0_W_MID_S", None)
    ]

    new_rows = []
    for i in range(count):
        tmpl = candidate_nodes[i % len(candidate_nodes)]
        occ_id = f"SIM_{i+1:03d}"
        floor_id = tmpl[0]
        node_id = tmpl[1]
        qr_code = tmpl[2]
        new_rows.append((occ_id, floor_id, node_id, "inside", qr_code))

    from database.db import execute_many
    execute_many(
        "INSERT INTO occupancy_sim (occupant_id, floor_id, current_node, status, scanned_qr) VALUES (?, ?, ?, ?, ?)",
        new_rows
    )

    records = query_db("SELECT * FROM occupancy_sim")
    total_scanned = sum(1 for r in records if r.get("scanned_qr"))
    inside = sum(1 for r in records if r["status"] == "inside")
    safe = sum(1 for r in records if r["status"] in ["safe", "evacuated"])

    return jsonify({
        "status": "success",
        "message": f"Populated {count} simulated occupants for evacuation drill.",
        "metrics": {
            "total_scanned": total_scanned,
            "inside_building": inside,
            "safely_evacuated": safe,
            "total_occupants": len(records)
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Starting Block A Digital Twin System on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
