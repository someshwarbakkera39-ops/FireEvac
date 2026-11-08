"""
Tests for Camera-Scannable QR Generation, Real-Time Occupant Counting,
and Live Evacuation Drill Simulation APIs
"""

import pytest
import os
import json
from app import app
from database.db import init_db, execute_db
from database.seed_data import seed_all

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    seed_all()
    execute_db("DELETE FROM qr_codes WHERE code_id NOT IN ("
               "'QR_G_ATRIUM', 'QR_G_ADMIN', 'QR_G_CLINIC', 'QR_G_CAFE', 'QR_G_SECURITY', "
               "'QR_1_FACULTY', 'QR_1_CSLAB', 'QR_1_NETLAB', 'QR_1_BRIDGE', 'QR_1_STAIR_A', "
               "'QR_2_LECTURE', 'QR_2_SEMINAR', 'QR_2_BRIDGE', 'QR_2_STAIR_A', 'QR_2_STAIR_B', "
               "'QR_3_LIBRARY', 'QR_3_AILAB', 'QR_3_HPC', 'QR_3_STAIR_A', 'QR_3_STAIR_B', "
               "'QR_4_BOARDROOM', 'QR_4_AUDITORIUM', 'QR_4_ROOF_EXIT', 'QR_4_STAIR_A', 'QR_4_STAIR_B')")
    yield

def test_qr_image_generation_png_and_svg():
    client = app.test_client()

    # 1. Test PNG format
    res_png = client.get("/api/qr/image/QR_3_AILAB")
    assert res_png.status_code == 200
    assert res_png.content_type == "image/png"
    assert len(res_png.data) > 500  # Valid PNG image bytes

    # 2. Test SVG format
    res_svg = client.get("/api/qr/image/QR_3_AILAB?format=svg")
    assert res_svg.status_code == 200
    assert "svg" in res_svg.content_type
    assert b"<svg" in res_svg.data

    # 3. Test non-existent QR
    res_404 = client.get("/api/qr/image/NON_EXISTENT_QR")
    assert res_404.status_code == 404

def test_qr_scan_localization_and_routing():
    client = app.test_client()

    scan_payload = {
        "qr_code": "QR_3_AILAB",
        "occupant_id": "TEST_PHONE_USER_01"
    }
    res = client.post("/api/occupancy/scan", json=scan_payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["occupant_id"] == "TEST_PHONE_USER_01"

    # Location resolution
    loc = data["location"]
    assert loc["floor"] == 3
    assert loc["node_id"] == "NODE_ROOM_3_05"
    assert "AI &" in loc["label"] or "305" in loc["room_code"]

    # Evacuation route
    route = data["route"]
    assert route["success"] is True
    assert len(route["path"]) > 1
    assert "target_exit_name" in route
    assert route["distance_meters"] > 0

    # Metrics
    metrics = data["metrics"]
    assert metrics["inside_building"] >= 1
    assert metrics["total_scanned"] >= 1

def test_occupancy_real_time_tracking_counters():
    client = app.test_client()

    # Fetch initial metrics
    initial_res = client.get("/api/occupancy")
    assert initial_res.status_code == 200
    initial_metrics = initial_res.get_json()["metrics"]
    init_inside = initial_metrics["inside_building"]
    init_safe = initial_metrics["safely_evacuated"]
    init_scanned = initial_metrics["total_scanned"]

    # 1. New user scans QR at Floor 4 Auditorium
    user_id = "TRACKING_USER_999"
    scan_res = client.post("/api/occupancy/scan", json={
        "qr_code": "QR_4_AUDITORIUM",
        "occupant_id": user_id
    })
    assert scan_res.status_code == 200
    after_scan = scan_res.get_json()["metrics"]

    assert after_scan["inside_building"] == init_inside + 1
    assert after_scan["total_scanned"] == init_scanned + 1

    # 2. User marks "Safely Evacuated"
    safe_res = client.post("/api/occupancy/report", json={
        "occupant_id": user_id,
        "status": "safe",
        "floor_id": 0,
        "safe_exit": "NODE_EXIT_G_MAIN"
    })
    assert safe_res.status_code == 200
    after_safe = safe_res.get_json()["metrics"]

    # Verification: inside decremented, safe incremented
    assert after_safe["inside_building"] == after_scan["inside_building"] - 1
    assert after_safe["safely_evacuated"] == init_safe + 1

def test_drill_simulation_population_and_crowd_scaling():
    client = app.test_client()

    pop_res = client.post("/api/simulation/populate", json={"count": 25})
    assert pop_res.status_code == 200
    pop_data = pop_res.get_json()
    assert pop_data["status"] == "success"
    assert pop_data["metrics"]["total_occupants"] == 25
    assert pop_data["metrics"]["inside_building"] == 25

    # Check floor breakdown
    occ_res = client.get("/api/occupancy")
    by_floor = occ_res.get_json()["by_floor"]
    total_on_floors = sum(by_floor.values())
    assert total_on_floors == 25

def test_qr_testkit_and_png_badge_assets():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    testkit_html = os.path.join(base_dir, "static", "qr_testkit.html")
    assert os.path.exists(testkit_html)
    assert os.path.getsize(testkit_html) > 1000

    qr_codes_dir = os.path.join(base_dir, "static", "qr_codes")
    assert os.path.exists(qr_codes_dir)
    png_files = [f for f in os.listdir(qr_codes_dir) if f.endswith(".png")]
    assert len(png_files) >= 15
    for pf in png_files:
        assert os.path.getsize(os.path.join(qr_codes_dir, pf)) > 200

def test_25_qr_checkpoints_and_commander_location():
    client = app.test_client()

    # 1. Verify 25 stationary QR checkpoints across Floors 0-4
    qr_res = client.get("/api/qr")
    assert qr_res.status_code == 200
    qr_data = qr_res.get_json()
    assert qr_data["status"] == "success"
    qr_codes = qr_data["qr_codes"]
    assert len(qr_codes) == 25

    # Check 5 checkpoints per floor
    floors = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for q in qr_codes:
        fl = q["floor_id"]
        assert fl in floors
        floors[fl] += 1
    for fl, count in floors.items():
        assert count == 5, f"Floor {fl} has {count} checkpoints instead of 5"

    # 2. Verify Incident Commander location endpoint
    cmd_res = client.get("/api/commander/location")
    assert cmd_res.status_code == 200
    cmd_data = cmd_res.get_json()
    assert cmd_data["status"] == "success"
    assert "node_id" in cmd_data["commander"]
    assert "Security" in cmd_data["commander"]["location_label"] or "G-103" in cmd_data["commander"]["location_label"]


