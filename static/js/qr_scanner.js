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
      // Offline fallback lookup
      const fallbackQR = {
        "QR_3_AILAB": { floor: 3, node_id: "NODE_ROOM_3_05", coordinates: { x: 890, y: 290 }, qr: { code_id: "QR_3_AILAB", location_label: "AI Lab 305", node_name: "[305] AI & Robotics Lab" } },
        "QR_4_AUDITORIUM": { floor: 4, node_id: "NODE_ROOM_4_06", coordinates: { x: 890, y: 390 }, qr: { code_id: "QR_4_AUDITORIUM", location_label: "Grand Auditorium", node_name: "[406] Grand Auditorium" } },
        "QR_2_LECTURE": { floor: 2, node_id: "NODE_ROOM_2_01", coordinates: { x: 250, y: 290 }, qr: { code_id: "QR_2_LECTURE", location_label: "Lecture Hall 201", node_name: "[201] Smart Lecture Hall" } },
        "QR_1_FACULTY": { floor: 1, node_id: "NODE_ROOM_1_01", coordinates: { x: 250, y: 290 }, qr: { code_id: "QR_1_FACULTY", location_label: "Faculty Dept 101", node_name: "[101] Faculty Dept Office" } },
        "QR_G_ATRIUM": { floor: 0, node_id: "NODE_LOBBY_SOUTH", coordinates: { x: 600, y: 480 }, qr: { code_id: "QR_G_ATRIUM", location_label: "Central Atrium", node_name: "Ground Floor Atrium Portal" } }
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

  _startScanLoop(onScanSuccess) {
    if (!this.isScanning || !this.videoElement) return;

    const checkFrame = async () => {
      if (!this.isScanning) return;

      if (this.barcodeDetector && this.videoElement.readyState >= 2) {
        try {
          const barcodes = await this.barcodeDetector.detect(this.videoElement);
          if (barcodes && barcodes.length > 0) {
            const rawVal = barcodes[0].rawValue;
            let code = rawVal;
            if (rawVal.includes("?qr=")) {
              code = rawVal.split("?qr=")[1].split("&")[0];
            } else if (rawVal.includes("/qr/")) {
              code = rawVal.split("/qr/")[1].split("?")[0];
            }

            if (navigator.vibrate) {
              navigator.vibrate([100, 50, 100]);
            }

            this.stopCamera();
            if (onScanSuccess) {
              onScanSuccess(code);
            } else {
              this.resolveCodeId(code);
            }
            return;
          }
        } catch (e) {
          // Frame dropped or not decoded
        }
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
