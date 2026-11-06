import os
import json
import math
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, close_db, query_db, execute_db, init_db
from database.seed_data import seed_all
from engine.graph_model import BlockAGraphModel
from engine.dijkstra import DijkstraRoutingEngine

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "block-a-digital-twin-safety-key-2026")
CORS(app, supports_credentials=True)

# Register database connection teardown
app.teardown_appcontext(close_db)

DATA_PATH = os.path.join(app.root_path, "static", "data", "building_model.json")

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

        if blocked_edges is None:
            db_blocked = query_db("SELECT from_node, to_node FROM paths WHERE is_blocked = 1")
            blocked_edges = [[r["from_node"], r["to_node"]] for r in db_blocked]

        if blocked_nodes is None:
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
# Stationary QR Localization APIs
# ============================================================================

@app.route("/api/qr", methods=["GET"])
def get_qr_codes():
    """Lists all stationary QR checkpoints registered in Block A."""
    qr_list = query_db(
        "SELECT qr.*, n.x_coord, n.y_coord, n.name as node_name, n.code as room_code "
        "FROM qr_codes qr JOIN nodes n ON qr.node_id = n.id ORDER BY qr.floor_id ASC"
    )
    return jsonify({"status": "success", "qr_codes": qr_list, "total": len(qr_list)})

@app.route("/api/qr/<string:code_id>", methods=["GET"])
def resolve_qr_code(code_id):
    """
    Instant zero-setup indoor positioning via scanned QR code.
    Resolves code_id to exact node, floor, and coordinate space.
    """
    qr = query_db(
        "SELECT qr.*, n.x_coord, n.y_coord, n.name as node_name, n.code as room_code, n.type as node_type "
        "FROM qr_codes qr JOIN nodes n ON qr.node_id = n.id WHERE qr.code_id = ?",
        [code_id],
        one=True
    )
    if not qr:
        return jsonify({"status": "error", "message": f"QR code '{code_id}' is not recognized in Block A."}), 404

    return jsonify({
        "status": "success",
        "qr": qr,
        "floor": qr["floor_id"],
        "node_id": qr["node_id"],
        "coordinates": {"x": qr["x_coord"], "y": qr["y_coord"]}
    })

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

# ============================================================================
# Occupancy, SOS & Drill Simulation APIs
# ============================================================================

@app.route("/api/occupancy", methods=["GET"])
def get_occupancy_summary():
    """Returns drill status metrics: inside count, safe exits, unaccounted occupants."""
    records = query_db("SELECT * FROM occupancy_sim")
    total = len(records)
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
            "total_occupants": total,
            "inside_building": inside,
            "safely_evacuated": safe,
            "missing_or_trapped": missing
        },
        "by_floor": by_floor,
        "records": records
    })

@app.route("/api/occupancy/report", methods=["POST"])
def report_occupant_status():
    """Occupant scans QR or updates status during drill."""
    data = request.get_json() or {}
    occupant_id = data.get("occupant_id", "ANON_OCCUPANT")
    status = data.get("status", "inside")
    current_node = data.get("current_node")
    floor_id = data.get("floor_id", 0)
    safe_exit = data.get("safe_exit")

    existing = query_db("SELECT id FROM occupancy_sim WHERE occupant_id = ?", [occupant_id], one=True)
    if existing:
        execute_db(
            "UPDATE occupancy_sim SET status = ?, current_node = ?, floor_id = ?, safe_exit = ?, last_ping = CURRENT_TIMESTAMP WHERE occupant_id = ?",
            [status, current_node, floor_id, safe_exit, occupant_id]
        )
    else:
        execute_db(
            "INSERT INTO occupancy_sim (occupant_id, floor_id, current_node, status, safe_exit) VALUES (?, ?, ?, ?, ?)",
            [occupant_id, floor_id, current_node, status, safe_exit]
        )

    return jsonify({"status": "success", "message": f"Status for '{occupant_id}' updated to '{status}'."})

@app.route("/api/occupancy/reset", methods=["POST"])
def reset_occupancy_drill():
    """Resets occupancy simulation to initial drill state."""
    execute_db("DELETE FROM occupancy_sim")
    seed_all()
    return jsonify({"status": "success", "message": "Evacuation drill occupancy simulation reset."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Starting Block A Digital Twin System on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
