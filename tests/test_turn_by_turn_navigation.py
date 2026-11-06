"""
Tests for Turn-by-Turn Directional Navigation (Front, Back, Left, Right, Descend, Exit)
and Nearest QR Checkpoint Localization
"""

import pytest
from app import app
from database.db import init_db
from database.seed_data import seed_all

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    seed_all()
    yield

def test_directional_navigation_maneuvers():
    """Verify that route instructions contain directional maneuvers and icons."""
    client = app.test_client()

    # Calculate evacuation route from AI Lab on Floor 3
    res = client.post("/api/route", json={"start_node": "NODE_ROOM_3_05"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    result = data["result"]
    assert result["success"] is True

    instructions = result["instructions"]
    assert len(instructions) >= 3

    # Check for presence of directional maneuvers
    maneuvers = [instr.get("maneuver") for instr in instructions]
    icons = [instr.get("icon") for instr in instructions]

    # Verify stair descent maneuver is present
    assert "descend" in maneuvers
    assert "🔽" in icons

    # Verify corridor entry or turn maneuver is present
    assert any(m in ["straight", "left", "right", "uturn"] for m in maneuvers)
    assert any(icon in ["⬆️", "⬅️", "➡️", "⬇️"] for icon in icons)

    # Verify exit portal is present
    assert "exit" in maneuvers
    assert "🚪" in icons

    # Verify segment distances are positive numbers
    for instr in instructions:
        assert "distance_meters" in instr
        assert instr["distance_meters"] >= 0

def test_nearest_qr_data_availability():
    """Verify that all QR checkpoints return coordinates and metadata for proximity calculation."""
    client = app.test_client()

    res = client.get("/api/qr")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["total"] >= 25

    for qr in data["qr_codes"]:
        assert "code_id" in qr
        assert "node_id" in qr
        assert "floor_id" in qr
        assert "x_coord" in qr
        assert "y_coord" in qr
        assert qr["x_coord"] > 0
        assert qr["y_coord"] > 0

def test_emergency_system_activation_and_standby():
    """Verify emergency system activation, QR arming, and standby transitions."""
    client = app.test_client()

    # 1. Start system and activate all QRs
    res_start = client.post("/api/system/start", json={"emergency_type": "fire_evacuation"})
    assert res_start.status_code == 200
    data_start = res_start.get_json()
    assert data_start["status"] == "success"
    assert data_start["system"]["is_active"] is True
    assert data_start["system"]["qr_codes_activated"] is True

    # 2. Check system status
    res_status = client.get("/api/system/status")
    assert res_status.status_code == 200
    data_status = res_status.get_json()
    assert data_status["system"]["is_active"] is True
    assert data_status["system"]["status"] == "active"

    # 3. Put system into standby mode
    res_standby = client.post("/api/system/standby")
    assert res_standby.status_code == 200
    data_standby = res_standby.get_json()
    assert data_standby["status"] == "success"
    assert data_standby["system"]["is_active"] is False
    assert data_standby["system"]["qr_codes_activated"] is False

    # 4. Re-activate system
    res_reactivate = client.post("/api/system/start")
    assert res_reactivate.status_code == 200
    assert res_reactivate.get_json()["system"]["is_active"] is True


