"""
Automated Test Suite for Phase 4: Admin Emergency Management Portal
Validates /admin dashboard access, point-and-click hazard deployment, corridor barricading, and drill controls.
"""

import pytest
from app import app
from database.db import query_db, execute_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_admin_portal_view(client):
    """Test that /admin loads the emergency management dashboard."""
    res = client.get("/admin")
    assert res.status_code == 200
    assert b"Block A Emergency Management Portal" in res.data
    assert b"Incident Simulation, Barricades & Drill Metrics" in res.data
    assert b"Printable QR Code Testing Kit" in res.data

def test_point_and_click_hazard_creation(client):
    """Test dynamic deployment of fire markers, smoke zones, and debris barricades."""
    # Deploy a fire hazard at (300, 400) on Floor 2
    res_fire = client.post("/api/hazards", json={
        "floor_id": 2,
        "location_x": 300,
        "location_y": 400,
        "type": "fire",
        "radius": 45,
        "description": "Point-and-click test fire"
    })
    assert res_fire.status_code == 201
    fire_id = res_fire.get_json()["hazard_id"]

    # Deploy a smoke obstacle on Floor 1
    res_smoke = client.post("/api/hazards", json={
        "floor_id": 1,
        "location_x": 600,
        "location_y": 370,
        "type": "smoke",
        "radius": 60,
        "description": "Point-and-click test smoke"
    })
    assert res_smoke.status_code == 201
    smoke_id = res_smoke.get_json()["hazard_id"]

    # Verify both exist in DB
    hazards = query_db("SELECT id, type, floor_id FROM hazards WHERE id IN (?, ?)", [fire_id, smoke_id])
    assert len(hazards) == 2

    # Clean up test hazards
    client.delete(f"/api/hazards/{fire_id}")
    client.delete(f"/api/hazards/{smoke_id}")

def test_corridor_barricade_controls(client):
    """Test corridor barricade toggle switches from the admin panel."""
    edge_u = "N2_C_WEST"
    edge_v = "N2_C_CENTER"

    # Place barricade
    res_block = client.post("/api/paths/toggle-block", json={
        "from_node": edge_u,
        "to_node": edge_v,
        "is_blocked": True
    })
    assert res_block.status_code == 200
    assert res_block.get_json()["is_blocked"] is True

    # Verify path in SQLite is blocked
    row = query_db(
        "SELECT is_blocked FROM paths WHERE (from_node = ? AND to_node = ?) OR (from_node = ? AND to_node = ?)",
        [edge_u, edge_v, edge_v, edge_u],
        one=True
    )
    assert row["is_blocked"] == 1

    # Remove barricade
    res_unblock = client.post("/api/paths/toggle-block", json={
        "from_node": edge_u,
        "to_node": edge_v,
        "is_blocked": False
    })
    assert res_unblock.status_code == 200
    assert res_unblock.get_json()["is_blocked"] is False

def test_simulation_center_all_clear(client):
    """Test the all-clear reset action: clears all active hazards and unblocks corridors."""
    # Add dummy hazard and blocked path
    client.post("/api/hazards", json={"floor_id": 0, "location_x": 500, "location_y": 500, "type": "fire"})
    client.post("/api/paths/toggle-block", json={"from_node": "N1_W_NORTH", "to_node": "N1_W_MID_N", "is_blocked": True})

    # Trigger all-clear
    res_clear = client.post("/api/hazards/clear")
    assert res_clear.status_code == 200

    # Verify active hazards is 0
    haz_count = query_db("SELECT COUNT(*) as c FROM hazards", one=True)["c"]
    assert haz_count == 0

    # Verify blocked paths is 0
    blocked_count = query_db("SELECT COUNT(*) as c FROM paths WHERE is_blocked = 1", one=True)["c"]
    assert blocked_count == 0

def test_printable_qr_code_kit(client):
    """Test retrieving printable QR code checkpoints for physical prototype markers."""
    res_qr = client.get("/api/qr")
    assert res_qr.status_code == 200
    qr_codes = res_qr.get_json()["qr_codes"]
    assert len(qr_codes) >= 10

    # Verify key checkpoints exist for all wings and floors
    code_ids = {q["code_id"] for q in qr_codes}
    assert "QR_3_AILAB" in code_ids
    assert "QR_4_AUDITORIUM" in code_ids
    assert "QR_G_ATRIUM" in code_ids
    assert "QR_2_LECTURE" in code_ids

def test_occupancy_evacuation_status_cards(client):
    """Test real-time occupancy counting for admin cards."""
    res = client.get("/api/occupancy")
    assert res.status_code == 200
    metrics = res.get_json()["metrics"]
    assert "inside_building" in metrics
    assert "safely_evacuated" in metrics
    assert "missing_or_trapped" in metrics
    assert "total_occupants" in metrics
    assert metrics["total_occupants"] == metrics["inside_building"] + metrics["safely_evacuated"] + metrics["missing_or_trapped"]

