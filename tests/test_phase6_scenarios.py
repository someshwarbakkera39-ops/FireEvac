"""
Phase 6 Automated Scenario Demonstration & End-to-End Integration Suite
Validates all 5 Mandatory Blueprint Scenarios (Section 13) and Production Configuration.
"""

import time
import os
import pytest
from app import app
from database.db import query_db, execute_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_mandatory_scenario_1_baseline_evacuation(client):
    """
    Mandatory Scenario 1: Standard Baseline Evacuation
    Conditions: Normal operational conditions, zero hazards.
    Target: Shortest path from Floor 4 Grand Auditorium to nearest ground exit.
    """
    client.post("/api/hazards/clear")

    t_start = time.perf_counter()
    res = client.post("/api/route", json={"start_node": "NODE_ROOM_4_06"})
    elapsed_ms = (time.perf_counter() - t_start) * 1000

    assert res.status_code == 200
    route = res.get_json()["result"]
    assert route["success"] is True
    assert route["alternate_route_applied"] is False
    assert route["target_exit"] in ["NODE_EXIT_G_MAIN", "NODE_EXIT_G_EAST", "NODE_EXIT_G_WEST"]
    assert 4 in route["floors_traversed"] and 0 in route["floors_traversed"]
    assert elapsed_ms < 25.0, f"Dijkstra latency should be < 25ms, took {elapsed_ms:.2f}ms"

def test_mandatory_scenario_2_ground_floor_exit_blockage(client):
    """
    Mandatory Scenario 2: Ground Floor Incident
    Conditions: Primary ground floor exit (Exit 1 Main South) blocked.
    Target: System dynamically redirects occupants to alternate secondary exit.
    """
    client.post("/api/hazards/clear")

    # Deploy hazard directly at Exit 1
    client.post("/api/hazards", json={
        "floor_id": 0,
        "location_x": 600,
        "location_y": 620,
        "type": "fire",
        "radius": 55
    })

    # Evacuate from Admin Office G-101
    res = client.post("/api/route", json={"start_node": "NODE_ROOM_G_01"})
    assert res.status_code == 200
    route = res.get_json()["result"]
    assert route["success"] is True
    assert route["target_exit"] != "NODE_EXIT_G_MAIN"
    assert route["target_exit"] in ["NODE_EXIT_G_WEST", "NODE_EXIT_G_EAST"]
    assert route["alternate_route_applied"] is True

    client.post("/api/hazards/clear")

def test_mandatory_scenario_3_vertical_staircase_b_engulfed(client):
    """
    Mandatory Scenario 3: Vertical Corridor Blockage
    Conditions: Staircase B engulfed on Floor 2.
    Target: Upper East occupants (e.g. AI Lab Floor 3) seamlessly rerouted to Staircase A across Central Spine.
    """
    client.post("/api/hazards/clear")

    # Engulf Staircase B landing on Floor 2
    client.post("/api/hazards", json={
        "floor_id": 2,
        "location_x": 1030,
        "location_y": 175,
        "type": "fire",
        "radius": 60
    })

    res = client.post("/api/route", json={"start_node": "NODE_ROOM_3_05"})
    assert res.status_code == 200
    route = res.get_json()["result"]
    assert route["success"] is True
    assert "STAIR_B_2" not in route["path"]
    assert "Staircase A (West Wing)" in route["stairwells_used"]
    assert route["alternate_route_applied"] is True

    client.post("/api/hazards/clear")

def test_mandatory_scenario_4_live_in_transit_rerouting(client):
    """
    Mandatory Scenario 4: Live In-Transit Rerouting
    Conditions: An occupant is navigating corridor N1_W_MID_N; hazard suddenly blocks path.
    Target: System dynamically updates route in real time.
    """
    client.post("/api/hazards/clear")

    # Step 1: Occupant starts in Room 101, normal route
    res1 = client.post("/api/route", json={"start_node": "NODE_ROOM_1_01"})
    path1 = res1.get_json()["result"]["path"]

    # Step 2: West North corridor is suddenly blocked by falling debris
    client.post("/api/paths/toggle-block", json={
        "from_node": "N1_W_NORTH",
        "to_node": "N1_W_MID_N",
        "is_blocked": True
    })

    # Step 3: Occupant recalculates while in transit
    res2 = client.post("/api/route", json={"start_node": "NODE_ROOM_1_01"})
    path2 = res2.get_json()["result"]["path"]

    assert path1 != path2
    assert ("N1_W_NORTH", "N1_W_MID_N") not in list(zip(path2[:-1], path2[1:]))

    # Clean up
    client.post("/api/paths/toggle-block", json={
        "from_node": "N1_W_NORTH",
        "to_node": "N1_W_MID_N",
        "is_blocked": False
    })
    client.post("/api/hazards/clear")

def test_mandatory_scenario_5_multi_hazard_compound(client):
    """
    Mandatory Scenario 5: Multi-Hazard Complex Scenario
    Conditions: Multiple corridors and Staircase A concurrently blocked.
    Target: Algorithm validates secondary safe egress route.
    """
    client.post("/api/hazards/clear")

    # Fire 1: Staircase A blocked on Floor 1
    client.post("/api/hazards", json={"floor_id": 1, "location_x": 170, "location_y": 175, "type": "fire", "radius": 60})
    # Fire 2: Ground Floor West Exit blocked
    client.post("/api/hazards", json={"floor_id": 0, "location_x": 100, "location_y": 370, "type": "fire", "radius": 50})

    # Evacuate from 3rd floor Library (West Wing)
    res = client.post("/api/route", json={"start_node": "NODE_ROOM_3_01"})
    assert res.status_code == 200
    route = res.get_json()["result"]
    assert route["success"] is True
    # Must use Staircase B and reach Ground Exit 1 or 3
    assert "STAIR_A_1" not in route["path"]
    assert "NODE_EXIT_G_WEST" not in route["path"]

    client.post("/api/hazards/clear")

def test_production_deployment_and_testkit_assets():
    """Verify production cloud deployment configuration and physical QR test kit."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Verify WSGI entrypoint and cloud deployment files
    assert os.path.exists(os.path.join(base_dir, "wsgi.py"))
    assert os.path.exists(os.path.join(base_dir, "vercel.json")) or os.path.exists(os.path.join(base_dir, "Procfile"))
    assert os.path.exists(os.path.join(base_dir, "config.py"))

    # Verify generated physical QR testing kit HTML
    qr_testkit_path = os.path.join(base_dir, "static", "qr_testkit.html")
    assert os.path.exists(qr_testkit_path)
    with open(qr_testkit_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "QR_3_AILAB" in content
        assert "QR_4_AUDITORIUM" in content
        assert "QR_G_ATRIUM" in content

