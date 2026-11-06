"""
Database Seed Script: Populates Block A Digital Twin SQLite Database
Blueprint Section 11 Implementation
"""

import os
import sys
import json

# Ensure project root is in sys.path for direct script execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash
from database.db import init_db, execute_db, execute_many, query_db
from engine.graph_model import BlockAGraphModel

def seed_all():
    """Initializes schema and seeds all 7 relational tables."""
    init_db()

    # 1. Seed admin_users
    users_count = query_db("SELECT COUNT(*) as count FROM admin_users", one=True)["count"]
    if users_count == 0:
        admin_users_data = [
            ("admin", generate_password_hash("admin123"), "super_admin", "Chief Safety Commander"),
            ("warden_ground", generate_password_hash("warden123"), "floor_warden", "Ground Floor Fire Warden"),
            ("warden_f1", generate_password_hash("warden123"), "floor_warden", "First Floor Safety Marshal"),
            ("warden_f2", generate_password_hash("warden123"), "floor_warden", "Second Floor Safety Marshal"),
            ("warden_f3", generate_password_hash("warden123"), "floor_warden", "Third Floor Safety Marshal"),
            ("warden_f4", generate_password_hash("warden123"), "floor_warden", "Fourth Floor Safety Marshal")
        ]
        execute_many(
            "INSERT INTO admin_users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
            admin_users_data
        )
        print("[+] Seeded 6 admin personnel & safety officers.")

    # 2. Seed floors
    floors_count = query_db("SELECT COUNT(*) as count FROM floors", one=True)["count"]
    if floors_count == 0:
        floors_data = [
            (0, 0, "Ground Floor (Level 0)", "G", 10, 1),
            (1, 1, "First Floor (Level 1)", "1F", 10, 0),
            (2, 2, "Second Floor (Level 2)", "2F", 10, 0),
            (3, 3, "Third Floor (Level 3)", "3F", 9, 0),
            (4, 4, "Fourth Floor (Level 4)", "4F", 9, 0)
        ]
        execute_many(
            "INSERT INTO floors (id, floor_number, floor_name, short_code, total_rooms, has_exits) VALUES (?, ?, ?, ?, ?, ?)",
            floors_data
        )
        print("[+] Seeded 5 elevation levels (G through 4F).")

    # 3. Seed nodes & paths from BlockAGraphModel
    nodes_count = query_db("SELECT COUNT(*) as count FROM nodes", one=True)["count"]
    graph = BlockAGraphModel()

    if nodes_count == 0:
        nodes_batch = []
        for nid, n in graph.nodes.items():
            nodes_batch.append((
                n["id"],
                n["floor"],
                n["x"],
                n["y"],
                n["type"],
                n["name"],
                n.get("code", n["id"]),
                json.dumps(n.get("metadata", {}))
            ))
        execute_many(
            "INSERT INTO nodes (id, floor_id, x_coord, y_coord, type, name, code, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            nodes_batch
        )
        print(f"[+] Seeded {len(nodes_batch)} spatial waypoint nodes.")

    paths_count = query_db("SELECT COUNT(*) as count FROM paths", one=True)["count"]
    if paths_count == 0:
        paths_batch = []
        for e in graph.edges:
            paths_batch.append((
                e["from"],
                e["to"],
                e["weight"],
                0,
                e.get("type", "walkway"),
                1 if e.get("bidirectional", True) else 0
            ))
        execute_many(
            "INSERT OR IGNORE INTO paths (from_node, to_node, weight, is_blocked, edge_type, bidirectional) VALUES (?, ?, ?, ?, ?, ?)",
            paths_batch
        )
        print(f"[+] Seeded {len(paths_batch)} walkable corridor and stairwell edges.")

    # 4. Seed stationary QR codes (5 checkpoints per floor = 25 total)
    qr_data = [
        # Ground Floor (Level 0)
        ("QR_G_ATRIUM", "NODE_LOBBY_SOUTH", 0, "Ground Floor Central Atrium Wall Marker", "Central Atrium Portal"),
        ("QR_G_ADMIN", "NODE_ROOM_G_01", 0, "Admin Office Room Door Marker", "Admin & Accounts G-101"),
        ("QR_G_CLINIC", "NODE_ROOM_G_02", 0, "First Aid & Clinic Entry Doorway", "First Aid Clinic G-102"),
        ("QR_G_CAFE", "NODE_ROOM_G_06", 0, "Cafeteria Main Entrance Pillar", "Cafeteria G-106"),
        ("QR_G_SECURITY", "NODE_ROOM_G_03", 0, "Campus Security Command Doorway", "Security Command G-103"),

        # Floor 1 (Level 1)
        ("QR_1_FACULTY", "NODE_ROOM_1_01", 1, "Faculty Department Wing A Wall Checkpoint", "Faculty Dept 101"),
        ("QR_1_CSLAB", "NODE_ROOM_1_06", 1, "CS Software Lab Entrance Plaque", "CS Software Lab 106"),
        ("QR_1_NETLAB", "NODE_ROOM_1_07", 1, "Advanced Networks & Systems Lab Doorway", "Networks Lab 107"),
        ("QR_1_BRIDGE", "N1_C_CENTER", 1, "First Floor Skybridge Exhibition Walkway Marker", "Skybridge Center L1"),
        ("QR_1_STAIR_A", "STAIR_A_1", 1, "West Staircase A Landing Floor 1", "West Staircase A L1"),

        # Floor 2 (Level 2)
        ("QR_2_LECTURE", "NODE_ROOM_2_01", 2, "Smart Lecture Hall 201 Doorway", "Lecture Theater 201"),
        ("QR_2_SEMINAR", "NODE_ROOM_2_06", 2, "Multipurpose Seminar Hall 206 Door", "Seminar Hall 206"),
        ("QR_2_BRIDGE", "N2_C_CENTER", 2, "Level 2 Central Skybridge Walkway", "Skybridge Walkway L2"),
        ("QR_2_STAIR_A", "STAIR_A_2", 2, "Staircase A Landing Checkpoint Floor 2", "West Staircase A L2"),
        ("QR_2_STAIR_B", "STAIR_B_2", 2, "Staircase B Landing Checkpoint Floor 2", "East Staircase B L2"),

        # Floor 3 (Level 3)
        ("QR_3_LIBRARY", "NODE_ROOM_3_01", 3, "Central Department Library Check-in Station", "Library Stacks 301"),
        ("QR_3_AILAB", "NODE_ROOM_3_05", 3, "AI & Autonomous Robotics Lab Entry Door", "AI & Robotics Lab 305"),
        ("QR_3_HPC", "NODE_ROOM_3_06", 3, "HPC Supercomputing Cluster Vault Wall", "HPC Facility 306"),
        ("QR_3_STAIR_A", "STAIR_A_3", 3, "West Staircase A Landing Floor 3", "West Staircase A L3"),
        ("QR_3_STAIR_B", "STAIR_B_3", 3, "East Staircase B Landing Floor 3", "East Staircase B L3"),

        # Floor 4 (Level 4)
        ("QR_4_BOARDROOM", "NODE_ROOM_4_01", 4, "Executive Boardroom Entrance Plaque", "Boardroom 401"),
        ("QR_4_AUDITORIUM", "NODE_ROOM_4_06", 4, "Grand Auditorium Main Foyer Column", "Grand Auditorium 406"),
        ("QR_4_ROOF_EXIT", "N4_C_CENTER", 4, "Roof Observatory & Skydeck Spine", "Skydeck Access L4"),
        ("QR_4_STAIR_A", "STAIR_A_4", 4, "West Staircase A Top Landing Floor 4", "West Staircase A L4"),
        ("QR_4_STAIR_B", "STAIR_B_4", 4, "East Staircase B Top Landing Floor 4", "East Staircase B L4")
    ]
    execute_many(
        "INSERT OR REPLACE INTO qr_codes (code_id, node_id, floor_id, description, location_label) VALUES (?, ?, ?, ?, ?)",
        qr_data
    )
    print(f"[+] Seeded {len(qr_data)} stationary QR localization checkpoints (5 per floor).")

    # 5. Seed occupancy simulation records
    occ_count = query_db("SELECT COUNT(*) as count FROM occupancy_sim", one=True)["count"]
    if occ_count == 0:
        occ_data = [
            ("OCC_001", 4, "NODE_ROOM_4_06", "inside", "QR_4_AUDITORIUM", None),
            ("OCC_002", 4, "NODE_ROOM_4_01", "inside", "QR_4_BOARDROOM", None),
            ("OCC_003", 3, "NODE_ROOM_3_05", "inside", "QR_3_AILAB", None),
            ("OCC_004", 3, "NODE_ROOM_3_01", "safe", "QR_3_LIBRARY", "NODE_EXIT_G_MAIN"),
            ("OCC_005", 3, "NODE_ROOM_3_06", "inside", "QR_3_HPC", None),
            ("OCC_006", 2, "NODE_ROOM_2_01", "evacuated", "QR_2_LECTURE", "NODE_EXIT_G_WEST"),
            ("OCC_007", 2, "NODE_ROOM_2_06", "safe", "QR_2_SEMINAR", "NODE_EXIT_G_EAST"),
            ("OCC_008", 1, "NODE_ROOM_1_06", "inside", "QR_1_CSLAB", None),
            ("OCC_009", 1, "NODE_ROOM_1_01", "safe", "QR_1_FACULTY", "NODE_EXIT_G_MAIN"),
            ("OCC_010", 0, "NODE_ROOM_G_06", "safe", "QR_G_CAFE", "NODE_EXIT_G_EAST"),
            ("OCC_011", 0, "NODE_ROOM_G_01", "safe", "QR_G_ADMIN", "NODE_EXIT_G_WEST"),
            ("OCC_012", 2, "N2_W_CENTER", "inside", None, None)
        ]
        execute_many(
            "INSERT INTO occupancy_sim (occupant_id, floor_id, current_node, status, scanned_qr, safe_exit) VALUES (?, ?, ?, ?, ?, ?)",
            occ_data
        )
        print(f"[+] Seeded {len(occ_data)} occupancy tracking records.")

if __name__ == "__main__":
    seed_all()

