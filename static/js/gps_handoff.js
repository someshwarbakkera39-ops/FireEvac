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

  startTracking() {
    if (!navigator.geolocation) {
      // Simulated GPS position outside South Exit for desktop prototype testing
      const simLat = 12.9712;
      const simLng = 77.5944;
      const nearest = this.findNearestAssembly(simLat, simLng);
      if (this.onPositionUpdate) {
        this.onPositionUpdate({
          userLat: simLat,
          userLng: simLng,
          nearestAssembly: nearest,
          simulated: true
        });
      }
      return false;
    }

    this.watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const uLat = pos.coords.latitude;
        const uLng = pos.coords.longitude;
        const nearest = this.findNearestAssembly(uLat, uLng);
        if (this.onPositionUpdate) {
          this.onPositionUpdate({
            userLat: uLat,
            userLng: uLng,
            accuracy: Math.round(pos.coords.accuracy),
            nearestAssembly: nearest,
            simulated: false
          });
        }
      },
      (err) => {
        console.warn("Geolocation watch error, using simulation fallback:", err);
        const simLat = 12.9712;
        const simLng = 77.5944;
        const nearest = this.findNearestAssembly(simLat, simLng);
        if (this.onPositionUpdate) {
          this.onPositionUpdate({
            userLat: simLat,
            userLng: simLng,
            nearestAssembly: nearest,
            simulated: true
          });
        }
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    );
    return true;
  }

  stopTracking() {
    if (this.watchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
  }
}

if (typeof window !== "undefined") {
  window.GPSAssemblyHandoff = GPSAssemblyHandoff;
}

