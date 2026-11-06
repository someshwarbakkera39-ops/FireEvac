/**
 * QR Indoor Positioning Scanner
 * Supports live camera stream decoding & simulated QR checkpoint resolution.
 */

class QRPositioningScanner {
  constructor(options = {}) {
    this.onPositionResolved = options.onPositionResolved || null;
    this.videoElement = null;
    this.stream = null;
    this.isScanning = false;
  }

  async resolveCodeId(codeId) {
    try {
      const resp = await fetch(`/api/qr/${codeId}`);
      const data = await resp.json();
      if (data.status === "success" && this.onPositionResolved) {
        this.onPositionResolved(data);
        return data;
      }
      return data;
    } catch (e) {
      // Offline fallback lookup
      const fallbackQR = {
        "QR_3_AILAB": { floor: 3, node_id: "NODE_ROOM_3_05", coordinates: { x: 890, y: 290 }, qr: { location_label: "AI Lab 305", node_name: "[305] AI & Robotics Lab" } },
        "QR_4_AUDITORIUM": { floor: 4, node_id: "NODE_ROOM_4_06", coordinates: { x: 890, y: 390 }, qr: { location_label: "Grand Auditorium", node_name: "[406] Grand Auditorium" } },
        "QR_2_LECTURE": { floor: 2, node_id: "NODE_ROOM_2_01", coordinates: { x: 250, y: 290 }, qr: { location_label: "Lecture Hall 201", node_name: "[201] Smart Lecture Hall" } },
        "QR_1_FACULTY": { floor: 1, node_id: "NODE_ROOM_1_01", coordinates: { x: 250, y: 290 }, qr: { location_label: "Faculty Dept 101", node_name: "[101] Faculty Dept Office" } },
        "QR_G_ATRIUM": { floor: 0, node_id: "NODE_LOBBY_SOUTH", coordinates: { x: 600, y: 480 }, qr: { location_label: "Central Atrium", node_name: "Ground Floor Atrium Portal" } }
      };

      if (fallbackQR[codeId] && this.onPositionResolved) {
        const res = { status: "success", ...fallbackQR[codeId] };
        this.onPositionResolved(res);
        return res;
      }
      return { status: "error", message: "QR resolution failed" };
    }
  }

  async startCamera(videoElementId) {
    this.videoElement = document.getElementById(videoElementId);
    if (!this.videoElement) return false;

    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        this.stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" }
        });
        this.videoElement.srcObject = this.stream;
        this.videoElement.setAttribute("playsinline", true);
        await this.videoElement.play();
        this.isScanning = true;
        return true;
      }
    } catch (err) {
      console.warn("Camera access unavailable, using QR checkpoint selection fallback:", err);
      return false;
    }
    return false;
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.isScanning = false;
  }
}

if (typeof window !== "undefined") {
  window.QRPositioningScanner = QRPositioningScanner;
}

