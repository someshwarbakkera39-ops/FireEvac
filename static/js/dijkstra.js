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

    // Generate instructions
    const instructions = [];
    instructions.push({
      step: 1,
      title: "Evacuation Initiated",
      floor: pathDetails[0].floor,
      text: `Start from ${pathDetails[0].name} (Level ${pathDetails[0].floor}).`
    });

    let stepNum = 2;
    for (let i = 1; i < pathDetails.length; i++) {
      const c = pathDetails[i];
      const p = pathDetails[i - 1];

      if (c.floor !== p.floor) {
        const stairName = c.id.includes("STAIR_A") ? "Staircase A (West)" : "Staircase B (East)";
        instructions.push({
          step: stepNum++,
          title: `Take ${stairName} (Descend to Level ${c.floor})`,
          floor: c.floor,
          text: `Enter ${stairName} and descend to Level ${c.floor}.`
        });
      } else if (c.type === "exit") {
        instructions.push({
          step: stepNum++,
          title: `Exit Facility via ${c.name}`,
          floor: 0,
          text: `Reach designated exit portal ${c.name} into exterior muster perimeter.`
        });
      }
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

