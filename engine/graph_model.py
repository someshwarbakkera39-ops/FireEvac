"""
Spatial Graph Model for Block A Facility (G+4 Floors)
Constructs mathematical coordinate graph G = (V, E)
Includes nodes, corridor edges, room door connectors, and vertical stairwell links.
"""

import math
import json
import os

class BlockAGraphModel:
    def __init__(self, building_data_path=None):
        if building_data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            building_data_path = os.path.join(base_dir, "static", "data", "building_model.json")
        
        self.building_data_path = building_data_path
        self.nodes = {}  # node_id -> {id, name, floor, x, y, type, code, metadata}
        self.edges = []  # list of {from, to, weight, type, bidirectional}
        self.adjacency = {}  # node_id -> list of (neighbor_id, weight, edge_type)
        
        self.load_and_build_graph()

    def add_node(self, node_id, name, floor, x, y, node_type="corridor", code=None, metadata=None):
        self.nodes[node_id] = {
            "id": node_id,
            "name": name,
            "floor": floor,
            "x": x,
            "y": y,
            "type": node_type,  # corridor, room, stair, exit, assembly
            "code": code or node_id,
            "metadata": metadata or {}
        }
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []

    def add_edge(self, from_node, to_node, weight=None, edge_type="walkway", bidirectional=True):
        if from_node not in self.nodes or to_node not in self.nodes:
            return False

        if weight is None:
            # Calculate physical euclidean distance in coordinate space
            n1 = self.nodes[from_node]
            n2 = self.nodes[to_node]
            if n1["floor"] == n2["floor"]:
                weight = round(math.hypot(n2["x"] - n1["x"], n2["y"] - n1["y"]), 2)
            else:
                # Vertical staircase descent calibrated travel cost
                floor_diff = abs(n2["floor"] - n1["floor"])
                weight = round(floor_diff * 28.0, 2)

        edge_obj = {
            "from": from_node,
            "to": to_node,
            "weight": weight,
            "type": edge_type,
            "bidirectional": bidirectional
        }
        self.edges.append(edge_obj)

        self.adjacency[from_node].append((to_node, weight, edge_type))
        if bidirectional:
            self.adjacency[to_node].append((from_node, weight, edge_type))
        return True

    def load_and_build_graph(self):
        """Constructs full Block A coordinate graph spanning Ground through 4th floor."""
        with open(self.building_data_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        floors = raw_data.get("floors", {})

        # 1. Build Nodes & Corridors for each floor (0, 1, 2, 3, 4)
        for fl_idx in range(5):
            fl_key = str(fl_idx)
            fl_data = floors.get(fl_key, {})

            # Standard corridor waypoints on this floor
            # West Wing Corridor Nodes
            self.add_node(f"N{fl_idx}_W_NORTH", f"Floor {fl_idx} West North Corridor", fl_idx, 275, 175, "corridor")
            self.add_node(f"N{fl_idx}_W_MID_N", f"Floor {fl_idx} West Mid-North Corridor", fl_idx, 275, 290, "corridor")
            self.add_node(f"N{fl_idx}_W_CENTER", f"Floor {fl_idx} West Central Corridor Junction", fl_idx, 275, 370, "corridor")
            self.add_node(f"N{fl_idx}_W_MID_S", f"Floor {fl_idx} West Mid-South Corridor", fl_idx, 275, 470, "corridor")
            self.add_node(f"N{fl_idx}_W_SOUTH", f"Floor {fl_idx} West South Corridor", fl_idx, 275, 550, "corridor")

            # Connect West Corridor vertical spine
            self.add_edge(f"N{fl_idx}_W_NORTH", f"N{fl_idx}_W_MID_N", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_W_MID_N", f"N{fl_idx}_W_CENTER", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_W_CENTER", f"N{fl_idx}_W_MID_S", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_W_MID_S", f"N{fl_idx}_W_SOUTH", edge_type="corridor")

            # East Wing Corridor Nodes
            self.add_node(f"N{fl_idx}_E_NORTH", f"Floor {fl_idx} East North Corridor", fl_idx, 925, 175, "corridor")
            self.add_node(f"N{fl_idx}_E_MID_N", f"Floor {fl_idx} East Mid-North Corridor", fl_idx, 925, 290, "corridor")
            self.add_node(f"N{fl_idx}_E_CENTER", f"Floor {fl_idx} East Central Corridor Junction", fl_idx, 925, 370, "corridor")
            self.add_node(f"N{fl_idx}_E_MID_S", f"Floor {fl_idx} East Mid-South Corridor", fl_idx, 925, 470, "corridor")
            self.add_node(f"N{fl_idx}_E_SOUTH", f"Floor {fl_idx} East South Corridor", fl_idx, 925, 550, "corridor")

            # Connect East Corridor vertical spine
            self.add_edge(f"N{fl_idx}_E_NORTH", f"N{fl_idx}_E_MID_N", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_E_MID_N", f"N{fl_idx}_E_CENTER", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_E_CENTER", f"N{fl_idx}_E_MID_S", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_E_MID_S", f"N{fl_idx}_E_SOUTH", edge_type="corridor")

            # Central Bridge Spine Corridor Nodes
            self.add_node(f"N{fl_idx}_C_WEST", f"Floor {fl_idx} Central Bridge West", fl_idx, 450, 370, "corridor")
            self.add_node(f"N{fl_idx}_C_CENTER", f"Floor {fl_idx} Central Bridge Midpoint", fl_idx, 600, 370, "corridor")
            self.add_node(f"N{fl_idx}_C_EAST", f"Floor {fl_idx} Central Bridge East", fl_idx, 750, 370, "corridor")

            # Connect Central Spine
            self.add_edge(f"N{fl_idx}_W_CENTER", f"N{fl_idx}_C_WEST", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_C_WEST", f"N{fl_idx}_C_CENTER", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_C_CENTER", f"N{fl_idx}_C_EAST", edge_type="corridor")
            self.add_edge(f"N{fl_idx}_C_EAST", f"N{fl_idx}_E_CENTER", edge_type="corridor")

            # Staircase Nodes on this floor
            # Stair A (West)
            stair_a_node = f"STAIR_A_{fl_idx}"
            self.add_node(stair_a_node, f"Staircase A Core (Level {fl_idx})", fl_idx, 170, 175, "stair", code=f"STA-{fl_idx}")
            self.add_edge(stair_a_node, f"N{fl_idx}_W_NORTH", weight=105.0, edge_type="stair_door")

            # Stair B (East)
            stair_b_node = f"STAIR_B_{fl_idx}"
            self.add_node(stair_b_node, f"Staircase B Core (Level {fl_idx})", fl_idx, 1030, 175, "stair", code=f"STB-{fl_idx}")
            self.add_edge(stair_b_node, f"N{fl_idx}_E_NORTH", weight=105.0, edge_type="stair_door")

            # Add Room Door Nodes and link to nearest corridor
            for room in fl_data.get("rooms", []):
                r_id = room["id"]
                door_x = room["door"]["x"]
                door_y = room["door"]["y"]
                r_node = f"NODE_{r_id}"
                self.add_node(
                    r_node,
                    f"[{room['code']}] {room['name']}",
                    fl_idx,
                    door_x,
                    door_y,
                    node_type="room",
                    code=room["code"],
                    metadata={"room_id": r_id, "type": room.get("type", "room")}
                )

                # Find closest corridor waypoint on this floor to connect room door
                best_corr = None
                min_dist = float("inf")
                for c_node_id, c_node in self.nodes.items():
                    if c_node["floor"] == fl_idx and c_node["type"] == "corridor":
                        d = math.hypot(c_node["x"] - door_x, c_node["y"] - door_y)
                        if d < min_dist:
                            min_dist = d
                            best_corr = c_node_id

                if best_corr:
                    self.add_edge(r_node, best_corr, edge_type="room_access")

        # 2. Multi-Floor Vertical Stairwell Links
        # Link Staircase A across floors 0 <-> 1 <-> 2 <-> 3 <-> 4
        for f in range(4):
            self.add_edge(
                f"STAIR_A_{f}",
                f"STAIR_A_{f+1}",
                weight=28.0,
                edge_type="vertical_stair",
                bidirectional=True
            )
            self.add_edge(
                f"STAIR_B_{f}",
                f"STAIR_B_{f+1}",
                weight=28.0,
                edge_type="vertical_stair",
                bidirectional=True
            )

        # 3. Ground Floor Building Exits & Outdoor Assembly Points
        # Primary Exit 1 (Main South)
        self.add_node("NODE_EXIT_G_MAIN", "Exit 1: Main South Exit", 0, 600, 620, "exit", code="EXIT-1")
        self.add_node("NODE_LOBBY_SOUTH", "Ground Floor Lobby South Portal", 0, 600, 480, "corridor")
        self.add_edge("N0_C_CENTER", "NODE_LOBBY_SOUTH", edge_type="corridor")
        self.add_edge("NODE_LOBBY_SOUTH", "NODE_EXIT_G_MAIN", weight=140.0, edge_type="exit_corridor")

        # West Wing Fire Exit 2
        self.add_node("NODE_EXIT_G_WEST", "Exit 2: West Wing Emergency Fire Exit", 0, 100, 370, "exit", code="EXIT-2")
        self.add_edge("N0_W_CENTER", "NODE_EXIT_G_WEST", weight=175.0, edge_type="exit_corridor")

        # East Wing Fire Exit 3
        self.add_node("NODE_EXIT_G_EAST", "Exit 3: East Wing Emergency Fire Exit", 0, 1100, 370, "exit", code="EXIT-3")
        self.add_edge("N0_E_CENTER", "NODE_EXIT_G_EAST", weight=175.0, edge_type="exit_corridor")

        # Outdoor Assembly Points
        self.add_node("NODE_ASSEMBLY_SOUTH", "Assembly Point 1 (South Lawn)", 0, 600, 715, "assembly", code="MUSTER-1")
        self.add_node("NODE_ASSEMBLY_NORTH", "Assembly Point 2 (North Sports Ground)", 0, 600, 45, "assembly", code="MUSTER-2")

        # Connect Exits to Safe Outdoor Assembly Points
        self.add_edge("NODE_EXIT_G_MAIN", "NODE_ASSEMBLY_SOUTH", weight=95.0, edge_type="outdoor_egress")
        self.add_edge("NODE_EXIT_G_EAST", "NODE_ASSEMBLY_SOUTH", weight=360.0, edge_type="outdoor_egress")
        self.add_edge("NODE_EXIT_G_WEST", "NODE_ASSEMBLY_NORTH", weight=410.0, edge_type="outdoor_egress")

    def get_all_exits(self):
        """Returns all primary exterior exits on Ground Floor."""
        return [
            nid for nid, n in self.nodes.items()
            if n["type"] == "exit" or n["type"] == "assembly"
        ]

    def export_graph_json(self):
        """Exports graph in web-ready JSON format for client rendering."""
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "exits": [nid for nid, n in self.nodes.items() if n["type"] == "exit"],
            "assembly_points": [nid for nid, n in self.nodes.items() if n["type"] == "assembly"],
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges)
        }

