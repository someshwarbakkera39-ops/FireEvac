"""
Automated Test Suite for Phase 5: Public User Panel, QR Indoor Localization & Outdoor GPS Integration
Validates zero-login mobile web client, QR-driven route calculation, emergency SOS dispatch, and GPS distance math.
"""

import math
import pytest
from app import app
from database.db import query_db, execute_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_public_user_panel_zero_login_access(client):
    """Test zero-login access to public evacuation guidance web client."""
    # Test /public
    res_pub = client.get("/public")
    assert res_pub.status_code == 200
    assert b"Emergency Evacuation Guidance" in res_pub.data
    assert b"SOS ALERT" in res_pub.data
    assert b"Scan Floor QR" in res_pub.data

    # Test /sos alias
    res_sos = client.get("/sos")
    assert res_sos.status_code == 200
    assert b"BLOCK A DIGITAL TWIN" in res_sos.data

def test_qr_checkpoint_to_evacuation_routing(client):
    """Test complete flow: scan stationary QR code -> resolve node -> compute dynamic route."""
    # 1. Resolve QR code for AI Lab 305
    res_qr = client.get("/api/qr/QR_3_AILAB")
    assert res_qr.status_code == 200
    qr_data = res_qr.get_json()
    resolved_node = qr_data["node_id"]
    assert resolved_node == "NODE_ROOM_3_05"
    assert qr_data["floor"] == 3

    # 2. Immediately request evacuation route from this resolved node
    res_route = client.post("/api/route", json={"start_node": resolved_node})
    assert res_route.status_code == 200
    route_data = res_route.get_json()["result"]
    assert route_data["success"] is True
    assert route_data["start_node"] == "NODE_ROOM_3_05"
    assert len(route_data["instructions"]) >= 3
    assert route_data["distance_meters"] > 0

def test_emergency_sos_dispatch_reporting(client):
    """Test 1-tap emergency SOS dispatch logging occupant into database."""
    res_sos = client.post("/api/occupancy/report", json={
        "occupant_id": "STUDENT_MOBILE_SOS_01",
        "current_node": "NODE_ROOM_3_05",
        "floor_id": 3,
        "status": "inside"
    })
    assert res_sos.status_code == 200
    assert res_sos.get_json()["status"] == "success"

    # Verify occupant in SQLite
    rec = query_db("SELECT * FROM occupancy_sim WHERE occupant_id = 'STUDENT_MOBILE_SOS_01'", one=True)
    assert rec is not None
    assert rec["current_node"] == "NODE_ROOM_3_05"
    assert rec["floor_id"] == 3

    # Clean up test record
    execute_db("DELETE FROM occupancy_sim WHERE occupant_id = 'STUDENT_MOBILE_SOS_01'")

def test_haversine_outdoor_gps_math():
    """Verify physical GPS distance and bearing calculation to outdoor muster grounds."""
    # Mock user GPS outside South Entrance: lat = 12.9712, lng = 77.5944
    u_lat, u_lng = 12.9712, 77.5944
    # Assembly Point 1 (South Lawn): lat = 12.9716, lng = 77.5946
    s_lat, s_lng = 12.9716, 77.5946

    # Haversine distance
    R = 6371000 # meters
    dLat = math.radians(s_lat - u_lat)
    dLon = math.radians(s_lng - u_lng)
    a = (math.sin(dLat / 2) ** 2 +
         math.cos(math.radians(u_lat)) * math.cos(math.radians(s_lat)) * math.sin(dLon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist = round(R * c)

    # South lawn is ~45-55 meters away from the building threshold
    assert 30 <= dist <= 80, f"Expected realistic walking distance ~45m, got {dist}m"

    # Bearing check
    y = math.sin(dLon) * math.cos(math.radians(s_lat))
    x = (math.cos(math.radians(u_lat)) * math.sin(math.radians(s_lat)) -
         math.sin(math.radians(u_lat)) * math.cos(math.radians(s_lat)) * math.cos(dLon))
    bearing = round((math.degrees(math.atan2(y, x)) + 360) % 360)
    assert 0 <= bearing <= 90, f"Expected North-East bearing towards lawn, got {bearing}°"

def test_safe_evacuation_acknowledgment(client):
    """Test occupant clicking 'I Have Safely Evacuated' marking status as safe."""
    res_safe = client.post("/api/occupancy/report", json={
        "occupant_id": "EVACUATED_USER_99",
        "status": "safe",
        "floor_id": 0,
        "current_node": "NODE_ASSEMBLY_SOUTH",
        "safe_exit": "NODE_EXIT_G_MAIN"
    })
    assert res_safe.status_code == 200

    rec = query_db("SELECT status, safe_exit FROM occupancy_sim WHERE occupant_id = 'EVACUATED_USER_99'", one=True)
    assert rec["status"] == "safe"
    assert rec["safe_exit"] == "NODE_EXIT_G_MAIN"

    # Clean up
    execute_db("DELETE FROM occupancy_sim WHERE occupant_id = 'EVACUATED_USER_99'")

