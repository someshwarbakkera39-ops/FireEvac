"""
Unit & Integration Tests for Real-Time Hazard / Gate Rerouting & Blocked Path Prevention
Verifies:
1. Corridor gates blocked in paths table (is_blocked = 1) immediately reroute Dijkstra.
2. Compromised edges and nodes are returned in /api/route payload for client map rendering.
3. Completely blocked pathways return result.success: False to trigger client-side hazard alert UI.
4. Dynamic canvas QR placement maintains 3-tuple adjacency in graph_model.
"""

import pytest
from app import app, graph_model
from database.db import execute_db, query_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Clean test state
        client.post("/api/hazards/clear")
        execute_db("DELETE FROM qr_codes WHERE code_id NOT IN ('QR_G_ATRIUM','QR_G_ADMIN','QR_G_CLINIC','QR_G_CAFE','QR_G_SECURITY','QR_1_FACULTY','QR_1_CSLAB','QR_1_NETLAB','QR_1_BRIDGE','QR_1_STAIR_A','QR_2_LECTURE','QR_2_SEMINAR','QR_2_BRIDGE','QR_2_STAIR_A','QR_2_STAIR_B','QR_3_LIBRARY','QR_3_AILAB','QR_3_HPC','QR_3_STAIR_A','QR_3_STAIR_B','QR_4_BOARDROOM','QR_4_AUDITORIUM','QR_4_ROOF_EXIT','QR_4_STAIR_A','QR_4_STAIR_B')")
        yield client
        # Tear down
        client.post("/api/hazards/clear")

def test_paths_blocked_gates_reroute(client):
    """Corridor gates set to is_blocked = 1 in database must be excluded from Dijkstra paths."""
    # 1. Baseline route from Floor 3 AI Lab (NODE_ROOM_3_05)
    res_base = client.post("/api/route", json={"start_node": "NODE_ROOM_3_05"})
    assert res_base.status_code == 200
    base_data = res_base.get_json()
    assert base_data["status"] == "success"
    assert base_data["result"]["success"] is True
    base_path = base_data["result"]["path"]

    # Pick a corridor edge in the active path
    edge_u, edge_v = None, None
    for i in range(len(base_path) - 1):
        u, v = base_path[i], base_path[i + 1]
        if "STAIR" not in u and "STAIR" not in v and "EXIT" not in u and "EXIT" not in v:
            edge_u, edge_v = u, v
            break

    if edge_u and edge_v:
        # Block this gate in database
        client.post("/api/paths/toggle-block", json={
            "from_node": edge_u,
            "to_node": edge_v,
            "is_blocked": True
        })

        # Recalculate route
        res_reroute = client.post("/api/route", json={"start_node": "NODE_ROOM_3_05"})
        reroute_data = res_reroute.get_json()

        # Blocked edges should contain [edge_u, edge_v] and [edge_v, edge_u]
        b_edges = reroute_data.get("blocked_edges", [])
        assert [edge_u, edge_v] in b_edges or [edge_v, edge_u] in b_edges

        # The new route must NOT traverse this blocked edge
        if reroute_data["result"]["success"]:
            new_path = reroute_data["result"]["path"]
            for i in range(len(new_path) - 1):
                pair = (new_path[i], new_path[i + 1])
                rev_pair = (new_path[i + 1], new_path[i])
                assert pair != (edge_u, edge_v) and rev_pair != (edge_u, edge_v), \
                    f"Rerouted path still traverses blocked gate {edge_u} <-> {edge_v}"

def test_complete_exit_severance_returns_error(client):
    """When all exit options are blocked by hazards, API must return error status and success: False."""
    # Place fire directly over all 3 ground exits
    exits = [
        {"x": 600, "y": 620},  # Main South Exit
        {"x": 1050, "y": 370}, # East Exit
        {"x": 150, "y": 370}   # West Exit
    ]
    for ex in exits:
        client.post("/api/hazards", json={
            "floor_id": 0,
            "location_x": ex["x"],
            "location_y": ex["y"],
            "type": "fire",
            "radius": 60
        })

    res = client.post("/api/route", json={"start_node": "NODE_ROOM_G_01"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "error"
    assert data["result"]["success"] is False
    assert "hazard" in data["result"]["error"].lower() or "exit" in data["result"]["error"].lower()

def test_dynamic_qr_placement_adjacency_tuples(client):
    """Stationary QR dynamic point placement must register adjacency as 3-tuples (neighbor, weight, type)."""
    # System must be active
    client.post("/api/system/start", json={"emergency_type": "fire_evacuation"})

    test_code = "QR_TEST_TUPLE_CHECK"
    res = client.post("/api/qr", json={
        "code_id": test_code,
        "floor_id": 2,
        "location_label": "Test Dynamic Point",
        "x_coord": 380,
        "y_coord": 200
    })
    assert res.status_code in [200, 201]
    res_data = res.get_json()
    placed_node_id = res_data["qr"]["node_id"]

    # Verify placed node has valid adjacency format
    if placed_node_id in graph_model.adjacency:
        for item in graph_model.adjacency[placed_node_id]:
            assert isinstance(item, tuple), f"Adjacency item {item} should be a tuple, not a dict"
            assert len(item) == 3, f"Adjacency tuple {item} must have 3 elements (neighbor, weight, edge_type)"

    # Verify calculate_route runs from this new QR node
    res_route = client.post("/api/route", json={"start_node": placed_node_id})
    assert res_route.status_code == 200
    route_json = res_route.get_json()
    assert route_json["result"]["success"] is True
