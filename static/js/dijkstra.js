/**
 * Client-Side Dijkstra Routing & Animated Path Visualizer
 * Enforces dynamic hazard edge-exclusion and real-time safe route rendering.
 */

class ClientDijkstra {
  constructor(graphData) {
    this.nodes = graphData.nodes || {};
    this.edges = graphData.edges || [];
    this.adjacency = {};
    this.buildAdjacency();
  }

  buildAdjacency() {
    this.adjacency = {};
    for (const nid in this.nodes) {
      this.adjacency[nid] = [];
    }

    this.edges.forEach(e => {
      const u = e.from;
      const v = e.to;
      const w = e.weight;
      if (this.adjacency[u]) this.adjacency[u].push({ neighbor: v, weight: w, type: e.type });
      if (e.bidirectional !== false && this.adjacency[v]) {
        this.adjacency[v].push({ neighbor: u, weight: w, type: e.type });
      }
    });
  }

  calculateRoute(startNodeId, options = {}) {
    const blockedNodes = new Set(options.blockedNodes || []);
    const blockedEdges = new Set();
    (options.blockedEdges || []).forEach(e => {
      if (Array.isArray(e)) {
        blockedEdges.add(`${e[0]}--${e[1]}`);
        blockedEdges.add(`${e[1]}--${e[0]}`);
      } else if (typeof e === 'string') {
        const parts = e.split('--');
        if (parts.length === 2) {
          blockedEdges.add(`${parts[0]}--${parts[1]}`);
          blockedEdges.add(`${parts[1]}--${parts[0]}`);
        }
      }
    });

    if (!this.nodes[startNodeId]) {
      return { success: false, error: `Start node '${startNodeId}' not found.` };
    }
    if (blockedNodes.has(startNodeId)) {
      return { success: false, error: `Current position '${startNodeId}' is blocked by hazard.` };
    }

    // Determine target exits
    let targetExits = options.targetExits || [];
    if (targetExits.length === 0) {
      targetExits = Object.keys(this.nodes).filter(nid => this.nodes[nid].type === 'exit');
    }
    const validTargets = targetExits.filter(t => !blockedNodes.has(t));
    if (validTargets.length === 0) {
      return { success: false, error: 'All exits are compromised by active hazards.' };
    }

    // Distances & Previous
    const dist = {};
    const prev = {};
    const unvisited = new Set(Object.keys(this.nodes));

    for (const nid in this.nodes) {
      dist[nid] = Infinity;
      prev[nid] = null;
    }
    dist[startNodeId] = 0;

    while (unvisited.size > 0) {
      // Find unvisited node with min dist
      let curr = null;
      let minVal = Infinity;
      unvisited.forEach(nid => {
        if (dist[nid] < minVal) {
          minVal = dist[nid];
          curr = nid;
        }
      });

      if (curr === null || minVal === Infinity) break;
      unvisited.delete(curr);

      // Early stop if nearest exit reached
      if (validTargets.includes(curr)) {
        break;
      }

      const neighbors = this.adjacency[curr] || [];
      neighbors.forEach(edge => {
        const next = edge.neighbor;
        if (!unvisited.has(next)) return;
        if (blockedNodes.has(next)) return;
        if (blockedEdges.has(`${curr}--${next}`)) return;

        const alt = dist[curr] + edge.weight;
        if (alt < dist[next]) {
          dist[next] = alt;
          prev[next] = curr;
        }
      });
    }

    // Find closest reachable exit
    let bestExit = null;
    let bestDist = Infinity;
    validTargets.forEach(tid => {
      if (dist[tid] < bestDist) {
        bestDist = dist[tid];
        bestExit = tid;
      }
    });

    if (!bestExit || bestDist === Infinity) {
      return { success: false, error: 'No safe evacuation path available. All egress routes blocked.' };
    }

    // Reconstruct path
    const path = [];
    let curr = bestExit;
    while (curr) {
      path.push(curr);
      curr = prev[curr];
    }
    path.reverse();

    const distanceMeters = Math.round(bestDist * 0.25 * 10) / 10;
    const estimatedTimeSec = Math.max(Math.round(distanceMeters / 1.15), 12);
    const pathDetails = path.map(nid => this.nodes[nid]);

    // Compute directional turns (left, right, straight, uturn)
    const computeTurn = (pPrev, pCurr, pNext) => {
      const v1x = pCurr.x - pPrev.x;
      const v1y = pCurr.y - pPrev.y;
      const v2x = pNext.x - pNext.x;
      const v2y = pNext.y - pCurr.y;
      const cross = v1x * (pNext.y - pCurr.y) - v1y * (pNext.x - pCurr.x);
      const dot = v1x * (pNext.x - pCurr.x) + v1y * (pNext.y - pCurr.y);
      const deg = Math.atan2(cross, dot) * (180 / Math.PI);
      if (deg >= -35 && deg <= 35) return { maneuver: "straight", icon: "⬆️", label: "Proceed Straight" };
      if (deg > 35 && deg < 145) return { maneuver: "right", icon: "➡️", label: "Turn Right" };
      if (deg < -35 && deg > -145) return { maneuver: "left", icon: "⬅️", label: "Turn Left" };
      return { maneuver: "uturn", icon: "⬇️", label: "Turn Around" };
    };

    // Generate instructions
    const instructions = [];
    instructions.push({
      step: 1,
      maneuver: "start",
      icon: "🚪",
      title: "Evacuation Initiated",
      floor: pathDetails[0].floor,
      text: `Start from ${pathDetails[0].name} (Level ${pathDetails[0].floor}).`,
      distance_meters: 0
    });

    let stepNum = 2;
    for (let i = 1; i < pathDetails.length; i++) {
      const c = pathDetails[i];
      const p = pathDetails[i - 1];
      const distSeg = Math.round(Math.hypot(c.x - p.x, c.y - p.y) * 0.25 * 10) / 10;

      if (c.floor !== p.floor) {
        const stairName = c.id.includes("STAIR_A") ? "Staircase A (West)" : "Staircase B (East)";
        instructions.push({
          step: stepNum++,
          maneuver: "descend",
          icon: "🔽",
          title: `Take ${stairName} (Descend to Level ${c.floor})`,
          floor: c.floor,
          text: `Enter ${stairName} and descend to Level ${c.floor}.`,
          distance_meters: distSeg
        });
      } else if (p.type === "room" && c.type === "corridor") {
        let t = { maneuver: "straight", icon: "⬆️", label: "Proceed Straight" };
        if (i + 1 < pathDetails.length) t = computeTurn(p, c, pathDetails[i + 1]);
        instructions.push({
          step: stepNum++,
          maneuver: t.maneuver,
          icon: t.icon,
          title: `${t.label} into Corridor`,
          floor: c.floor,
          text: `Step out of room into hallway and ${t.label.toLowerCase()} along corridor.`,
          distance_meters: distSeg
        });
      } else if (p.type === "corridor" && c.type === "corridor" && i + 1 < pathDetails.length) {
        const t = computeTurn(p, c, pathDetails[i + 1]);
        if (t.maneuver === "left" || t.maneuver === "right" || t.maneuver === "uturn") {
          instructions.push({
            step: stepNum++,
            maneuver: t.maneuver,
            icon: t.icon,
            title: `${t.label} at Hallway Junction`,
            floor: c.floor,
            text: `${t.label} toward ${pathDetails[i + 1].name}.`,
            distance_meters: distSeg
          });
        }
      } else if (c.type === "exit") {
        instructions.push({
          step: stepNum++,
          maneuver: "exit",
          icon: "🚪",
          title: `Exit Facility via ${c.name}`,
          floor: 0,
          text: `Reach designated exit portal ${c.name} into exterior muster perimeter.`,
          distance_meters: distSeg
        });
      }
    }

    if (pathDetails[pathDetails.length - 1].type !== "exit" && pathDetails[pathDetails.length - 1].type !== "assembly") {
      instructions.push({
        step: stepNum++,
        maneuver: "exit",
        icon: "✅",
        title: "Clear Building Perimeter",
        floor: 0,
        text: "Proceed through exit door to primary outdoor assembly clearing.",
        distance_meters: 0
      });
    }

    return {
      success: true,
      path: path,
      pathDetails: pathDetails,
      targetExit: bestExit,
      targetExitName: this.nodes[bestExit].name,
      totalWeight: bestDist,
      distanceMeters: distanceMeters,
      estimatedTimeSeconds: estimatedTimeSec,
      instructions: instructions
    };
  }
}

if (typeof window !== "undefined") {
  window.ClientDijkstra = ClientDijkstra;
}

