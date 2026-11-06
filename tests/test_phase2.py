"""
Automated Test Suite for Phase 2: Spatial Graph Modeling & Dynamic Dijkstra Routing Engine
Validates multi-floor graph construction, edge exclusions, and hazard scenarios.
"""

import pytest
from engine.graph_model import BlockAGraphModel
from engine.dijkstra import DijkstraRoutingEngine

@pytest.fixture
def graph():
    return BlockAGraphModel()

@pytest.fixture
def engine(graph):
    return DijkstraRoutingEngine(graph)

def test_graph_initialization(graph):
    """Verify that graph vertices and edges are constructed across all 5 floors."""
    assert len(graph.nodes) >= 60, f"Expected at least 60 nodes, got {len(graph.nodes)}"
    assert len(graph.edges) >= 70, f"Expected at least 70 edges, got {len(graph.edges)}"

    # Check each floor has nodes
    for fl in range(5):
        floor_nodes = [n for n in graph.nodes.values() if n["floor"] == fl]
        assert len(floor_nodes) >= 10, f"Floor {fl} has insufficient nodes: {len(floor_nodes)}"
        
        # Check staircase nodes on each floor
        assert f"STAIR_A_{fl}" in graph.nodes
        assert f"STAIR_B_{fl}" in graph.nodes

    # Check Ground floor exits
    assert "NODE_EXIT_G_MAIN" in graph.nodes
    assert "NODE_EXIT_G_WEST" in graph.nodes
    assert "NODE_EXIT_G_EAST" in graph.nodes
    assert "NODE_ASSEMBLY_SOUTH" in graph.nodes
    assert "NODE_ASSEMBLY_NORTH" in graph.nodes

def test_scenario_1_baseline_evacuation(engine):
    """Scenario 1: Normal conditions, shortest path from 4th floor to nearest ground exit."""
    # Start at 4th floor Executive Boardroom
    res = engine.calculate_evacuation_route("NODE_ROOM_4_01")
    assert res["success"] is True
    assert res["target_exit"] in ["NODE_EXIT_G_MAIN", "NODE_EXIT_G_WEST", "NODE_EXIT_G_EAST"]
    assert res["distance_meters"] > 0
    assert res["estimated_time_seconds"] > 0
    assert 4 in res["floors_traversed"] and 0 in res["floors_traversed"]
    assert len(res["instructions"]) >= 3

def test_scenario_2_ground_exit_blockage(engine):
    """Scenario 2: Primary Ground Exit is blocked by fire; system redirects to secondary exits."""
    # Normal route from Room G-101
    baseline = engine.calculate_evacuation_route("NODE_ROOM_G_01")
    assert baseline["success"] is True

    # Block Primary South Exit
    res = engine.calculate_evacuation_route(
        "NODE_ROOM_G_01",
        blocked_nodes=["NODE_EXIT_G_MAIN"]
    )
    assert res["success"] is True
    assert res["target_exit"] != "NODE_EXIT_G_MAIN"
    assert res["target_exit"] in ["NODE_EXIT_G_WEST", "NODE_EXIT_G_EAST"]
    assert res["alternate_route_applied"] is True

def test_scenario_3_staircase_b_blockage_reroute(engine):
    """Scenario 3: Staircase B engulfed on Floor 2; East wing occupants rerouted to Staircase A."""
    # From 3rd floor AI Lab (East Wing, normally prefers Staircase B)
    baseline = engine.calculate_evacuation_route("NODE_ROOM_3_05")
    assert baseline["success"] is True
    assert "Staircase B (East Wing)" in baseline["stairwells_used"]

    # Now simulate fire engulfing Staircase B on Floor 2
    reroute = engine.calculate_evacuation_route(
        "NODE_ROOM_3_05",
        blocked_nodes=["STAIR_B_2", "STAIR_B_1"]
    )
    assert reroute["success"] is True
    # System MUST reroute through Staircase A across the central bridge!
    assert "Staircase A (West Wing)" in reroute["stairwells_used"]
    assert "STAIR_B_2" not in reroute["path"]
    assert reroute["alternate_route_applied"] is True

def test_scenario_4_corridor_edge_exclusion(engine):
    """Scenario 4: Specific corridor segment blocked; path circumvents the obstruction."""
    # Corridor between West Center and Central Bridge West is blocked on Floor 1
    blocked_corridor = [("N1_W_CENTER", "N1_C_WEST")]
    res = engine.calculate_evacuation_route(
        "NODE_ROOM_1_01",
        blocked_edges=blocked_corridor
    )
    assert res["success"] is True
    for i in range(len(res["path"]) - 1):
        edge = (res["path"][i], res["path"][i+1])
        assert edge != ("N1_W_CENTER", "N1_C_WEST")
        assert edge != ("N1_C_WEST", "N1_W_CENTER")

def test_scenario_5_complex_multi_hazard(engine):
    """Scenario 5: Multiple corridors and an entire staircase blocked concurrently."""
    blocked_nodes = ["STAIR_A_1", "NODE_EXIT_G_WEST"]
    blocked_edges = [("N2_W_CENTER", "N2_C_WEST")]

    res = engine.calculate_evacuation_route(
        "NODE_ROOM_3_01",  # Library West Wing Floor 3
        blocked_nodes=blocked_nodes,
        blocked_edges=blocked_edges
    )
    assert res["success"] is True
    assert "STAIR_A_1" not in res["path"]
    assert "NODE_EXIT_G_WEST" not in res["path"]

def test_turn_by_turn_instructions(engine):
    """Verify that clear step-by-step human directives are generated."""
    res = engine.calculate_evacuation_route("NODE_ROOM_3_05")
    assert len(res["instructions"]) >= 4
    first_step = res["instructions"][0]
    assert first_step["step"] == 1
    assert "Evacuation Initiated" in first_step["title"]
    
    # Check that at least one stair instruction is present
    stair_steps = [s for s in res["instructions"] if s["type"] == "stair_descent"]
    assert len(stair_steps) >= 1
    assert "Staircase" in stair_steps[0]["title"]

