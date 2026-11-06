/**
 * Outdoor GPS Positioning & Assembly Grounds Handoff Engine
 * HTML5 / W3C Geolocation API Implementation (Blueprint Section 8)
 */

class GPSAssemblyHandoff {
  constructor(options = {}) {
    this.assemblyPoints = [
      {
        id: "ASSEMBLY_SOUTH",
        name: "Primary Safe Assembly Point 1 (South Lawn)",
        lat: 12.9716,
        lng: 77.5946,
        desc: "Open lawn clearing south of Block A main entrance."
      },
      {
        id: "ASSEMBLY_NORTH",
        name: "Secondary Safe Muster Point 2 (North Sports Ground)",
        lat: 12.9725,
        lng: 77.5946,
        desc: "Athletics complex and outdoor basketball pavilion."
      }
    ];

    this.onPositionUpdate = options.onPositionUpdate || null;
    this.watchId = null;
    this.isSimulating = false;
    this.simInterval = null;
    this.simStep = 0;
    this.forceSimulation = false;

    // Waypoints for smooth walking simulation from South Exit to Assembly Point 1
    this.simulatedPath = [
      { lat: 12.97120, lng: 77.59440, msg: "Stepped outside Main South Exit onto perimeter walkway." },
      { lat: 12.97130, lng: 77.59445, msg: "Passing exterior covered colonnade heading South." },
      { lat: 12.97142, lng: 77.59450, msg: "Approaching South Lawn safety perimeter rope." },
      { lat: 12.97152, lng: 77.59456, msg: "Entering designated Muster Clearing 1." },
      { lat: 12.97160, lng: 77.59460, msg: "Arrived at Primary Safe Assembly Point 1 (South Lawn). Safety Check-in Confirmed!" }
    ];
  }

  // Haversine formula for physical distance (meters)
  calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // Earth radius in meters
    const dLat = (lat2 - lat1) * (Math.PI / 180);
    const dLon = (lon2 - lon1) * (Math.PI / 180);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return Math.round(R * c);
  }

  // Compass bearing in degrees (0 = North, 90 = East, 180 = South, 270 = West)
  calculateBearing(lat1, lon1, lat2, lon2) {
    const dLon = (lon2 - lon1) * (Math.PI / 180);
    const y = Math.sin(dLon) * Math.cos(lat2 * (Math.PI / 180));
    const x =
      Math.cos(lat1 * (Math.PI / 180)) * Math.sin(lat2 * (Math.PI / 180)) -
      Math.sin(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) * Math.cos(dLon);
    let brng = Math.atan2(y, x) * (180 / Math.PI);
    return Math.round((brng + 360) % 360);
  }

  getCompassDirection(bearing) {
    const directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    return directions[Math.round(bearing / 45) % 8];
  }

  findNearestAssembly(userLat, userLng) {
    let nearest = null;
    let minDist = Infinity;

    this.assemblyPoints.forEach(p => {
      const dist = this.calculateDistance(userLat, userLng, p.lat, p.lng);
      if (dist < minDist) {
        minDist = dist;
        nearest = { ...p, distanceMeters: dist, bearing: this.calculateBearing(userLat, userLng, p.lat, p.lng) };
      }
    });

    return nearest;
  }

  startSimulation() {
    this.stopTracking();
    this.isSimulating = true;
    this.simStep = 0;

    const emitSimStep = () => {
      const point = this.simulatedPath[this.simStep];
      const nearest = this.findNearestAssembly(point.lat, point.lng);
      const isArrived = this.simStep >= this.simulatedPath.length - 1;

      if (this.onPositionUpdate) {
        this.onPositionUpdate({
          userLat: point.lat,
          userLng: point.lng,
          accuracy: 3,
          nearestAssembly: nearest,
          simulated: true,
          stepMessage: point.msg,
          arrived: isArrived
        });
      }

      if (this.simStep < this.simulatedPath.length - 1) {
        this.simStep++;
      }
    };

    emitSimStep();
    this.simInterval = setInterval(emitSimStep, 1500);
  }

  startTracking(forceSim = false) {
    this.stopTracking();

    if (forceSim || this.forceSimulation) {
      this.startSimulation();
      return true;
    }

    if (!navigator.geolocation) {
      this.startSimulation();
      return false;
    }

    this.watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const uLat = pos.coords.latitude;
        const uLng = pos.coords.longitude;
        const nearest = this.findNearestAssembly(uLat, uLng);

        // If coordinates are more than 10km from campus (testing away from campus site),
        // use interactive campus simulation so the outdoor handoff prototype works realistically
        if (nearest && nearest.distanceMeters > 5000) {
          console.info("Device GPS is away from campus site; activating interactive campus walk simulation.");
          this.startSimulation();
          return;
        }

        if (this.onPositionUpdate) {
          this.onPositionUpdate({
            userLat: uLat,
            userLng: uLng,
            accuracy: Math.round(pos.coords.accuracy),
            nearestAssembly: nearest,
            simulated: false,
            arrived: nearest ? nearest.distanceMeters <= 8 : false
          });
        }
      },
      (err) => {
        console.warn("Geolocation watch error or permission unavailable, switching to simulated walk:", err);
        this.startSimulation();
      },
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
    );
    return true;
  }

  stopTracking() {
    if (this.simInterval) {
      clearInterval(this.simInterval);
      this.simInterval = null;
    }
    this.isSimulating = false;

    if (this.watchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
  }
}

if (typeof window !== "undefined") {
  window.GPSAssemblyHandoff = GPSAssemblyHandoff;
}

