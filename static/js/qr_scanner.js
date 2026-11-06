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
    this.animFrameId = null;
    this.barcodeDetector = null;
    this.canvas = typeof document !== "undefined" ? document.createElement("canvas") : null;
    this.canvasContext = this.canvas ? this.canvas.getContext("2d", { willReadFrequently: true }) : null;

    if (typeof window !== "undefined" && "BarcodeDetector" in window) {
      try {
        this.barcodeDetector = new BarcodeDetector({ formats: ["qr_code"] });
      } catch (e) {
        this.barcodeDetector = null;
      }
    }
  }

  /**
   * Resolves a QR code ID via API or offline fallback.
   */
  async resolveCodeId(codeId) {
    // Clean string (extract parameter if full URL was scanned)
    let cleanCode = codeId;
    if (typeof codeId === "string") {
      if (codeId.includes("?qr=")) {
        cleanCode = codeId.split("?qr=")[1].split("&")[0];
      } else if (codeId.includes("/qr/")) {
        cleanCode = codeId.split("/qr/")[1].split("?")[0];
      }
    }

    try {
      const resp = await fetch(`/api/qr/${cleanCode}`);
      const data = await resp.json();
      if (data.status === "success" && this.onPositionResolved) {
        this.onPositionResolved(data);
        return data;
      }
      return data;
    } catch (e) {
      // Offline fallback lookup for all 25 checkpoints
      const fallbackQR = {
        // Ground Floor
        "QR_G_ATRIUM": { floor: 0, node_id: "NODE_LOBBY_SOUTH", coordinates: { x: 600, y: 520 }, qr: { code_id: "QR_G_ATRIUM", location_label: "Central Atrium Portal", node_name: "Central Atrium Portal" } },
        "QR_G_ADMIN": { floor: 0, node_id: "NODE_ROOM_G_01", coordinates: { x: 180, y: 220 }, qr: { code_id: "QR_G_ADMIN", location_label: "Admin & Accounts G-101", node_name: "Admin Office G-101" } },
        "QR_G_CLINIC": { floor: 0, node_id: "NODE_ROOM_G_02", coordinates: { x: 180, y: 310 }, qr: { code_id: "QR_G_CLINIC", location_label: "First Aid Clinic G-102", node_name: "Medical Clinic G-102" } },
        "QR_G_CAFE": { floor: 0, node_id: "NODE_ROOM_G_06", coordinates: { x: 1020, y: 440 }, qr: { code_id: "QR_G_CAFE", location_label: "Cafeteria G-106", node_name: "Cafeteria Food Court G-106" } },
        "QR_G_SECURITY": { floor: 0, node_id: "NODE_ROOM_G_03", coordinates: { x: 180, y: 440 }, qr: { code_id: "QR_G_SECURITY", location_label: "Security Command G-103", node_name: "Security Command Center G-103" } },

        // Floor 1
        "QR_1_FACULTY": { floor: 1, node_id: "NODE_ROOM_1_01", coordinates: { x: 180, y: 220 }, qr: { code_id: "QR_1_FACULTY", location_label: "Faculty Dept 101", node_name: "Faculty Wing A 101" } },
        "QR_1_CSLAB": { floor: 1, node_id: "NODE_ROOM_1_06", coordinates: { x: 1020, y: 220 }, qr: { code_id: "QR_1_CSLAB", location_label: "CS Software Lab 106", node_name: "CS Software Lab 106" } },
        "QR_1_NETLAB": { floor: 1, node_id: "NODE_ROOM_1_07", coordinates: { x: 1020, y: 310 }, qr: { code_id: "QR_1_NETLAB", location_label: "Networks Lab 107", node_name: "Advanced Networks Lab 107" } },
        "QR_1_BRIDGE": { floor: 1, node_id: "N1_C_CENTER", coordinates: { x: 600, y: 370 }, qr: { code_id: "QR_1_BRIDGE", location_label: "Skybridge Center L1", node_name: "Skybridge Center L1" } },
        "QR_1_STAIR_A": { floor: 1, node_id: "STAIR_A_1", coordinates: { x: 380, y: 220 }, qr: { code_id: "QR_1_STAIR_A", location_label: "West Staircase A L1", node_name: "West Staircase A L1" } },

        // Floor 2
        "QR_2_LECTURE": { floor: 2, node_id: "NODE_ROOM_2_01", coordinates: { x: 180, y: 220 }, qr: { code_id: "QR_2_LECTURE", location_label: "Lecture Theater 201", node_name: "Smart Lecture Hall 201" } },
        "QR_2_SEMINAR": { floor: 2, node_id: "NODE_ROOM_2_06", coordinates: { x: 1020, y: 220 }, qr: { code_id: "QR_2_SEMINAR", location_label: "Seminar Hall 206", node_name: "Multipurpose Seminar Hall 206" } },
        "QR_2_BRIDGE": { floor: 2, node_id: "N2_C_CENTER", coordinates: { x: 600, y: 370 }, qr: { code_id: "QR_2_BRIDGE", location_label: "Skybridge Walkway L2", node_name: "Skybridge Walkway L2" } },
        "QR_2_STAIR_A": { floor: 2, node_id: "STAIR_A_2", coordinates: { x: 380, y: 220 }, qr: { code_id: "QR_2_STAIR_A", location_label: "West Staircase A L2", node_name: "West Staircase A L2" } },
        "QR_2_STAIR_B": { floor: 2, node_id: "STAIR_B_2", coordinates: { x: 820, y: 220 }, qr: { code_id: "QR_2_STAIR_B", location_label: "East Staircase B L2", node_name: "East Staircase B L2" } },

        // Floor 3
        "QR_3_LIBRARY": { floor: 3, node_id: "NODE_ROOM_3_01", coordinates: { x: 180, y: 220 }, qr: { code_id: "QR_3_LIBRARY", location_label: "Library Stacks 301", node_name: "Central Library 301" } },
        "QR_3_AILAB": { floor: 3, node_id: "NODE_ROOM_3_05", coordinates: { x: 600, y: 320 }, qr: { code_id: "QR_3_AILAB", location_label: "AI & Robotics Lab 305", node_name: "AI & Robotics Lab 305" } },
        "QR_3_HPC": { floor: 3, node_id: "NODE_ROOM_3_06", coordinates: { x: 1020, y: 220 }, qr: { code_id: "QR_3_HPC", location_label: "HPC Facility 306", node_name: "HPC Cluster 306" } },
        "QR_3_STAIR_A": { floor: 3, node_id: "STAIR_A_3", coordinates: { x: 380, y: 220 }, qr: { code_id: "QR_3_STAIR_A", location_label: "West Staircase A L3", node_name: "West Staircase A L3" } },
        "QR_3_STAIR_B": { floor: 3, node_id: "STAIR_B_3", coordinates: { x: 820, y: 220 }, qr: { code_id: "QR_3_STAIR_B", location_label: "East Staircase B L3", node_name: "East Staircase B L3" } },

        // Floor 4
        "QR_4_BOARDROOM": { floor: 4, node_id: "NODE_ROOM_4_01", coordinates: { x: 180, y: 220 }, qr: { code_id: "QR_4_BOARDROOM", location_label: "Boardroom 401", node_name: "Executive Boardroom 401" } },
        "QR_4_AUDITORIUM": { floor: 4, node_id: "NODE_ROOM_4_06", coordinates: { x: 1020, y: 220 }, qr: { code_id: "QR_4_AUDITORIUM", location_label: "Grand Auditorium 406", node_name: "Grand Auditorium 406" } },
        "QR_4_ROOF_EXIT": { floor: 4, node_id: "N4_C_CENTER", coordinates: { x: 600, y: 370 }, qr: { code_id: "QR_4_ROOF_EXIT", location_label: "Skydeck Access L4", node_name: "Skydeck Access L4" } },
        "QR_4_STAIR_A": { floor: 4, node_id: "STAIR_A_4", coordinates: { x: 380, y: 220 }, qr: { code_id: "QR_4_STAIR_A", location_label: "West Staircase A L4", node_name: "West Staircase A L4" } },
        "QR_4_STAIR_B": { floor: 4, node_id: "STAIR_B_4", coordinates: { x: 820, y: 220 }, qr: { code_id: "QR_4_STAIR_B", location_label: "East Staircase B L4", node_name: "East Staircase B L4" } }
      };

      if (fallbackQR[cleanCode] && this.onPositionResolved) {
        const res = { status: "success", ...fallbackQR[cleanCode] };
        this.onPositionResolved(res);
        return res;
      }
      return { status: "error", message: "QR resolution failed" };
    }
  }

  /**
   * Starts camera stream and begins barcode detection loop.
   */
  async startCamera(videoElementId, onScanSuccess) {
    this.videoElement = document.getElementById(videoElementId);
    if (!this.videoElement) return false;

    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        this.stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 }
          }
        });

        this.videoElement.srcObject = this.stream;
        this.videoElement.setAttribute("playsinline", "true");
        this.videoElement.muted = true;
        await this.videoElement.play();
        this.isScanning = true;

        // Start continuous barcode detection loop
        this._startScanLoop(onScanSuccess);
        return true;
      }
    } catch (err) {
      console.warn("Camera access denied or unavailable:", err);
      return false;
    }
    return false;
  }

  _extractCode(rawVal) {
    if (!rawVal) return "";
    let code = String(rawVal).trim();
    if (code.includes("?qr=")) {
      code = code.split("?qr=")[1].split("&")[0];
    } else if (code.includes("/qr/")) {
      code = code.split("/qr/")[1].split("?")[0];
    }
    return code;
  }

  _handleSuccessfulScan(code, onScanSuccess) {
    if (navigator.vibrate) {
      try { navigator.vibrate([100, 50, 100]); } catch (e) {}
    }
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(880, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.18);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.18);
    } catch (e) {}

    this.stopCamera();
    if (onScanSuccess) {
      onScanSuccess(code);
    } else {
      this.resolveCodeId(code);
    }
  }

  _startScanLoop(onScanSuccess) {
    if (!this.isScanning || !this.videoElement) return;

    const checkFrame = async () => {
      if (!this.isScanning || !this.videoElement) return;

      // 1. Try native BarcodeDetector if supported
      if (this.barcodeDetector && this.videoElement.readyState >= 2) {
        try {
          const barcodes = await this.barcodeDetector.detect(this.videoElement);
          if (barcodes && barcodes.length > 0) {
            const rawVal = barcodes[0].rawValue;
            const code = this._extractCode(rawVal);
            this._handleSuccessfulScan(code, onScanSuccess);
            return;
          }
        } catch (e) {}
      }

      // 2. High-performance jsQR fallback (iOS Safari, Firefox, Chrome, Desktop webcams)
      if (typeof window !== "undefined" && window.jsQR && this.videoElement.readyState >= 2 && this.canvasContext) {
        try {
          const vw = this.videoElement.videoWidth || 640;
          const vh = this.videoElement.videoHeight || 480;
          if (vw > 0 && vh > 0) {
            const scale = Math.min(1, 640 / Math.max(vw, vh));
            const cw = Math.floor(vw * scale);
            const ch = Math.floor(vh * scale);
            if (this.canvas.width !== cw) this.canvas.width = cw;
            if (this.canvas.height !== ch) this.canvas.height = ch;
            this.canvasContext.drawImage(this.videoElement, 0, 0, cw, ch);
            const imgData = this.canvasContext.getImageData(0, 0, cw, ch);
            const qrCode = window.jsQR(imgData.data, cw, ch, {
              inversionAttempts: "dontInvert"
            });
            if (qrCode && qrCode.data) {
              const code = this._extractCode(qrCode.data);
              this._handleSuccessfulScan(code, onScanSuccess);
              return;
            }
          }
        } catch (e) {}
      }

      if (this.isScanning) {
        this.animFrameId = requestAnimationFrame(checkFrame);
      }
    };

    this.animFrameId = requestAnimationFrame(checkFrame);
  }

  /**
   * Stops video stream and detection loop.
   */
  stopCamera() {
    this.isScanning = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
  }
}

if (typeof window !== "undefined") {
  window.QRPositioningScanner = QRPositioningScanner;
}
