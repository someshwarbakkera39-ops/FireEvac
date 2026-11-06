/**
 * 2D Digital Twin Interactive Vector SVG Map Renderer
 * Renders digitized architectural floor plans of Block A (G through 4F)
 * Includes Phase 2 Dynamic Path Optimization & Hazard Exclusion layers.
 */

class FloorMapRenderer {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) throw new Error(`Container #${containerId} not found`);

    this.model = window.BLOCK_A_MODEL;
    this.currentFloor = options.initialFloor !== undefined ? options.initialFloor : 0;
    this.onNodeClick = options.onNodeClick || null;
    this.onRoomClick = options.onRoomClick || null;
    this.onQrClick = options.onQrClick || null;
    this.qrCodes = options.qrCodes || [];

    // View state
    this.zoom = 1;
    this.panX = 0;
    this.panY = 0;
    this.isPanning = false;
    this.startX = 0;
    this.startY = 0;

    // Layer visibility
    this.layers = {
      rooms: true,
      labels: true,
      corridors: true,
      stairwells: true,
      exits: true,
      grid: true,
      graph: false,
      path: true,
      hazards: true,
      qr: true
    };

    // Active path / highlight layers (for Dijkstra & Hazards)
    this.activePathNodes = [];      // Array of node IDs
    this.graphData = null;          // Holds graph model {nodes, edges}
    this.blockedEdges = new Set();  // "u--v"
    this.blockedNodes = new Set();  // "node_id"
    this.rawHazards = [];           // Array of {id, floor_id, location_x, location_y, type, radius}
    this.startNode = null;          // node_id
    this.simOccupants = [];         // Active drill occupants
    this.isEvacuated = false;       // True when user confirms safe evacuation outside
    this.evacuatedExitId = null;    // The exit node user exited through
    this.hasDragged = false;
    this.isMouseDown = false;
    this.downClientX = 0;
    this.downClientY = 0;

    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div class="map-wrapper" style="position:relative; width:100%; height:100%; overflow:hidden; background:#0f172a;">
        <svg id="buildingSvg" viewBox="0 0 1200 750" preserveAspectRatio="xMidYMid meet"
             style="width:100%; height:100%; cursor:grab; user-select:none;">
          <defs>
            <!-- Grid pattern -->
            <pattern id="archGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(100, 116, 139, 0.15)" stroke-width="1"/>
              <circle cx="0" cy="0" r="1.5" fill="rgba(100, 116, 139, 0.3)"/>
            </pattern>
            
            <!-- Staircase hatch pattern -->
            <pattern id="stairTreads" width="8" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(0)">
              <rect width="8" height="16" fill="#fef3c7"/>
              <line x1="0" y1="4" x2="8" y2="4" stroke="#d97706" stroke-width="1"/>
              <line x1="0" y1="8" x2="8" y2="8" stroke="#d97706" stroke-width="1"/>
              <line x1="0" y1="12" x2="8" y2="12" stroke="#d97706" stroke-width="1"/>
              <line x1="0" y1="16" x2="8" y2="16" stroke="#b45309" stroke-width="1.5"/>
            </pattern>

            <!-- Hazard Warning Barricade Pattern -->
            <pattern id="hazardBarricade" width="20" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="10" height="20" fill="#dc2626"/>
              <rect x="10" width="10" height="20" fill="#fbbf24"/>
            </pattern>

            <!-- Glow filters for safety palette -->
            <filter id="greenGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#16a34a" flood-opacity="0.9"/>
            </filter>
            <filter id="redGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#dc2626" flood-opacity="1"/>
            </filter>
            <filter id="blueGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#2563eb" flood-opacity="1"/>
            </filter>
            <filter id="cyanGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#06b6d4" flood-opacity="0.95"/>
            </filter>

            <!-- Marker for directed path -->
            <marker id="pathArrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#22c55e" />
            </marker>
          </defs>

          <!-- Root Transform Group for Pan & Zoom -->
          <g id="viewportGroup">
            <g id="gridLayer"></g>
            <g id="structureLayer"></g>
            <g id="corridorLayer"></g>
            <g id="roomsLayer"></g>
            <g id="stairwellsLayer"></g>
            <g id="exitsLayer"></g>
            <g id="graphLayer"></g>
            <g id="qrMarkersLayer"></g>
            <g id="hazardLayer"></g>
            <g id="pathLayer"></g>
            <g id="userMarkerLayer"></g>
            <g id="simulationLayer"></g>
          </g>
        </svg>

        <!-- North Compass Badge -->
        <div style="position:absolute; top:12px; left:12px; pointer-events:none; z-index:25; display:flex; align-items:center; gap:5px; background:rgba(15, 23, 42, 0.88); border:1px solid #334155; padding:5px 9px; border-radius:6px; font-size:10px; color:#cbd5e1; font-weight:800; box-shadow:0 4px 12px rgba(0,0,0,0.4); backdrop-filter:blur(4px);">
          <span style="color:#ef4444; font-size:12px;">▲</span> NORTH <span style="color:#64748b; font-weight:normal;">| 1:100</span>
        </div>

        <!-- Floating On-Canvas Smooth Navigation HUD Controls -->
        <div class="map-hud-controls" style="position:absolute; bottom:16px; right:16px; display:flex; flex-direction:column; gap:6px; z-index:30;">
          <button class="map-hud-btn" id="mapHudZoomIn" title="Zoom In (+)" style="width:34px; height:34px; border-radius:6px; background:rgba(15, 23, 42, 0.9); border:1px solid #334155; color:#38bdf8; font-size:16px; font-weight:800; display:flex; align-items:center; justify-content:center; cursor:pointer; box-shadow:0 4px 12px rgba(0,0,0,0.5); transition:all 0.15s ease;">＋</button>
          <button class="map-hud-btn" id="mapHudZoomOut" title="Zoom Out (−)" style="width:34px; height:34px; border-radius:6px; background:rgba(15, 23, 42, 0.9); border:1px solid #334155; color:#38bdf8; font-size:16px; font-weight:800; display:flex; align-items:center; justify-content:center; cursor:pointer; box-shadow:0 4px 12px rgba(0,0,0,0.5); transition:all 0.15s ease;">−</button>
          <button class="map-hud-btn" id="mapHudReset" title="Reset View Frame (100%)" style="width:34px; height:34px; border-radius:6px; background:rgba(15, 23, 42, 0.9); border:1px solid #334155; color:#a5b4fc; font-size:14px; font-weight:800; display:flex; align-items:center; justify-content:center; cursor:pointer; box-shadow:0 4px 12px rgba(0,0,0,0.5); transition:all 0.15s ease;">⟲</button>
        </div>

        <!-- Dynamic Architectural Tooltip -->
        <div id="mapTooltip" style="position:absolute; display:none; pointer-events:none; z-index:100;
             background:rgba(15, 23, 42, 0.95); border:1px solid #38bdf8; color:#f8fafc;
             padding:8px 12px; border-radius:6px; font-size:12px; font-family:sans-serif;
             box-shadow:0 10px 25px rgba(0,0,0,0.5); backdrop-filter:blur(4px);"></div>
      </div>
    `;

    this.svg = this.container.querySelector("#buildingSvg");
    this.viewportGroup = this.container.querySelector("#viewportGroup");
    this.tooltip = this.container.querySelector("#mapTooltip");

    // Hook HUD control buttons
    const btnIn = this.container.querySelector("#mapHudZoomIn");
    const btnOut = this.container.querySelector("#mapHudZoomOut");
    const btnReset = this.container.querySelector("#mapHudReset");
    if (btnIn) btnIn.addEventListener("click", () => this.zoomIn());
    if (btnOut) btnOut.addEventListener("click", () => this.zoomOut());
    if (btnReset) btnReset.addEventListener("click", () => this.resetView());

    this.attachEvents();
    this.render();
  }

  attachEvents() {
    // Mouse wheel zoom (silky smooth dampening to eliminate dizzying fast zooms)
    this.svg.addEventListener("wheel", (e) => {
      e.preventDefault();
      const delta = Math.sign(e.deltaY);
      const zoomFactor = delta < 0 ? 1.035 : 0.965;
      const newZoom = Math.min(Math.max(this.zoom * zoomFactor, 0.75), 2.8);
      
      const rect = this.svg.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      
      this.panX -= (mouseX / this.zoom) * (newZoom - this.zoom);
      this.panY -= (mouseY / this.zoom) * (newZoom - this.zoom);
      this.zoom = newZoom;
      this.updateTransform();
    }, { passive: false });

    // Pan with mouse drag
    this.svg.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return;
      this.isMouseDown = true;
      this.hasDragged = false;
      this.downClientX = e.clientX;
      this.downClientY = e.clientY;
      this.startX = e.clientX - this.panX;
      this.startY = e.clientY - this.panY;
    });

    window.addEventListener("mousemove", (e) => {
      if (!this.isMouseDown) return;
      if (Math.hypot(e.clientX - this.downClientX, e.clientY - this.downClientY) > 5) {
        this.hasDragged = true;
        this.isPanning = true;
        this.svg.style.cursor = "grabbing";
        this.panX = e.clientX - this.startX;
        this.panY = e.clientY - this.startY;
        this.updateTransform();
      }
    });

    window.addEventListener("mouseup", () => {
      this.isMouseDown = false;
      this.isPanning = false;
      this.svg.style.cursor = "grab";
    });

    // Touch support
    let touchStartDist = 0;
    this.svg.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) {
        this.isPanning = true;
        this.startX = e.touches[0].clientX - this.panX;
        this.startY = e.touches[0].clientY - this.panY;
      } else if (e.touches.length === 2) {
        this.isPanning = false;
        touchStartDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
      }
    });

    this.svg.addEventListener("touchmove", (e) => {
      if (this.isPanning && e.touches.length === 1) {
        this.panX = e.touches[0].clientX - this.startX;
        this.panY = e.touches[0].clientY - this.startY;
        this.updateTransform();
      } else if (e.touches.length === 2 && touchStartDist > 0) {
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const factor = dist / touchStartDist;
        this.zoom = Math.min(Math.max(this.zoom * (factor > 1 ? 1.03 : 0.97), 0.5), 4.5);
        this.updateTransform();
      }
    });

    this.svg.addEventListener("touchend", () => {
      this.isPanning = false;
    });
  }

  updateTransform() {
    this.viewportGroup.setAttribute(
      "transform",
      `translate(${this.panX}, ${this.panY}) scale(${this.zoom})`
    );
  }

  setFloor(floorLevel) {
    if (this.model.floors[floorLevel] !== undefined) {
      this.currentFloor = parseInt(floorLevel, 10);
      this.render();
    }
  }

  setGraphData(graphData) {
    this.graphData = graphData;
    this.render();
  }

  setRoute(pathNodeIds, startNodeId = null) {
    this.isEvacuated = false;
    this.activePathNodes = pathNodeIds || [];
    if (startNodeId) this.startNode = startNodeId;
    this.render();
  }

  setEvacuated(isEvacuated = true, exitId = "NODE_EXIT_G_MAIN") {
    this.isEvacuated = isEvacuated;
    this.evacuatedExitId = exitId;
    if (isEvacuated) {
      this.activePathNodes = [];
      this.currentFloor = 0;
    }
    this.render();
  }

  clearRoute() {
    this.activePathNodes = [];
    this.render();
  }

  setHazards(blockedNodes = [], blockedEdges = [], rawHazards = []) {
    this.blockedNodes = new Set(blockedNodes);
    this.blockedEdges = new Set(blockedEdges);
    this.rawHazards = rawHazards || [];
    this.render();
  }

  getSvgCoordinates(clientX, clientY) {
    if (this.svg) {
      try {
        const pt = this.svg.createSVGPoint();
        pt.x = clientX;
        pt.y = clientY;
        const target = this.viewportGroup || this.svg;
        const ctm = target.getScreenCTM();
        if (ctm) {
          const transformed = pt.matrixTransform(ctm.inverse());
          return {
            x: Math.round(transformed.x),
            y: Math.round(transformed.y)
          };
        }
      } catch (err) {}

      // Fallback calculation using bounding client rect & viewBox
      const rect = this.svg.getBoundingClientRect();
      const svgW = 1200;
      const svgH = 750;
      const scaleX = svgW / (rect.width || 1);
      const scaleY = svgH / (rect.height || 1);
      const relX = (clientX - rect.left) * scaleX;
      const relY = (clientY - rect.top) * scaleY;
      return {
        x: Math.round((relX - this.panX) / this.zoom),
        y: Math.round((relY - this.panY) / this.zoom)
      };
    }
    return { x: 600, y: 375 };
  }

  toggleLayer(layerKey, isVisible) {
    if (this.layers[layerKey] !== undefined) {
      this.layers[layerKey] = isVisible;
      this.render();
    }
  }

  resetView() {
    this.zoom = 1;
    this.panX = 0;
    this.panY = 0;
    this.updateTransform();
  }

  zoomIn() {
    this.zoom = Math.min(this.zoom * 1.15, 2.8);
    this.updateTransform();
  }

  zoomOut() {
    this.zoom = Math.max(this.zoom / 1.15, 0.75);
    this.updateTransform();
  }

  setQrCodes(qrList) {
    this.qrCodes = qrList || [];
    this.render();
  }

  showTooltip(e, html) {
    const rect = this.container.getBoundingClientRect();
    this.tooltip.innerHTML = html;
    this.tooltip.style.display = "block";
    this.tooltip.style.left = `${e.clientX - rect.left + 15}px`;
    this.tooltip.style.top = `${e.clientY - rect.top + 15}px`;
  }

  hideTooltip() {
    this.tooltip.style.display = "none";
  }

  render() {
    const floor = this.model.floors[this.currentFloor];
    if (!floor) return;

    // Clear layers
    this.container.querySelector("#gridLayer").innerHTML = "";
    this.container.querySelector("#structureLayer").innerHTML = "";
    this.container.querySelector("#corridorLayer").innerHTML = "";
    this.container.querySelector("#roomsLayer").innerHTML = "";
    this.container.querySelector("#stairwellsLayer").innerHTML = "";
    this.container.querySelector("#exitsLayer").innerHTML = "";
    this.container.querySelector("#graphLayer").innerHTML = "";
    const qrLayer = this.container.querySelector("#qrMarkersLayer");
    if (qrLayer) qrLayer.innerHTML = "";
    this.container.querySelector("#hazardLayer").innerHTML = "";
    this.container.querySelector("#pathLayer").innerHTML = "";
    this.container.querySelector("#userMarkerLayer").innerHTML = "";

    // 1. Grid Layer
    if (this.layers.grid) {
      this.container.querySelector("#gridLayer").innerHTML = `
        <rect x="0" y="0" width="1200" height="750" fill="url(#archGrid)" />
      `;
    }

    // 2. Structural Footprint (Outer Walls of Block A)
    const structHtml = `
      <!-- Outdoor Ground context -->
      <rect x="0" y="0" width="1200" height="750" fill="#0f172a"/>
      
      <!-- Assembly Grounds Guidance lines if on Ground Floor -->
      ${this.currentFloor === 0 ? `
        <rect x="420" y="660" width="360" height="80" rx="8" fill="rgba(22, 163, 74, 0.12)" stroke="#16a34a" stroke-dasharray="6,4" stroke-width="2"/>
        <text x="600" y="695" fill="#4ade80" font-size="14" font-weight="bold" text-anchor="middle" letter-spacing="1">PRIMARY SAFE ASSEMBLY POINT 1 (SOUTH LAWN)</text>
        <text x="600" y="715" fill="#86efac" font-size="11" text-anchor="middle">Direct Egress from Main South Exit</text>
        
        <rect x="420" y="10" width="360" height="70" rx="8" fill="rgba(22, 163, 74, 0.12)" stroke="#16a34a" stroke-dasharray="6,4" stroke-width="2"/>
        <text x="600" y="45" fill="#4ade80" font-size="14" font-weight="bold" text-anchor="middle" letter-spacing="1">SECONDARY SAFE MUSTER POINT 2 (NORTH SPORTS FIELD)</text>
      ` : ''}

      <!-- Main Building Footprint Perimeter -->
      <g id="outerPerimeter">
        <rect x="95" y="115" width="360" height="510" rx="10" fill="#1e293b" stroke="#475569" stroke-width="5"/>
        <rect x="445" y="275" width="310" height="190" fill="#1e293b" stroke="#475569" stroke-width="5"/>
        <rect x="745" y="115" width="360" height="510" rx="10" fill="#1e293b" stroke="#475569" stroke-width="5"/>

        <!-- Watermark -->
        <text x="600" y="225" fill="rgba(148, 163, 184, 0.2)" font-size="42" font-weight="900" text-anchor="middle" letter-spacing="6">BLOCK A</text>
        <text x="600" y="260" fill="rgba(56, 189, 248, 0.4)" font-size="18" font-weight="bold" text-anchor="middle" letter-spacing="3">${floor.name.toUpperCase()} (LEVEL ${floor.level})</text>
      </g>
    `;
    this.container.querySelector("#structureLayer").innerHTML = structHtml;

    // 3. Walkable Corridors
    if (this.layers.corridors) {
      let corrHtml = `
        <g id="corridorsGroup">
          <rect x="255" y="348" width="690" height="44" fill="#334155" stroke="#64748b" stroke-width="1.5"/>
          <rect x="255" y="155" width="40" height="420" fill="#334155" stroke="#64748b" stroke-width="1.5"/>
          <rect x="905" y="155" width="40" height="420" fill="#334155" stroke="#64748b" stroke-width="1.5"/>
          <rect x="170" y="160" width="105" height="30" fill="#334155" stroke="#64748b" stroke-width="1.5"/>
          <rect x="925" y="160" width="105" height="30" fill="#334155" stroke="#64748b" stroke-width="1.5"/>
      `;

      if (this.currentFloor === 0) {
        corrHtml += `
          <rect x="575" y="370" width="50" height="250" fill="#334155" stroke="#16a34a" stroke-dasharray="4,2" stroke-width="2"/>
          <rect x="100" y="348" width="160" height="44" fill="#334155" stroke="#16a34a" stroke-dasharray="4,2" stroke-width="2"/>
          <rect x="940" y="348" width="160" height="44" fill="#334155" stroke="#16a34a" stroke-dasharray="4,2" stroke-width="2"/>
        `;
      }

      corrHtml += `
          <line x1="275" y1="175" x2="275" y2="555" stroke="rgba(148, 163, 184, 0.4)" stroke-dasharray="4,4" stroke-width="2"/>
          <line x1="925" y1="175" x2="925" y2="555" stroke="rgba(148, 163, 184, 0.4)" stroke-dasharray="4,4" stroke-width="2"/>
          <line x1="275" y1="370" x2="925" y2="370" stroke="rgba(148, 163, 184, 0.4)" stroke-dasharray="4,4" stroke-width="2"/>
        </g>
      `;
      this.container.querySelector("#corridorLayer").innerHTML = corrHtml;
    }

    // 4. Stairwells (Staircase A & B)
    if (this.layers.stairwells) {
      let stairHtml = `<g id="stairwellsGroup">`;
      this.model.stairwells.forEach(stair => {
        const stairNodeId = `${stair.id}_${this.currentFloor}`;
        const isEngulfed = this.blockedNodes.has(stairNodeId);

        stairHtml += `
          <g class="stairwell-node" style="cursor:pointer;" data-id="${stair.id}" data-node="${stairNodeId}">
            <rect x="${stair.bounds.x}" y="${stair.bounds.y}" width="${stair.bounds.width}" height="${stair.bounds.height}"
                  rx="6" fill="${isEngulfed ? '#ef4444' : 'url(#stairTreads)'}" stroke="${isEngulfed ? '#dc2626' : '#f59e0b'}" stroke-width="${isEngulfed ? 4 : 2.5}"/>
            <rect x="${stair.bounds.x + 8}" y="${stair.bounds.y + 8}" width="${stair.bounds.width - 16}" height="24" rx="4"
                  fill="rgba(15, 23, 42, 0.85)"/>
            <text x="${stair.bounds.x + stair.bounds.width / 2}" y="${stair.bounds.y + 24}"
                  fill="${isEngulfed ? '#fca5a5' : '#fbbf24'}" font-size="11" font-weight="bold" text-anchor="middle">
              ${isEngulfed ? '⚠ COMPROMISED' : (stair.id === "STAIR_A" ? "STAIRCASE A (WEST)" : "STAIRCASE B (EAST)")}
            </text>
            <text x="${stair.bounds.x + stair.bounds.width / 2}" y="${stair.bounds.y + 54}"
                  fill="${isEngulfed ? '#ffffff' : '#78350f'}" font-size="12" font-weight="900" text-anchor="middle">
              ▲▼ LEVEL ${this.currentFloor} / 4
            </text>
            <text x="${stair.bounds.x + stair.bounds.width / 2}" y="${stair.bounds.y + 74}"
                  fill="${isEngulfed ? '#fee2e2' : '#92400e'}" font-size="9" font-weight="bold" text-anchor="middle">
              ${isEngulfed ? 'FIRE BLOCKAGE' : 'FIRE EGRESS CORE'}
            </text>
            <circle cx="${stair.connector.x}" cy="${stair.connector.y}" r="6" fill="${isEngulfed ? '#dc2626' : '#f59e0b'}" stroke="#ffffff" stroke-width="2"/>
          </g>
        `;
      });
      stairHtml += `</g>`;
      this.container.querySelector("#stairwellsLayer").innerHTML = stairHtml;

      this.container.querySelectorAll(".stairwell-node").forEach(elem => {
        const id = elem.getAttribute("data-id");
        const stair = this.model.stairwells.find(s => s.id === id);
        elem.addEventListener("mouseenter", (e) => {
          this.showTooltip(e, `
            <div style="font-weight:bold; color:#fbbf24;">${stair.name}</div>
            <div style="font-size:11px; color:#cbd5e1; margin-top:2px;">${stair.desc}</div>
            <div style="font-size:10px; color:#94a3b8; margin-top:4px;">Vertical link: Floors 0 to 4 (descent travel cost calibrated)</div>
          `);
        });
        elem.addEventListener("mouseleave", () => this.hideTooltip());
      });
    }

    // 5. Rooms & Spaces
    if (this.layers.rooms) {
      let roomsHtml = `<g id="roomsGroup">`;
      floor.rooms.forEach(r => {
        const roomNodeId = `NODE_${r.id}`;
        const isStart = this.startNode === roomNodeId;

        const typeColors = {
          office: { fill: "#1e293b", border: "#64748b", text: "#e2e8f0" },
          classroom: { fill: "#1e293b", border: "#64748b", text: "#e2e8f0" },
          lab: { fill: "#1e293b", border: "#0284c7", text: "#38bdf8" },
          server: { fill: "#1e293b", border: "#f59e0b", text: "#fbbf24" },
          medical: { fill: "#1e293b", border: "#ef4444", text: "#fca5a5" },
          lobby: { fill: "#1e293b", border: "#3b82f6", text: "#93c5fd" },
          auditorium: { fill: "#1e293b", border: "#8b5cf6", text: "#c4b5fd" },
          library: { fill: "#1e293b", border: "#10b981", text: "#6ee7b7" },
          executive: { fill: "#1e293b", border: "#ec4899", text: "#f472b6" }
        };
        const conf = typeColors[r.type] || { fill: "#1e293b", border: "#64748b", text: "#e2e8f0" };
        const rw = (r.w !== undefined ? r.w : r.width) || 100;
        const rh = (r.h !== undefined ? r.h : r.height) || 60;

        roomsHtml += `
          <g class="room-element" data-id="${r.id}" data-node="${roomNodeId}" style="cursor:pointer;">
            <rect x="${r.x}" y="${r.y}" width="${rw}" height="${rh}" rx="6"
                  fill="${isStart ? 'rgba(37, 99, 235, 0.3)' : conf.fill}"
                  stroke="${isStart ? '#38bdf8' : conf.border}"
                  stroke-width="${isStart ? 3 : 1.8}"/>
            <circle cx="${r.door.x}" cy="${r.door.y}" r="4" fill="#38bdf8" stroke="#ffffff" stroke-width="1.5"/>
            <rect x="${r.x + 8}" y="${r.y + 8}" width="50" height="18" rx="3" fill="rgba(15, 23, 42, 0.7)"/>
            <text x="${r.x + 33}" y="${r.y + 21}" fill="${conf.text}" font-size="10" font-weight="bold" text-anchor="middle">${r.code}</text>
            
            ${this.layers.labels ? `
              <text x="${r.x + rw / 2}" y="${r.y + rh / 2 + 5}" fill="#f1f5f9"
                    font-size="${rw > 200 ? 13 : 11}" font-weight="600" text-anchor="middle"
                    style="pointer-events:none;">
                ${r.name}
              </text>
            ` : ''}
          </g>
        `;
      });
      roomsHtml += `</g>`;
      this.container.querySelector("#roomsLayer").innerHTML = roomsHtml;

      this.container.querySelectorAll(".room-element").forEach(elem => {
        const id = elem.getAttribute("data-id");
        const room = floor.rooms.find(r => r.id === id);
        elem.addEventListener("mouseenter", (e) => {
          this.showTooltip(e, `
            <div style="font-weight:bold; color:#38bdf8;">[${room.code}] ${room.name}</div>
            <div style="font-size:11px; color:#cbd5e1; margin-top:2px;">Category: ${room.type.toUpperCase()}</div>
            <div style="font-size:10px; color:#94a3b8; margin-top:2px;">Click to set as START evacuation location</div>
          `);
        });
        elem.addEventListener("mouseleave", () => this.hideTooltip());
        elem.addEventListener("click", () => {
          if (this.onRoomClick) this.onRoomClick(room, floor);
        });
      });
    }

    // 6. Exits (Ground Floor only)
    if (this.layers.exits && floor.exits && floor.exits.length > 0) {
      let exitsHtml = `<g id="exitsGroup">`;
      floor.exits.forEach(ex => {
        const exitNodeId = `NODE_${ex.id}`;
        const isBlocked = this.blockedNodes.has(exitNodeId);

        exitsHtml += `
          <g class="exit-marker" data-id="${ex.id}" data-node="${exitNodeId}" style="cursor:pointer;" filter="${isBlocked ? 'url(#redGlow)' : 'url(#greenGlow)'}">
            <rect x="${ex.x}" y="${ex.y}" width="${ex.w}" height="${ex.h}" rx="5"
                  fill="${isBlocked ? '#dc2626' : '#16a34a'}" stroke="#ffffff" stroke-width="2"/>
            <text x="${ex.x + ex.w / 2}" y="${ex.y + ex.h / 2 + 4}"
                  fill="#ffffff" font-size="10" font-weight="900" text-anchor="middle" letter-spacing="1">
              ${isBlocked ? 'BLOCKED' : ex.label}
            </text>
            <circle cx="${ex.node.x}" cy="${ex.node.y}" r="8" fill="${isBlocked ? '#dc2626' : '#22c55e'}" stroke="#ffffff" stroke-width="2">
              <animate attributeName="r" values="7;11;7" dur="1.5s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="1;0.4;1" dur="1.5s" repeatCount="indefinite"/>
            </circle>
          </g>
        `;
      });
      exitsHtml += `</g>`;
      this.container.querySelector("#exitsLayer").innerHTML = exitsHtml;
    }

    // 7. Graph Topology Layer (V & E)
    if (this.layers.graph && this.graphData) {
      let gHtml = `<g id="debugGraphGroup" opacity="0.6">`;
      // Render Edges on this floor
      this.graphData.edges.forEach(e => {
        const u = this.graphData.nodes[e.from];
        const v = this.graphData.nodes[e.to];
        if (u && v && u.floor === this.currentFloor && v.floor === this.currentFloor) {
          const isBlocked = this.blockedEdges.has(`${e.from}--${e.to}`) || this.blockedEdges.has(`${e.to}--${e.from}`);
          gHtml += `
            <line x1="${u.x}" y1="${u.y}" x2="${v.x}" y2="${v.y}"
                  stroke="${isBlocked ? '#dc2626' : '#60a5fa'}" stroke-width="${isBlocked ? 3 : 1.5}"
                  stroke-dasharray="${isBlocked ? '4,4' : 'none'}"/>
          `;
        }
      });
      // Render Nodes on this floor
      for (const nid in this.graphData.nodes) {
        const n = this.graphData.nodes[nid];
        if (n.floor === this.currentFloor) {
          const isBlocked = this.blockedNodes.has(nid);
          gHtml += `
            <circle cx="${n.x}" cy="${n.y}" r="4" fill="${isBlocked ? '#dc2626' : '#38bdf8'}" stroke="#ffffff" stroke-width="1"/>
          `;
        }
      }
      gHtml += `</g>`;
      this.container.querySelector("#graphLayer").innerHTML = gHtml;
    }

    // 7B. Stationary QR Positioning Markers Layer (All 25 Checkpoints across Floors 0-4)
    if (this.layers.qr !== false && this.qrCodes && this.qrCodes.length > 0) {
      const qrLayer = this.container.querySelector("#qrMarkersLayer");
      if (qrLayer) {
        let qrHtml = `<g id="qrMarkersGroup" filter="url(#cyanGlow)">`;
        const fallbackCoords = {
          "NODE_LOBBY_SOUTH": { x: 600, y: 520 },
          "NODE_ROOM_G_01": { x: 180, y: 220 },
          "NODE_ROOM_G_02": { x: 180, y: 310 },
          "NODE_ROOM_G_03": { x: 180, y: 440 },
          "NODE_ROOM_G_06": { x: 1020, y: 440 },
          "NODE_ROOM_1_01": { x: 180, y: 220 },
          "NODE_ROOM_1_06": { x: 1020, y: 220 },
          "NODE_ROOM_1_07": { x: 1020, y: 310 },
          "N1_C_CENTER": { x: 600, y: 370 },
          "STAIR_A_1": { x: 380, y: 220 },
          "NODE_ROOM_2_01": { x: 180, y: 220 },
          "NODE_ROOM_2_06": { x: 1020, y: 220 },
          "N2_C_CENTER": { x: 600, y: 370 },
          "STAIR_A_2": { x: 380, y: 220 },
          "STAIR_B_2": { x: 820, y: 220 },
          "NODE_ROOM_3_01": { x: 180, y: 220 },
          "NODE_ROOM_3_05": { x: 600, y: 320 },
          "NODE_ROOM_3_06": { x: 1020, y: 220 },
          "STAIR_A_3": { x: 380, y: 220 },
          "STAIR_B_3": { x: 820, y: 220 },
          "NODE_ROOM_4_01": { x: 180, y: 220 },
          "NODE_ROOM_4_06": { x: 1020, y: 220 },
          "N4_C_CENTER": { x: 600, y: 370 },
          "STAIR_A_4": { x: 380, y: 220 },
          "STAIR_B_4": { x: 820, y: 220 }
        };

        this.qrCodes.forEach(q => {
          if (parseInt(q.floor_id, 10) === this.currentFloor) {
            let qx = 600, qy = 370;
            if (this.graphData && this.graphData.nodes && this.graphData.nodes[q.node_id]) {
              qx = this.graphData.nodes[q.node_id].x;
              qy = this.graphData.nodes[q.node_id].y;
            } else if (fallbackCoords[q.node_id]) {
              qx = fallbackCoords[q.node_id].x;
              qy = fallbackCoords[q.node_id].y;
            }

            qrHtml += `
              <g class="qr-marker-badge" data-code="${q.code_id}" data-node="${q.node_id}" style="cursor:pointer;">
                <!-- Pulsing Outer Cyan Wave Ring -->
                <circle cx="${qx}" cy="${qy}" r="15" fill="rgba(6, 182, 212, 0.18)" stroke="#06b6d4" stroke-width="1.5">
                  <animate attributeName="r" values="11;18;11" dur="2s" repeatCount="indefinite"/>
                  <animate attributeName="opacity" values="0.8;0.2;0.8" dur="2s" repeatCount="indefinite"/>
                </circle>

                <!-- High-Tech Square QR Badge -->
                <rect x="${qx - 11}" y="${qy - 11}" width="22" height="22" rx="4"
                      fill="#090d16" stroke="#06b6d4" stroke-width="2"/>

                <!-- Micro QR Matrix Finder Patterns -->
                <rect x="${qx - 8}" y="${qy - 8}" width="6" height="6" fill="#38bdf8"/>
                <rect x="${qx - 6}" y="${qy - 6}" width="2" height="2" fill="#090d16"/>
                <rect x="${qx + 2}" y="${qy - 8}" width="6" height="6" fill="#38bdf8"/>
                <rect x="${qx + 4}" y="${qy - 6}" width="2" height="2" fill="#090d16"/>
                <rect x="${qx - 8}" y="${qy + 2}" width="6" height="6" fill="#38bdf8"/>
                <rect x="${qx - 6}" y="${qy + 4}" width="2" height="2" fill="#090d16"/>
                <rect x="${qx + 3}" y="${qy + 3}" width="4" height="4" fill="#38bdf8"/>

                <!-- Label Chip Tag Below Marker -->
                <rect x="${qx - 45}" y="${qy + 14}" width="90" height="15" rx="3"
                      fill="rgba(15, 23, 42, 0.95)" stroke="#06b6d4" stroke-width="1"/>
                <text x="${qx}" y="${qy + 25}" fill="#67e8f9" font-size="8.5" font-weight="800" text-anchor="middle" letter-spacing="0.4">
                  QR: ${(q.location_label || q.code_id).substring(0, 14)}
                </text>
              </g>
            `;
          }
        });
        qrHtml += `</g>`;
        qrLayer.innerHTML = qrHtml;

        // Tooltip & Click Handlers on QR Markers
        this.container.querySelectorAll(".qr-marker-badge").forEach(elem => {
          const codeId = elem.getAttribute("data-code");
          const q = this.qrCodes.find(item => item.code_id === codeId);
          if (q) {
            elem.addEventListener("mouseenter", (e) => {
              this.showTooltip(e, `
                <div style="font-weight:bold; color:#38bdf8; display:flex; align-items:center; gap:5px;">
                  <span>📷 PHYSICAL QR CHECKPOINT</span>
                </div>
                <div style="font-size:12px; font-weight:800; color:#f8fafc; margin-top:3px;">${q.location_label}</div>
                <div style="font-size:10.5px; color:#94a3b8; margin-top:2px;">Payload: <code style="color:#67e8f9; background:rgba(6,182,212,0.15); padding:1px 4px; border-radius:3px;">${q.code_id}</code> • Floor ${q.floor_id}</div>
                <div style="font-size:10px; color:#cbd5e1; margin-top:3px;">${q.description || 'Stationary wall marker'}</div>
                <div style="font-size:9.5px; color:#4ade80; font-weight:bold; margin-top:5px;">⚡ Click marker to select & update route</div>
              `);
            });
            elem.addEventListener("mouseleave", () => this.hideTooltip());
            elem.addEventListener("click", () => {
              if (this.onQrClick) this.onQrClick(q);
            });
          }
        });
      }
    }

    // 8. Hazard Markers Layer (Vivid Red #dc2626)
    if (this.layers.hazards) {
      let hazHtml = `<g id="hazardOverlays" filter="url(#redGlow)">`;
      // Blocked edges on this floor
      if (this.graphData) {
        this.blockedEdges.forEach(eStr => {
          const parts = eStr.split("--");
          if (parts.length === 2) {
            const u = this.graphData.nodes[parts[0]];
            const v = this.graphData.nodes[parts[1]];
            if (u && v && u.floor === this.currentFloor && v.floor === this.currentFloor) {
              hazHtml += `
                <line x1="${u.x}" y1="${u.y}" x2="${v.x}" y2="${v.y}"
                      stroke="#dc2626" stroke-width="8" stroke-linecap="round"/>
                <line x1="${u.x}" y1="${u.y}" x2="${v.x}" y2="${v.y}"
                      stroke="#fbbf24" stroke-width="4" stroke-dasharray="6,6" stroke-linecap="round"/>
                <circle cx="${(u.x + v.x)/2}" cy="${(u.y + v.y)/2}" r="12" fill="#dc2626" stroke="#ffffff" stroke-width="2"/>
                <text x="${(u.x + v.x)/2}" y="${(u.y + v.y)/2 + 4}" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">✕</text>
              `;
            }
          }
        });

        // Blocked nodes on this floor
        this.blockedNodes.forEach(nid => {
          const n = this.graphData.nodes[nid];
          if (n && n.floor === this.currentFloor) {
            hazHtml += `
              <g class="hazard-node-marker">
                <circle cx="${n.x}" cy="${n.y}" r="16" fill="rgba(220, 38, 38, 0.4)" stroke="#dc2626" stroke-width="3">
                  <animate attributeName="r" values="14;22;14" dur="1.2s" repeatCount="indefinite"/>
                  <animate attributeName="opacity" values="0.9;0.3;0.9" dur="1.2s" repeatCount="indefinite"/>
                </circle>
                <circle cx="${n.x}" cy="${n.y}" r="8" fill="#dc2626" stroke="#ffffff" stroke-width="2"/>
                <text x="${n.x}" y="${n.y + 4}" fill="#ffffff" font-size="9" font-weight="900" text-anchor="middle">🔥</text>
              </g>
            `;
          }
        });
      }

      // 8B. Render all point-and-click placed hazards on current floor
      if (this.rawHazards && this.rawHazards.length > 0) {
        this.rawHazards.forEach(h => {
          if (parseInt(h.floor_id, 10) === this.currentFloor) {
            const rad = parseFloat(h.radius) || 45;
            const hx = parseFloat(h.location_x);
            const hy = parseFloat(h.location_y);
            const type = (h.type || "fire").toLowerCase();

            if (type.includes("smoke")) {
              // Dense Smoke Hazard
              hazHtml += `
                <g class="hazard-placed-marker" data-id="${h.id || ''}" style="cursor:pointer;">
                  <circle cx="${hx}" cy="${hy}" r="${rad}" fill="rgba(100, 116, 139, 0.45)" stroke="#64748b" stroke-dasharray="4,4" stroke-width="2">
                    <animate attributeName="r" values="${rad * 0.9};${rad * 1.1};${rad * 0.9}" dur="2s" repeatCount="indefinite"/>
                  </circle>
                  <circle cx="${hx}" cy="${hy}" r="15" fill="#334155" stroke="#f8fafc" stroke-width="2"/>
                  <text x="${hx}" y="${hy + 5}" fill="#ffffff" font-size="12" text-anchor="middle">💨</text>
                </g>
              `;
            } else if (type.includes("barri") || type.includes("block")) {
              // Barricade Obstacle
              hazHtml += `
                <g class="hazard-placed-marker" data-id="${h.id || ''}" style="cursor:pointer;">
                  <circle cx="${hx}" cy="${hy}" r="${rad * 0.75}" fill="rgba(217, 119, 6, 0.35)" stroke="#d97706" stroke-width="2.5"/>
                  <rect x="${hx - 15}" y="${hy - 12}" width="30" height="24" rx="4" fill="#d97706" stroke="#ffffff" stroke-width="1.5"/>
                  <text x="${hx}" y="${hy + 5}" fill="#ffffff" font-size="13" text-anchor="middle">🚧</text>
                </g>
              `;
            } else {
              // Fire Hazard
              hazHtml += `
                <g class="hazard-placed-marker" data-id="${h.id || ''}" style="cursor:pointer;">
                  <circle cx="${hx}" cy="${hy}" r="${rad}" fill="rgba(220, 38, 38, 0.35)" stroke="#dc2626" stroke-width="3">
                    <animate attributeName="r" values="${rad * 0.85};${rad * 1.15};${rad * 0.85}" dur="1s" repeatCount="indefinite"/>
                    <animate attributeName="opacity" values="0.8;0.3;0.8" dur="1s" repeatCount="indefinite"/>
                  </circle>
                  <circle cx="${hx}" cy="${hy}" r="15" fill="#dc2626" stroke="#ffffff" stroke-width="2"/>
                  <text x="${hx}" y="${hy + 5}" fill="#ffffff" font-size="12" text-anchor="middle">🔥</text>
                </g>
              `;
            }
          }
        });
      }
      hazHtml += `</g>`;
      this.container.querySelector("#hazardLayer").innerHTML = hazHtml;
    }

    // 9. Safe Evacuation Path Layer (Bright Green #16a34a)
    if (this.layers.path && this.activePathNodes && this.activePathNodes.length > 1 && this.graphData) {
      let pathHtml = `<g id="dynamicPathGroup" filter="url(#greenGlow)">`;
      const ptsOnFloor = [];

      // Extract contiguous segments that belong to this floor
      for (let i = 0; i < this.activePathNodes.length - 1; i++) {
        const uId = this.activePathNodes[i];
        const vId = this.activePathNodes[i + 1];
        const u = this.graphData.nodes[uId];
        const v = this.graphData.nodes[vId];

        if (u && v) {
          // If both nodes are on current floor, draw the path line
          if (u.floor === this.currentFloor && v.floor === this.currentFloor) {
            pathHtml += `
              <line x1="${u.x}" y1="${u.y}" x2="${v.x}" y2="${v.y}"
                    stroke="#16a34a" stroke-width="7" stroke-linecap="round"/>
              <line x1="${u.x}" y1="${u.y}" x2="${v.x}" y2="${v.y}"
                    stroke="#4ade80" stroke-width="3.5" stroke-linecap="round"
                    stroke-dasharray="10, 8">
                <animate attributeName="stroke-dashoffset" values="36;0" dur="0.9s" repeatCount="indefinite"/>
              </line>
            `;
          }

          // If vertical descent occurs at this step
          if (u.floor === this.currentFloor && v.floor !== this.currentFloor) {
            // Occupant enters staircase to descend
            pathHtml += `
              <g class="stair-descent-beacon">
                <circle cx="${u.x}" cy="${u.y}" r="14" fill="#22c55e" stroke="#ffffff" stroke-width="3"/>
                <text x="${u.x}" y="${u.y + 5}" fill="#0f172a" font-size="12" font-weight="900" text-anchor="middle">↓</text>
                <rect x="${u.x - 55}" y="${u.y + 18}" width="110" height="20" rx="4" fill="rgba(15, 23, 42, 0.9)" stroke="#16a34a" stroke-width="1.5"/>
                <text x="${u.x}" y="${u.y + 32}" fill="#4ade80" font-size="10" font-weight="bold" text-anchor="middle">DESCEND TO L${v.floor}</text>
              </g>
            `;
          } else if (u.floor !== this.currentFloor && v.floor === this.currentFloor) {
            // Occupant arrives on this floor from staircase
            pathHtml += `
              <g class="stair-arrival-beacon">
                <circle cx="${v.x}" cy="${v.y}" r="12" fill="#22c55e" stroke="#ffffff" stroke-width="2"/>
                <rect x="${v.x - 55}" y="${v.y - 25}" width="110" height="20" rx="4" fill="rgba(15, 23, 42, 0.9)" stroke="#16a34a" stroke-width="1.5"/>
                <text x="${v.x}" y="${v.y - 11}" fill="#4ade80" font-size="10" font-weight="bold" text-anchor="middle">ARRIVED ON L${v.floor}</text>
              </g>
            `;
          }
        }
      }

      // Draw path waypoint nodes on this floor
      this.activePathNodes.forEach((nid, idx) => {
        const n = this.graphData.nodes[nid];
        if (n && n.floor === this.currentFloor) {
          pathHtml += `
            <circle cx="${n.x}" cy="${n.y}" r="5" fill="#22c55e" stroke="#ffffff" stroke-width="2"/>
          `;
        }
      });

      pathHtml += `</g>`;
      this.container.querySelector("#pathLayer").innerHTML = pathHtml;
    }

    // 10. User Current Position or Safely Evacuated Marker
    const markerLayer = this.container.querySelector("#userMarkerLayer");
    if (markerLayer) {
      if (this.isEvacuated) {
        if (this.currentFloor === 0) {
          const isNorth = (this.evacuatedExitId === "NODE_EXIT_G_WEST" || this.evacuatedExitId === "EXIT_G_WEST");
          const ax = 600;
          const ay = isNorth ? 45 : 715;
          const targetLabel = isNorth ? "ASSEMBLY POINT 2 (NORTH SPORTS GROUND)" : "ASSEMBLY POINT 1 (SOUTH LAWN)";

          markerLayer.innerHTML = `
            <g id="evacuatedBeacon" filter="url(#greenGlow)">
              <circle cx="${ax}" cy="${ay}" r="32" fill="rgba(22, 163, 74, 0.25)" stroke="#22c55e" stroke-width="2.5">
                <animate attributeName="r" values="22;42;22" dur="1.8s" repeatCount="indefinite"/>
                <animate attributeName="opacity" values="0.9;0.15;0.9" dur="1.8s" repeatCount="indefinite"/>
              </circle>
              <circle cx="${ax}" cy="${ay}" r="14" fill="#16a34a" stroke="#ffffff" stroke-width="3"/>
              <text x="${ax}" y="${ay + 5}" font-size="13" text-anchor="middle">🛡️</text>
              <rect x="${ax - 105}" y="${ay - 44}" width="210" height="28" rx="6"
                    fill="rgba(15, 23, 42, 0.95)" stroke="#22c55e" stroke-width="2"/>
              <text x="${ax}" y="${ay - 26}" fill="#4ade80" font-size="11" font-weight="900" text-anchor="middle">
                ✓ YOU ARE SAFELY OUTSIDE
              </text>
              <rect x="${ax - 120}" y="${ay + 22}" width="240" height="20" rx="4"
                    fill="rgba(15, 23, 42, 0.9)" stroke="#16a34a" stroke-width="1"/>
              <text x="${ax}" y="${ay + 36}" fill="#a7f3d0" font-size="9" font-weight="700" text-anchor="middle">
                ${targetLabel}
              </text>
            </g>
          `;
        } else {
          markerLayer.innerHTML = "";
        }
      } else if (this.startNode && this.graphData && this.graphData.nodes[this.startNode]) {
        const startN = this.graphData.nodes[this.startNode];
        if (startN.floor === this.currentFloor) {
          markerLayer.innerHTML = `
            <g id="userBeacon" filter="url(#blueGlow)">
              <circle cx="${startN.x}" cy="${startN.y}" r="22" fill="rgba(37, 99, 235, 0.25)" stroke="#38bdf8" stroke-width="2">
                <animate attributeName="r" values="16;32;16" dur="2s" repeatCount="indefinite"/>
                <animate attributeName="opacity" values="0.8;0.1;0.8" dur="2s" repeatCount="indefinite"/>
              </circle>
              <circle cx="${startN.x}" cy="${startN.y}" r="9" fill="#2563eb" stroke="#ffffff" stroke-width="2.5"/>
              <rect x="${startN.x - 65}" y="${startN.y - 30}" width="130" height="22" rx="4"
                    fill="rgba(15, 23, 42, 0.95)" stroke="#38bdf8" stroke-width="1.5"/>
              <text x="${startN.x}" y="${startN.y - 15}" fill="#38bdf8" font-size="10" font-weight="900" text-anchor="middle">
                YOU ARE HERE
              </text>
            </g>
          `;
        } else {
          markerLayer.innerHTML = "";
        }
      } else {
        markerLayer.innerHTML = "";
      }
    }

    // 11. Live Simulation Drill Occupants Layer
    this.renderSimulationLayer();

    this.updateTransform();
  }

  setSimulationOccupants(occupants) {
    this.simOccupants = occupants || [];
    this.renderSimulationLayer();
  }

  renderSimulationLayer() {
    const simGroup = this.container.querySelector("#simulationLayer");
    if (!simGroup) return;

    if (!this.simOccupants || this.simOccupants.length === 0) {
      simGroup.innerHTML = "";
      return;
    }

    let html = `<g id="simOccupantsGroup" filter="url(#blueGlow)">`;
    let safeCount = 0;
    this.simOccupants.forEach(occ => {
      if (occ.floor === this.currentFloor && occ.status === "inside") {
        const color = occ.isRerouting ? "#f59e0b" : (occ.color || "#38bdf8");
        html += `
          <g class="sim-occupant" transform="translate(${Math.round(occ.x)}, ${Math.round(occ.y)})">
            <circle r="14" fill="none" stroke="${color}" stroke-width="1.5" opacity="0.4">
              <animate attributeName="r" values="9;18;9" dur="1.2s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="0.6;0.1;0.6" dur="1.2s" repeatCount="indefinite"/>
            </circle>
            <circle r="7" fill="${color}" stroke="#ffffff" stroke-width="2"/>
            <rect x="-24" y="-22" width="48" height="13" rx="3" fill="rgba(15, 23, 42, 0.9)" stroke="${color}" stroke-width="1"/>
            <text x="0" y="-12" fill="#ffffff" font-size="8" font-weight="bold" text-anchor="middle">${occ.id}</text>
            ${occ.isRerouting ? `<text x="0" y="18" fill="#f59e0b" font-size="8" font-weight="bold" text-anchor="middle">REROUTE</text>` : ''}
          </g>
        `;
      } else if (this.currentFloor === 0 && (occ.status === "safe" || occ.status === "evacuated")) {
        // Draw safely evacuated occupants at outdoor assembly lawn (clustered around x=600, y=715)
        safeCount++;
        const clusterOffset = (safeCount % 8) * 16 - 56;
        const clusterRow = Math.floor(safeCount / 8) * 16;
        const sx = 600 + clusterOffset;
        const sy = 745 + clusterRow;
        html += `
          <g class="sim-occupant-safe" transform="translate(${sx}, ${sy})">
            <circle r="5" fill="#16a34a" stroke="#ffffff" stroke-width="1"/>
            <text x="0" y="2.5" fill="#ffffff" font-size="6" font-weight="bold" text-anchor="middle">✓</text>
          </g>
        `;
      }
    });
    html += `</g>`;
    simGroup.innerHTML = html;
  }
}

if (typeof window !== "undefined") {
  window.FloorMapRenderer = FloorMapRenderer;
}
