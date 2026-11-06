import os
import json
import pytest
from app import app, load_building_data

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_building_model_structure():
    """Verify Block A architectural data integrity across all 5 floors."""
    data = load_building_data()
    assert "building" in data
    assert "floors" in data
    assert "corridor_network" in data

    building = data["building"]
    assert building["floors_count"] == 5
    assert set(building["floor_indices"]) == {0, 1, 2, 3, 4}

    # Verify stairwells alignment
    stairwells = building["stairwells"]
    assert len(stairwells) == 2
    stair_a = next(s for s in stairwells if s["id"] == "STAIR_A")
    stair_b = next(s for s in stairwells if s["id"] == "STAIR_B")

    assert stair_a["center_node"] == {"x": 170, "y": 175}
    assert stair_b["center_node"] == {"x": 1030, "y": 175}
    assert stair_a["serves_floors"] == [0, 1, 2, 3, 4]
    assert stair_b["serves_floors"] == [0, 1, 2, 3, 4]

    # Verify each floor has rooms and valid geometry
    floors = data["floors"]
    for fl_idx in range(5):
        fl_key = str(fl_idx)
        assert fl_key in floors, f"Floor {fl_key} missing from building model"
        fl_data = floors[fl_key]
        assert fl_data["level"] == fl_idx
        assert len(fl_data["rooms"]) > 0, f"Floor {fl_idx} has no rooms"
        
        for r in fl_data["rooms"]:
            assert "id" in r and "name" in r and "code" in r
            assert r["x"] > 0 and r["y"] > 0 and r["width"] > 0 and r["height"] > 0
            assert "door" in r and "x" in r["door"] and "y" in r["door"]

    # Verify Ground floor exits
    ground_exits = floors["0"]["exits"]
    assert len(ground_exits) == 3
    exit_ids = {e["id"] for e in ground_exits}
    assert "EXIT_G_MAIN" in exit_ids
    assert "EXIT_G_WEST" in exit_ids
    assert "EXIT_G_EAST" in exit_ids

def test_api_endpoints(client):
    """Test REST API responses for building, floor, and corridor data."""
    # Test index page
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert b"Block A Facility Evacuation Digital Twin" in res_index.data

    # Test /api/building
    res_building = client.get("/api/building")
    assert res_building.status_code == 200
    data_b = res_building.get_json()
    assert data_b["status"] == "success"
    assert data_b["total_floors"] == 5

    # Test each floor endpoint
    for f in range(5):
        res_fl = client.get(f"/api/floors/{f}")
        assert res_fl.status_code == 200
        data_fl = res_fl.get_json()
        assert data_fl["status"] == "success"
        assert data_fl["floor"]["level"] == f

    # Test corridors endpoint
    res_corr = client.get("/api/corridors")
    assert res_corr.status_code == 200
    data_c = res_corr.get_json()
    assert data_c["status"] == "success"
    assert len(data_c["corridors"]) >= 5

if __name__ == "__main__":
    pytest.main(["-v", __file__])

