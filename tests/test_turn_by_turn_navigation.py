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
