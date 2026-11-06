"""
Automated Test Suite for Phase 3: Backend Architecture & Database Design
Validates SQLite schemas, session authentication, hazard CRUD, QR resolution, and occupancy tracking.
"""

import pytest
from app import app
from database.db import query_db, execute_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_sqlite_tables_exist():
    """Verify all 7 relational tables from Blueprint Section 11 exist and have records."""
    tables = query_db("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_names = {t["name"] for t in tables}
    expected_tables = {"admin_users", "floors", "nodes", "paths", "qr_codes", "hazards", "occupancy_sim"}
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"

    # Verify counts
    assert query_db("SELECT COUNT(*) as c FROM floors", one=True)["c"] == 5
    assert query_db("SELECT COUNT(*) as c FROM nodes", one=True)["c"] >= 60
    assert query_db("SELECT COUNT(*) as c FROM paths", one=True)["c"] >= 70
    assert query_db("SELECT COUNT(*) as c FROM qr_codes", one=True)["c"] >= 10
    assert query_db("SELECT COUNT(*) as c FROM admin_users", one=True)["c"] >= 1

def test_session_authentication_flow(client):
    """Test login, session me check, and logout."""
    # 1. Invalid login
    res_bad = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res_bad.status_code == 401

    # 2. Valid login
    res_good = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_good.status_code == 200
    data = res_good.get_json()
    assert data["status"] == "success"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "super_admin"

    # 3. /api/auth/me in session
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 200
    assert res_me.get_json()["authenticated"] is True

    # 4. Logout
    res_logout = client.post("/api/auth/logout")
    assert res_logout.status_code == 200

    # 5. /api/auth/me after logout
    res_me2 = client.get("/api/auth/me")
    assert res_me2.get_json()["authenticated"] is False

def test_hazard_crud_lifecycle(client):
    """Test adding, listing, querying, and deleting dynamic hazards."""
    # Add a fire hazard on Floor 2
    res_add = client.post("/api/hazards", json={
        "floor_id": 2,
        "location_x": 925,
        "location_y": 175,
        "type": "fire",
        "severity": "critical",
        "radius": 50.0,
        "description": "Simulated fire near Staircase B Floor 2"
    })
    assert res_add.status_code == 201
    haz_id = res_add.get_json()["hazard_id"]

    # Verify in list
    res_list = client.get("/api/hazards?floor=2")
    assert res_list.status_code == 200
    hazards = res_list.get_json()["hazards"]
    assert any(h["id"] == haz_id for h in hazards)

    # Delete the hazard
    res_del = client.delete(f"/api/hazards/{haz_id}")
    assert res_del.status_code == 200

    # Verify deleted
    res_list2 = client.get(f"/api/hazards?floor=2")
    assert not any(h["id"] == haz_id for h in res_list2.get_json()["hazards"])

def test_path_block_toggling(client):
    """Test toggling is_blocked state on walkable corridor paths."""
    edge_u = "N1_W_CENTER"
    edge_v = "N1_C_WEST"

    # Toggle to blocked
    res_block = client.post("/api/paths/toggle-block", json={
        "from_node": edge_u,
        "to_node": edge_v,
        "is_blocked": True
    })
    assert res_block.status_code == 200
    assert res_block.get_json()["is_blocked"] is True

    # Check in DB
    row = query_db(
        "SELECT is_blocked FROM paths WHERE (from_node = ? AND to_node = ?) OR (from_node = ? AND to_node = ?)",
        [edge_u, edge_v, edge_v, edge_u],
        one=True
    )
    assert row["is_blocked"] == 1

    # Toggle back to clear
    res_unblock = client.post("/api/paths/toggle-block", json={
        "from_node": edge_u,
        "to_node": edge_v,
        "is_blocked": False
    })
    assert res_unblock.status_code == 200
    assert res_unblock.get_json()["is_blocked"] is False

def test_stationary_qr_code_resolution(client):
    """Test scanning/resolving a stationary QR code for indoor floor and node positioning."""
    # Test valid QR code
    res_qr = client.get("/api/qr/QR_3_AILAB")
    assert res_qr.status_code == 200
    data = res_qr.get_json()
    assert data["status"] == "success"
    assert data["floor"] == 3
    assert data["node_id"] == "NODE_ROOM_3_05"
    assert data["coordinates"]["x"] == 890
    assert data["coordinates"]["y"] == 290

    # Test unknown QR code
    res_unknown = client.get("/api/qr/UNKNOWN_CODE_999")
    assert res_unknown.status_code == 404

def test_occupancy_simulation_tracking(client):
    """Test occupancy drill reporting and statistics."""
    # Check current summary
    res_occ = client.get("/api/occupancy")
    assert res_occ.status_code == 200
    metrics = res_occ.get_json()["metrics"]
    assert metrics["total_occupants"] >= 10

    # Occupant reports safe evacuation at South Exit
    res_rep = client.post("/api/occupancy/report", json={
        "occupant_id": "TEST_STUDENT_42",
        "floor_id": 0,
        "status": "safe",
        "current_node": "NODE_EXIT_G_MAIN",
        "safe_exit": "NODE_EXIT_G_MAIN"
    })
    assert res_rep.status_code == 200

    # Verify updated record
    rec = query_db("SELECT * FROM occupancy_sim WHERE occupant_id = 'TEST_STUDENT_42'", one=True)
    assert rec is not None
    assert rec["status"] == "safe"

    # Cleanup
    execute_db("DELETE FROM occupancy_sim WHERE occupant_id = 'TEST_STUDENT_42'")

def test_database_driven_dijkstra_rerouting(client):
    """Verify that /api/route automatically reads active DB hazards without manual payload."""
    # Clear any leftover hazards
    client.post("/api/hazards/clear")

    # Baseline route from Floor 3 AI Lab (normally exits through East/Main exit)
    res_base = client.post("/api/route", json={"start_node": "NODE_ROOM_3_05"})
    assert res_base.status_code == 200
    base_exit = res_base.get_json()["result"]["target_exit"]

    # Place a fire hazard directly blocking Main Exit in SQLite DB
    client.post("/api/hazards", json={
        "floor_id": 0,
        "location_x": 600,
        "location_y": 620,
        "type": "fire",
        "radius": 60.0
    })

    # Call /api/route without passing any blocked nodes - engine must read from SQLite!
    res_reroute = client.post("/api/route", json={"start_node": "NODE_ROOM_G_01"})
    assert res_reroute.status_code == 200
    new_exit = res_reroute.get_json()["result"]["target_exit"]
    assert new_exit != "NODE_EXIT_G_MAIN"
    assert new_exit in ["NODE_EXIT_G_WEST", "NODE_EXIT_G_EAST"]

    # Cleanup
    client.post("/api/hazards/clear")

