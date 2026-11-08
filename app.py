import os
import json
import math
import io
import time
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

def point_to_segment_dist(px, py, x1, y1, x2, y2):
    """Calculates perpendicular Euclidean distance from point (px, py) to line segment (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / l2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

def get_active_hazard_exclusions(custom_blocked_nodes=None, custom_blocked_edges=None):
    """
    Computes compromised nodes and blocked corridor edges by intersecting all active hazards
    and barricades in SQLite database against graph topology.
    Returns (blocked_nodes, blocked_edges, hazards_list).
    """
    blocked_edges = []
    if custom_blocked_edges is not None:
        for item in custom_blocked_edges:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                blocked_edges.append([item[0], item[1]])
            elif isinstance(item, str) and "--" in item:
                u, v = item.split("--")
                blocked_edges.append([u, v])

    # Always incorporate blocked corridor gates from the database
    db_blocked = query_db("SELECT from_node, to_node FROM paths WHERE is_blocked = 1")
    for r in db_blocked:
        pair1 = [r["from_node"], r["to_node"]]
        pair2 = [r["to_node"], r["from_node"]]
        if pair1 not in blocked_edges:
            blocked_edges.append(pair1)
        if pair2 not in blocked_edges:
            blocked_edges.append(pair2)

    blocked_nodes = list(custom_blocked_nodes) if custom_blocked_nodes is not None else []

    db_hazards = query_db("SELECT * FROM hazards")
    for h in db_hazards:
        h_fl = h["floor_id"]
        hx, hy = float(h["location_x"]), float(h["location_y"])
        hradius = float(h.get("radius") or 45.0)

        # Block compromised nodes within hazard radius + safety margin
        for nid, n in graph_model.nodes.items():
            if n["floor"] == h_fl:
                if math.hypot(n["x"] - hx, n["y"] - hy) <= (hradius + 15):
                    if nid not in blocked_nodes:
                        blocked_nodes.append(nid)

        # Block compromised corridor edges traversing through the hazard radius
        for edge in graph_model.edges:
            u = graph_model.nodes.get(edge["from"])
            v = graph_model.nodes.get(edge["to"])
            if u and v and u["floor"] == h_fl and v["floor"] == h_fl:
                if point_to_segment_dist(hx, hy, u["x"], u["y"], v["x"], v["y"]) <= (hradius + 20):
                    pair1 = [edge["from"], edge["to"]]
                    pair2 = [edge["to"], edge["from"]]
                    if pair1 not in blocked_edges:
                        blocked_edges.append(pair1)
                    if pair2 not in blocked_edges:
                        blocked_edges.append(pair2)

    return blocked_nodes, blocked_edges, db_hazards

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
        req_blocked_edges = data.get("blocked_edges")
        req_blocked_nodes = data.get("blocked_nodes")

        blocked_nodes, blocked_edges, db_hazards = get_active_hazard_exclusions(req_blocked_nodes, req_blocked_edges)

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
            "result": result,
            "blocked_nodes": blocked_nodes,
            "blocked_edges": blocked_edges,
            "hazards_count": len(db_hazards)
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

# ============================================================================
# Emergency System Activation & Master QR Control State
# ============================================================================

_SYSTEM_STATE = {
    "is_active": True,
    "status": "active",
    "emergency_type": "fire_evacuation",
    "activated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "qr_codes_activated": True,
    "message": "Block A Smart Evacuation System Active - All QRs Armed"
}

@app.route("/api/system/status", methods=["GET"])
def get_system_status():
    """Returns the current master emergency system state and QR activation status."""
    return jsonify({
        "status": "success",
        "system": _SYSTEM_STATE
    })

@app.route("/api/system/start", methods=["POST"])
def start_system_emergency():
    """
    Activates the emergency evacuation system, arms all stationary and mobile QR markers,
    and sounds evacuation protocol alerts across the digital twin.
    """
    global _SYSTEM_STATE
    data = request.get_json(silent=True) or {}
    emergency_type = data.get("emergency_type", "fire_evacuation")
    
    _SYSTEM_STATE["is_active"] = True
    _SYSTEM_STATE["status"] = "active"
    _SYSTEM_STATE["emergency_type"] = emergency_type
    _SYSTEM_STATE["activated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _SYSTEM_STATE["qr_codes_activated"] = True
    _SYSTEM_STATE["message"] = "Emergency Evacuation System Started - All 25 Checkpoint QRs Armed"

    return jsonify({
        "status": "success",
        "message": "Emergency evacuation system successfully started. All QRs armed.",
        "system": _SYSTEM_STATE
    })

@app.route("/api/system/standby", methods=["POST"])
def standby_system_emergency():
    """
    Sets the evacuation system into standby monitoring mode (normal operations).
    """
    global _SYSTEM_STATE
    _SYSTEM_STATE["is_active"] = False
    _SYSTEM_STATE["status"] = "standby"
    _SYSTEM_STATE["qr_codes_activated"] = False
    _SYSTEM_STATE["message"] = "System in Standby Monitoring - Normal Building Operations"

    return jsonify({
        "status": "success",
        "message": "System set to Standby Monitoring mode.",
        "system": _SYSTEM_STATE
    })

@app.route("/api/qr", methods=["POST"])
def register_qr_code():
    """
    Registers a new stationary QR marker label mapped to a node.
    Enforces rule: QR checkpoints can only be placed IF AND ONLY IF system is ACTIVE.
    Supports point-and-click dynamic placement with x_coord and y_coord.
    """
    global _SYSTEM_STATE
    if not _SYSTEM_STATE.get("is_active"):
        return jsonify({
            "status": "error",
            "message": "QR checkpoints can only be placed when the Emergency System is ACTIVE. Please activate the system first."
        }), 403

    data = request.get_json() or {}
    code_id = data.get("code_id")
    floor_id = int(data.get("floor_id", 0))
    desc = data.get("description", "Stationary indoor QR checkpoint")
    label = data.get("location_label") or code_id
    node_id = data.get("node_id")
    x_coord = data.get("x_coord")
    y_coord = data.get("y_coord")

    if not code_id and label:
        clean_name = "".join(c if c.isalnum() else "_" for c in label.upper()).strip("_")
        code_id = f"QR_{floor_id}_{clean_name}"[:24]

    if not code_id:
        return jsonify({"status": "error", "message": "code_id or location_label is required."}), 400

    # Dynamic spatial placement on canvas
    if x_coord is not None and y_coord is not None:
        x_val = float(x_coord)
        y_val = float(y_coord)

        if not node_id:
            # Check for closest node on this floor
            closest_nid = None
            closest_dist = float("inf")
            for nid, n in graph_model.nodes.items():
                if n["floor"] == floor_id:
                    d = math.hypot(n["x"] - x_val, n["y"] - y_val)
                    if d < closest_dist:
                        closest_dist = d
                        closest_nid = nid

            if closest_dist <= 35 and closest_nid:
                node_id = closest_nid
            else:
                new_nid = f"NODE_CUSTOM_{code_id}"
                node_id = new_nid
                execute_db(
                    "INSERT OR REPLACE INTO nodes (id, floor_id, x_coord, y_coord, type, name, code) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [new_nid, floor_id, x_val, y_val, "corridor", label, code_id]
                )
                if closest_nid:
                    w = round(closest_dist * 0.25, 2)
                    execute_db(
                        "INSERT OR IGNORE INTO paths (from_node, to_node, weight, is_blocked, edge_type, bidirectional) VALUES (?, ?, ?, 0, 'corridor', 1)",
                        [new_nid, closest_nid, w]
                    )
                    execute_db(
                        "INSERT OR IGNORE INTO paths (from_node, to_node, weight, is_blocked, edge_type, bidirectional) VALUES (?, ?, ?, 0, 'corridor', 1)",
                        [closest_nid, new_nid, w]
                    )
                # Update in-memory graph model for immediate dynamic routing
                graph_model.nodes[new_nid] = {
                    "id": new_nid,
                    "floor": floor_id,
                    "x": x_val,
                    "y": y_val,
                    "type": "corridor",
                    "name": label,
                    "code": code_id
                }
                if closest_nid:
                    if new_nid not in graph_model.adjacency:
                        graph_model.adjacency[new_nid] = []
                    if closest_nid not in graph_model.adjacency:
                        graph_model.adjacency[closest_nid] = []
                    graph_model.adjacency[new_nid].append((closest_nid, w, "corridor"))
                    graph_model.adjacency[closest_nid].append((new_nid, w, "corridor"))
                    graph_model.edges.append({"from": new_nid, "to": closest_nid, "weight": w, "type": "corridor", "bidirectional": True})

    if not node_id:
        return jsonify({"status": "error", "message": "node_id or valid coordinates are required."}), 400

    try:
        execute_db(
            "INSERT OR REPLACE INTO qr_codes (code_id, node_id, floor_id, description, location_label) VALUES (?, ?, ?, ?, ?)",
            [code_id, node_id, floor_id, desc, label]
        )
        base_url = request.host_url.rstrip("/")
        return jsonify({
            "status": "success",
            "message": f"QR checkpoint '{code_id}' registered successfully.",
            "qr": {
                "code_id": code_id,
                "node_id": node_id,
                "floor_id": floor_id,
                "location_label": label,
                "description": desc,
                "scan_url": f"{base_url}/public?qr={code_id}",
                "image_url": f"/api/qr/image/{code_id}"
            }
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ============================================================================
# IoT Environmental Sensors & AI Surveillance Cameras APIs
# ============================================================================

_AUTOMATION_ENABLED = True

@app.route("/api/sensors", methods=["GET"])
def get_sensors():
    """Returns active IoT sensors and AI surveillance cameras with live telemetry status."""
    floor_filter = request.args.get("floor", type=int)
    if floor_filter is not None:
        sensors = query_db("SELECT * FROM iot_devices WHERE floor_id = ? ORDER BY id ASC", [floor_filter])
    else:
        sensors = query_db("SELECT * FROM iot_devices ORDER BY floor_id ASC, id ASC")
    
    return jsonify({
        "status": "success",
        "automation_enabled": _AUTOMATION_ENABLED,
        "sensors": sensors,
        "total": len(sensors)
    })

@app.route("/api/sensors/toggle-automation", methods=["POST"])
def toggle_sensor_automation():
    """Toggles automated emergency detection and hazard spawning from IoT sensor grid."""
    global _AUTOMATION_ENABLED
    data = request.get_json(silent=True) or {}
    if "enabled" in data:
        _AUTOMATION_ENABLED = bool(data["enabled"])
    else:
        _AUTOMATION_ENABLED = not _AUTOMATION_ENABLED

    return jsonify({
        "status": "success",
        "automation_enabled": _AUTOMATION_ENABLED,
        "message": f"Automated IoT/AI Hazard Detection is now {'ENABLED' if _AUTOMATION_ENABLED else 'DISABLED'}."
    })

@app.route("/api/sensors/<string:device_id>/trigger", methods=["POST"])
def trigger_sensor_alert(device_id):
    """
    Simulates or logs a hazard detection event on an IoT sensor or AI CCTV camera.
    If automation is enabled, automatically registers a fire/smoke hazard at device coordinates.
    """
    dev = query_db("SELECT * FROM iot_devices WHERE id = ?", [device_id], one=True)
    if not dev:
        return jsonify({"status": "error", "message": f"IoT device '{device_id}' not found."}), 404

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    reading = "CRITICAL ALERT: Hazard Signature Detected"
    execute_db(
        "UPDATE iot_devices SET status = 'alert', last_reading = ?, last_triggered = ? WHERE id = ?",
        [reading, now_str, device_id]
    )

    hazard_id = None
    if _AUTOMATION_ENABLED:
        hz_type = "smoke" if "smoke" in dev["type"] else "fire"
        res = execute_db(
            "INSERT INTO hazards (floor_id, location_x, location_y, type, severity, radius, description, reported_by) "
            "VALUES (?, ?, ?, ?, 'critical', 48.0, ?, 'AI_IoT_Automated_Grid')",
            [dev["floor_id"], dev["location_x"], dev["location_y"], hz_type, f"Automated detection from {dev['name']}"]
        )
        hazard_id = res["lastrowid"]

    updated_dev = query_db("SELECT * FROM iot_devices WHERE id = ?", [device_id], one=True)
    return jsonify({
        "status": "success",
        "message": f"Sensor '{dev['name']}' triggered alert status.",
        "device": updated_dev,
        "automation_active": _AUTOMATION_ENABLED,
        "hazard_created_id": hazard_id
    })

@app.route("/api/sensors/<string:device_id>/reset", methods=["POST"])
def reset_sensor_device(device_id):
    """Resets an IoT device or AI camera back to normal nominal state."""
    dev = query_db("SELECT * FROM iot_devices WHERE id = ?", [device_id], one=True)
    if not dev:
        return jsonify({"status": "error", "message": f"IoT device '{device_id}' not found."}), 404

    execute_db(
        "UPDATE iot_devices SET status = 'normal', last_reading = 'Nominal telemetry (System Normal)' WHERE id = ?",
        [device_id]
    )
    updated_dev = query_db("SELECT * FROM iot_devices WHERE id = ?", [device_id], one=True)
    return jsonify({
        "status": "success",
        "message": f"Device '{dev['name']}' reset to normal operational state.",
        "device": updated_dev
    })

@app.route("/api/sensors/reset-all", methods=["POST"])
def reset_all_sensors():
    """Resets all IoT sensors and AI CCTV cameras back to normal operational state."""
    execute_db("UPDATE iot_devices SET status = 'normal', last_reading = 'Nominal telemetry'")
    sensors = query_db("SELECT * FROM iot_devices ORDER BY floor_id ASC, id ASC")
    return jsonify({
        "status": "success",
        "message": "All IoT sensors and AI cameras restored to nominal operational state.",
        "sensors": sensors
    })

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
    GET: Returns current live location of Incident Commander.
    POST: Updates commander's post.
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

    # Compute immediate dynamic evacuation route with full hazard exclusion (nodes & corridor edges)
    blocked_nodes, blocked_edges, hazards_list = get_active_hazard_exclusions()

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
        "hazards": hazards_list,
        "blocked_nodes": blocked_nodes,
        "blocked_edges": blocked_edges,
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
