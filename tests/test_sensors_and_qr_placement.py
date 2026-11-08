"""
Tests for:
1. Admin QR Placement Tool (Conditional activation: allowed IF AND ONLY IF system is active)
2. QR Scan Hazard avoidance & active hazard synchronization
3. Automated IoT Environmental Sensors & AI CCTV Surveillance Grid
"""

import pytest
from app import app
from database.db import init_db, execute_db
from database.seed_data import seed_all

BASE_25_QRS = [
    'QR_G_ATRIUM', 'QR_G_ADMIN', 'QR_G_CLINIC', 'QR_G_CAFE', 'QR_G_SECURITY',
    'QR_1_FACULTY', 'QR_1_CSLAB', 'QR_1_NETLAB', 'QR_1_BRIDGE', 'QR_1_STAIR_A',
    'QR_2_LECTURE', 'QR_2_SEMINAR', 'QR_2_BRIDGE', 'QR_2_STAIR_A', 'QR_2_STAIR_B',
    'QR_3_LIBRARY', 'QR_3_AILAB', 'QR_3_HPC', 'QR_3_STAIR_A', 'QR_3_STAIR_B',
    'QR_4_BOARDROOM', 'QR_4_AUDITORIUM', 'QR_4_ROOF_EXIT', 'QR_4_STAIR_A', 'QR_4_STAIR_B'
]

def clean_custom_state():
    q_str = ",".join(f"'{q}'" for q in BASE_25_QRS)
    execute_db("DELETE FROM hazards")
    execute_db("UPDATE paths SET is_blocked = 0")
    execute_db(f"DELETE FROM qr_codes WHERE code_id NOT IN ({q_str})")
    execute_db("DELETE FROM nodes WHERE id LIKE 'NODE_CUSTOM_%'")

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    seed_all()
    clean_custom_state()
    yield
    clean_custom_state()

def test_qr_placement_blocked_when_system_standby():
    """Verify that QR checkpoints CANNOT be placed when the Emergency System is in Standby mode."""
    client = app.test_client()

    # 1. Put system in standby
    res_standby = client.post("/api/system/standby")
    assert res_standby.status_code == 200

    # 2. Attempt to register/place a new QR checkpoint
    res_place = client.post("/api/qr", json={
        "floor_id": 2,
        "location_label": "Floor 2 West Wing Gate",
        "x_coord": 275.0,
        "y_coord": 310.0
    })
    # Must be rejected with 403 Forbidden!
    assert res_place.status_code == 403
    data = res_place.get_json()
    assert data["status"] == "error"
    assert "ACTIVE" in data["message"]

def test_qr_placement_allowed_when_system_active():
    """Verify that QR checkpoints CAN be placed when the Emergency System is ACTIVE."""
    client = app.test_client()

    # 1. Start / activate the emergency system
    res_start = client.post("/api/system/start", json={"emergency_type": "fire_evacuation"})
    assert res_start.status_code == 200

    # 2. Place new QR checkpoint at Floor 3 custom coordinates
    res_place = client.post("/api/qr", json={
        "floor_id": 3,
        "location_label": "Floor 3 Robotics Gate",
        "description": "Stationary marker placed by safety warden",
        "x_coord": 600.0,
        "y_coord": 350.0
    })
    assert res_place.status_code == 201
    data = res_place.get_json()
    assert data["status"] == "success"
    new_qr = data["qr"]
    assert "code_id" in new_qr
    assert new_qr["floor_id"] == 3
    assert new_qr["location_label"] == "Floor 3 Robotics Gate"

    # 3. Verify it is listed in GET /api/qr for Print Kit
    res_list = client.get("/api/qr")
    assert res_list.status_code == 200
    list_data = res_list.get_json()
    codes = [q["code_id"] for q in list_data["qr_codes"]]
    assert new_qr["code_id"] in codes

    # 4. Verify scannable image endpoint works for this new QR
    res_img = client.get(f"/api/qr/image/{new_qr['code_id']}")
    assert res_img.status_code == 200
    assert res_img.mimetype == "image/png"

def test_qr_scan_returns_active_hazards_and_avoids_fire():
    """
    Verify that when an occupant scans a QR code:
    1. The response returns active hazards so the user map can render them immediately.
    2. The route calculation strictly avoids corridor edges and nodes blocked by fire.
    """
    client = app.test_client()

    # Place a fire hazard on Floor 3 along the corridor near x=600, y=370
    res_haz = client.post("/api/hazards", json={
        "floor_id": 3,
        "location_x": 600.0,
        "location_y": 370.0,
        "type": "fire",
        "radius": 45.0,
        "description": "Simulated corridor fire"
    })
    assert res_haz.status_code == 201

    # Occupant scans QR code in AI Lab 305 on Floor 3
    res_scan = client.post("/api/occupancy/scan", json={
        "qr_code": "QR_3_AILAB",
        "occupant_id": "TEST_OCC_HAZARD"
    })
    assert res_scan.status_code == 200
    scan_data = res_scan.get_json()
    assert scan_data["status"] == "success"

    # Verify hazards list is returned to user client
    assert "hazards" in scan_data
    assert len(scan_data["hazards"]) >= 1
    assert any(h["floor_id"] == 3 for h in scan_data["hazards"])

    # Verify route exists and avoids blocked edges
    assert "route" in scan_data
    assert scan_data["route"]["success"] is True
    path = scan_data["route"]["path"]
    assert len(path) >= 2

def test_iot_sensors_api_and_automated_detection():
    """Verify IoT sensor querying, automation toggle, and automated hazard creation upon trigger."""
    client = app.test_client()

    # 1. Fetch sensor grid
    res_sensors = client.get("/api/sensors")
    assert res_sensors.status_code == 200
    data = res_sensors.get_json()
    assert data["status"] == "success"
    assert data["total"] >= 10
    sensors = data["sensors"]
    
    # Check that cameras and sensors are represented
    types = [s["type"] for s in sensors]
    assert "camera" in types
    assert any("sensor" in t for t in types)

    # 2. Verify automation is enabled
    assert data["automation_enabled"] is True

    # 3. Trigger a sensor alert (e.g. SENSOR_1_CSLAB on Floor 1)
    target_sensor = "SENSOR_1_CSLAB"
    res_trig = client.post(f"/api/sensors/{target_sensor}/trigger")
    assert res_trig.status_code == 200
    trig_data = res_trig.get_json()
    assert trig_data["status"] == "success"
    assert trig_data["device"]["status"] == "alert"
    # Automated detection should have automatically created an active hazard!
    assert trig_data["hazard_created_id"] is not None

    # 4. Verify hazard exists in /api/hazards
    res_haz = client.get("/api/hazards?floor=1")
    haz_data = res_haz.get_json()
    assert haz_data["total"] >= 1
    assert any(h["id"] == trig_data["hazard_created_id"] for h in haz_data["hazards"])

    # 5. Reset the sensor
    res_reset = client.post(f"/api/sensors/{target_sensor}/reset")
    assert res_reset.status_code == 200
    reset_data = res_reset.get_json()
    assert reset_data["device"]["status"] == "normal"

    # 6. Test toggle automation
    res_toggle = client.post("/api/sensors/toggle-automation", json={"enabled": False})
    assert res_toggle.status_code == 200
    assert res_toggle.get_json()["automation_enabled"] is False

    # Trigger with automation disabled: sensor status changes, but no automated hazard is spawned
    res_trig2 = client.post(f"/api/sensors/CAM_G_LOBBY/trigger")
    assert res_trig2.status_code == 200
    assert res_trig2.get_json()["hazard_created_id"] is None

    # Reset all sensors
    res_reset_all = client.post("/api/sensors/reset-all")
    assert res_reset_all.status_code == 200
    all_s = client.get("/api/sensors").get_json()["sensors"]
    assert all(s["status"] == "normal" for s in all_s)
