"""
Dynamic Dijkstra Path Optimization Engine for Multi-Floor Evacuation
Implements priority-queue pathfinding with real-time hazard exclusion logic.
"""

import heapq
import math

class DijkstraRoutingEngine:
    def __init__(self, graph_model):
        self.graph = graph_model

    def calculate_evacuation_route(self, start_node_id, target_exit_ids=None, blocked_edges=None, blocked_nodes=None):
        """
        Executes dynamic Dijkstra shortest path from start_node_id to nearest safe exit.
        Excludes any blocked edges or hazardous nodes.
        
        :param start_node_id: ID of the starting node (room door, corridor, or QR checkpoint)
        :param target_exit_ids: Optional list of acceptable exit node IDs. Defaults to all ground exits.
        :param blocked_edges: Set of tuple pairs (u, v) or undirected sets representing blocked corridor edges.
        :param blocked_nodes: Set of node IDs engulfed in fire or structurally impassable.
        :return: Dict containing path, distance, turn-by-turn guidance, and evacuation metrics.
        """
        if start_node_id not in self.graph.nodes:
            return {
                "success": False,
                "error": f"Starting node '{start_node_id}' does not exist in graph."
            }

        # Initialize exclusion sets
        blocked_nodes_set = set(blocked_nodes or [])
        blocked_edges_set = set()
        if blocked_edges:
            for item in blocked_edges:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    u, v = item[0], item[1]
                    blocked_edges_set.add((u, v))
                    blocked_edges_set.add((v, u))
                elif isinstance(item, str) and "--" in item:
                    u, v = item.split("--")
                    blocked_edges_set.add((u, v))
                    blocked_edges_set.add((v, u))

        # Check if starting node itself is blocked
        if start_node_id in blocked_nodes_set:
            return {
                "success": False,
                "error": f"Current location '{start_node_id}' is directly compromised by hazard."
            }

        # Default exits if not provided
        if not target_exit_ids:
            target_exit_ids = [
                nid for nid, n in self.graph.nodes.items()
                if n["type"] == "exit"
            ]

        # Filter out blocked target exits
        valid_targets = [tid for tid in target_exit_ids if tid not in blocked_nodes_set]
        if not valid_targets:
            return {
                "success": False,
                "error": "All designated building exits are blocked by simulated hazards."
            }

        # Dijkstra algorithm using min-heap
        distances = {node_id: float("inf") for node_id in self.graph.nodes}
        distances[start_node_id] = 0.0
        previous_nodes = {node_id: None for node_id in self.graph.nodes}
        
        # Priority queue stores (cost, current_node)
        pq = [(0.0, start_node_id)]
        visited = set()

        while pq:
            current_dist, current_node = heapq.heappop(pq)

            if current_node in visited:
                continue
            visited.add(current_node)

            # If current node is one of the valid targets and has the minimum cost, we can evaluate
            if current_node in valid_targets and current_dist < float("inf"):
                # Early termination when shortest exit reached
                best_exit = current_node
                break

            for neighbor, weight, edge_type in self.graph.adjacency.get(current_node, []):
                # Check hazard exclusion
                if neighbor in blocked_nodes_set:
                    continue
                if (current_node, neighbor) in blocked_edges_set:
                    continue

                new_dist = current_dist + weight
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous_nodes[neighbor] = current_node
                    heapq.heappush(pq, (new_dist, neighbor))
        else:
            best_exit = None

        # Determine the nearest reachable exit
        reachable_targets = [(distances[tid], tid) for tid in valid_targets if distances[tid] < float("inf")]
        if not reachable_targets:
            return {
                "success": False,
                "error": "No safe path found! All viable egress routes are cut off by active hazards."
            }

        reachable_targets.sort(key=lambda x: x[0])
        best_cost, best_exit = reachable_targets[0]

        # Reconstruct path from start to best_exit
        path = []
        curr = best_exit
        while curr is not None:
            path.append(curr)
            curr = previous_nodes[curr]
        path.reverse()

        # Detailed breakdown of nodes in path
        path_nodes_data = [self.graph.nodes[nid] for nid in path]

        # Evacuation Metrics
        # Conversion ratio: 1 coordinate unit ≈ 0.25 meters in Block A facility
        distance_meters = round(best_cost * 0.25, 1)
        # Normal calm walking speed is 1.4 m/s; emergency evacuation speed calibrated at 1.15 m/s
        estimated_time_sec = max(int(round(distance_meters / 1.15)), 12)

        # Floors traversed
        floors_in_path = list(dict.fromkeys([n["floor"] for n in path_nodes_data]))
        
        # Stairwells used
        stairwells_used = []
        for n in path_nodes_data:
            if "STAIR_A" in n["id"] and "Staircase A (West Wing)" not in stairwells_used:
                stairwells_used.append("Staircase A (West Wing)")
            elif "STAIR_B" in n["id"] and "Staircase B (East Wing)" not in stairwells_used:
                stairwells_used.append("Staircase B (East Wing)")

        # Generate Turn-by-Turn Navigation Instructions
        instructions = self._generate_instructions(path_nodes_data, best_exit, stairwells_used)

        return {
            "success": True,
            "start_node": start_node_id,
            "target_exit": best_exit,
            "target_exit_name": self.graph.nodes[best_exit]["name"],
            "path": path,
            "path_details": path_nodes_data,
            "total_weight": round(best_cost, 2),
            "distance_meters": distance_meters,
            "estimated_time_seconds": estimated_time_sec,
            "floors_traversed": floors_in_path,
            "stairwells_used": stairwells_used,
            "instructions": instructions,
            "alternate_route_applied": len(blocked_edges_set) > 0 or len(blocked_nodes_set) > 0
        }

    def _compute_turn(self, p_prev, p_curr, p_next):
        """Computes human heading maneuver (straight, left, right, uturn)."""
        v1_x = p_curr["x"] - p_prev["x"]
        v1_y = p_curr["y"] - p_prev["y"]
        v2_x = p_next["x"] - p_curr["x"]
        v2_y = p_next["y"] - p_curr["y"]

        len1 = math.hypot(v1_x, v1_y)
        len2 = math.hypot(v2_x, v2_y)
        if len1 < 1e-3 or len2 < 1e-3:
            return "straight", "⬆️", "Proceed Straight"

        cross = v1_x * v2_y - v1_y * v2_x
        dot = v1_x * v2_x + v1_y * v2_y
        angle_deg = math.degrees(math.atan2(cross, dot))

        if -35.0 <= angle_deg <= 35.0:
            return "straight", "⬆️", "Proceed Straight"
        elif 35.0 < angle_deg < 145.0:
            return "right", "➡️", "Turn Right"
        elif -145.0 < angle_deg < -35.0:
            return "left", "⬅️", "Turn Left"
        else:
            return "uturn", "⬇️", "Turn Around"

    def _generate_instructions(self, path_nodes, exit_node_id, stairwells):
        """Generates clear, step-by-step human evacuation directives with left/right/straight navigation maneuvers."""
        instructions = []
        if not path_nodes:
            return instructions

        start = path_nodes[0]
        instructions.append({
            "step": 1,
            "type": "start",
            "maneuver": "start",
            "icon": "🚪",
            "floor": start["floor"],
            "title": "Evacuation Initiated",
            "text": f"Begin immediate egress from {start['name']} on Floor {start['floor']}.",
            "distance_meters": 0
        })

        step_counter = 2
        i = 1
        while i < len(path_nodes):
            curr = path_nodes[i]
            prev = path_nodes[i - 1]
            dist_seg = round(math.hypot(curr["x"] - prev["x"], curr["y"] - prev["y"]) * 0.25, 1)

            # Check for vertical floor transition via staircase
            if curr["floor"] != prev["floor"]:
                stair_name = "Staircase A" if "STAIR_A" in curr["id"] else "Staircase B"
                direction = "downward" if curr["floor"] < prev["floor"] else "upward"
                instructions.append({
                    "step": step_counter,
                    "type": "stair_descent",
                    "maneuver": "descend",
                    "icon": "🔽",
                    "floor": curr["floor"],
                    "title": f"Take {stair_name} ({direction.upper()})",
                    "text": f"Enter {stair_name} and descend from Floor {prev['floor']} to Floor {curr['floor']}.",
                    "distance_meters": dist_seg
                })
                step_counter += 1
                i += 1
                continue

            # Check for Corridor Transitions
            if curr["type"] == "corridor" and prev["type"] == "room":
                turn_dir = "straight"
                turn_icon = "⬆️"
                turn_label = "Proceed Straight"
                if i + 1 < len(path_nodes):
                    turn_dir, turn_icon, turn_label = self._compute_turn(prev, curr, path_nodes[i + 1])
                instructions.append({
                    "step": step_counter,
                    "type": "corridor_entry",
                    "maneuver": turn_dir,
                    "icon": turn_icon,
                    "floor": curr["floor"],
                    "title": f"{turn_label} into Corridor",
                    "text": f"Step out through door into hallway ({curr['name']}) and {turn_label.lower()}.",
                    "distance_meters": dist_seg
                })
                step_counter += 1
            elif curr["type"] == "stair" and prev["type"] == "corridor":
                stair_name = "Staircase A (West)" if "STAIR_A" in curr["id"] else "Staircase B (East)"
                instructions.append({
                    "step": step_counter,
                    "type": "stair_approach",
                    "maneuver": "straight",
                    "icon": "⬆️",
                    "floor": curr["floor"],
                    "title": f"Proceed to {stair_name}",
                    "text": f"Follow corridor directly to {stair_name} fire door.",
                    "distance_meters": dist_seg
                })
                step_counter += 1
            elif curr["type"] == "corridor" and prev["type"] == "corridor" and i + 1 < len(path_nodes):
                turn_dir, turn_icon, turn_label = self._compute_turn(prev, curr, path_nodes[i + 1])
                if turn_dir in ["left", "right", "uturn"]:
                    instructions.append({
                        "step": step_counter,
                        "type": "corridor_turn",
                        "maneuver": turn_dir,
                        "icon": turn_icon,
                        "floor": curr["floor"],
                        "title": f"{turn_label} at Junction",
                        "text": f"{turn_label} along corridor toward {path_nodes[i+1]['name']}.",
                        "distance_meters": dist_seg
                    })
                    step_counter += 1
            elif curr["type"] == "exit":
                instructions.append({
                    "step": step_counter,
                    "type": "exit_portal",
                    "maneuver": "exit",
                    "icon": "🚪",
                    "floor": 0,
                    "title": f"Pass through {curr['name']}",
                    "text": f"Pass through designated exterior exit door into open perimeter.",
                    "distance_meters": dist_seg
                })
                step_counter += 1
            elif curr["type"] == "assembly":
                instructions.append({
                    "step": step_counter,
                    "type": "safe_assembly",
                    "maneuver": "safe",
                    "icon": "✅",
                    "floor": 0,
                    "title": "Proceed to Safe Assembly Area",
                    "text": f"Arrive at {curr['name']}. Report immediately to safety marshals.",
                    "distance_meters": dist_seg
                })
                step_counter += 1

            i += 1

        # Final instruction ensuring assembly arrival
        if path_nodes[-1]["type"] != "assembly":
            instructions.append({
                "step": step_counter,
                "type": "safe_arrival",
                "maneuver": "safe",
                "icon": "✅",
                "floor": 0,
                "title": "Clear Egress Corridor",
                "text": "Evacuate building perimeter and proceed to designated Outdoor Assembly Grounds.",
                "distance_meters": 0
            })

        return instructions

