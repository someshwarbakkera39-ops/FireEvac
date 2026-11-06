/**
 * Smart Emergency Evacuation Planning & Digital Twin System
 * Block A Architectural Blueprint & Vector Coordinate Model
 * Floors: Ground (0), 1st (1), 2nd (2), 3rd (3), 4th (4)
 */

const BLOCK_A_MODEL = {
  metadata: {
    title: "Block A Facility Digital Twin",
    floorsCount: 5,
    levels: [0, 1, 2, 3, 4],
    viewBox: "0 0 1200 750",
    dimensions: { width: 1200, height: 750 }
  },
  palette: {
    slate: "#64748b",
    slateDark: "#334155",
    slateLight: "#f1f5f9",
    wallColor: "#475569",
    safeGreen: "#16a34a",
    hazardRed: "#dc2626",
    currentBlue: "#2563eb",
    warningAmber: "#f59e0b",
    corridorFill: "#e2e8f0",
    roomFill: "#f8fafc",
    roomBorder: "#94a3b8",
    roomHover: "#e0f2fe",
    stairFill: "#fef3c7",
    stairBorder: "#d97706",
    exitFill: "#dcfce7",
    exitBorder: "#16a34a"
  },
  stairwells: [
    {
      id: "STAIR_A",
      name: "Staircase A (West Wing Core)",
      bounds: { x: 120, y: 130, width: 100, height: 90 },
      node: { x: 170, y: 175 },
      connector: { x: 275, y: 175 },
      serves: [0, 1, 2, 3, 4],
      desc: "Reinforced West Fire Staircase with multi-floor egress"
    },
    {
      id: "STAIR_B",
      name: "Staircase B (East Wing Core)",
      bounds: { x: 980, y: 130, width: 100, height: 90 },
      node: { x: 1030, y: 175 },
      connector: { x: 925, y: 175 },
      serves: [0, 1, 2, 3, 4],
      desc: "Reinforced East Fire Staircase with multi-floor egress"
    }
  ],
  assemblyPoints: [
    {
      id: "ASSEMBLY_SOUTH",
      name: "Assembly Point 1 - South Lawn",
      x: 600,
      y: 715,
      radius: 28,
      lat: 12.9716,
      lng: 77.5946
    },
    {
      id: "ASSEMBLY_NORTH",
      name: "Assembly Point 2 - North Sports Field",
      x: 600,
      y: 45,
      radius: 28,
      lat: 12.9725,
      lng: 77.5946
    }
  ],
  floors: {
    0: {
      name: "Ground Floor",
      level: 0,
      code: "G",
      subtitle: "Main Entrance, Admin Offices, Atrium & 3 Building Exits",
      exits: [
        {
          id: "EXIT_G_MAIN",
          name: "Exit 1 (South Main Exit)",
          x: 570,
          y: 620,
          w: 60,
          h: 22,
          node: { x: 600, y: 620 },
          assemblyId: "ASSEMBLY_SOUTH",
          label: "MAIN EXIT 1"
        },
        {
          id: "EXIT_G_WEST",
          name: "Exit 2 (West Fire Exit)",
          x: 100,
          y: 345,
          w: 22,
          h: 50,
          node: { x: 100, y: 370 },
          assemblyId: "ASSEMBLY_NORTH",
          label: "FIRE EXIT 2"
        },
        {
          id: "EXIT_G_EAST",
          name: "Exit 3 (East Fire Exit)",
          x: 1078,
          y: 345,
          w: 22,
          h: 50,
          node: { x: 1100, y: 370 },
          assemblyId: "ASSEMBLY_SOUTH",
          label: "FIRE EXIT 3"
        }
      ],
      rooms: [
        { id: "ROOM_G_01", code: "G-101", name: "Admin & Finance Office", x: 120, y: 240, w: 130, h: 100, door: { x: 250, y: 290 }, type: "admin" },
        { id: "ROOM_G_02", code: "G-102", name: "First Aid & Clinic", x: 120, y: 360, w: 130, h: 100, door: { x: 250, y: 410 }, type: "medical" },
        { id: "ROOM_G_03", code: "G-103", name: "Security Operations Command", x: 120, y: 480, w: 130, h: 110, door: { x: 250, y: 535 }, type: "security" },
        { id: "ROOM_G_04", code: "G-104", name: "Visitor Lounge & Reception", x: 300, y: 130, w: 130, h: 100, door: { x: 300, y: 180 }, type: "lounge" },
        { id: "ROOM_G_05", code: "G-105", name: "Records Archive & Store", x: 300, y: 420, w: 130, h: 170, door: { x: 300, y: 470 }, type: "facility" },
        { id: "LOBBY_G", code: "G-ATRIUM", name: "Grand Central Atrium", x: 450, y: 260, w: 300, h: 220, door: { x: 600, y: 480 }, type: "lobby" },
        { id: "ROOM_G_06", code: "G-106", name: "Cafeteria & Dining Hall", x: 770, y: 130, w: 190, h: 160, door: { x: 890, y: 290 }, type: "dining" },
        { id: "ROOM_G_07", code: "G-107", name: "Electrical Substation", x: 770, y: 420, w: 130, h: 170, door: { x: 900, y: 470 }, type: "utility" },
        { id: "ROOM_G_08", code: "G-108", name: "Facility Maintenance", x: 950, y: 240, w: 130, h: 100, door: { x: 950, y: 290 }, type: "engineering" },
        { id: "ROOM_G_09", code: "G-109", name: "Logistics Receiving Bay", x: 950, y: 420, w: 130, h: 170, door: { x: 950, y: 470 }, type: "logistics" }
      ]
    },
    1: {
      name: "First Floor",
      level: 1,
      code: "1F",
      subtitle: "Faculty Suites, Software Labs, Prototype Workshop & Skybridge",
      exits: [],
      rooms: [
        { id: "ROOM_1_01", code: "101", name: "Faculty Office Wing A", x: 120, y: 240, w: 130, h: 100, door: { x: 250, y: 290 }, type: "office" },
        { id: "ROOM_1_02", code: "102", name: "Faculty Office Wing B", x: 120, y: 360, w: 130, h: 100, door: { x: 250, y: 410 }, type: "office" },
        { id: "ROOM_1_03", code: "103", name: "HOD Executive Suite", x: 120, y: 480, w: 130, h: 110, door: { x: 250, y: 535 }, type: "executive" },
        { id: "ROOM_1_04", code: "104", name: "Staff Conference W1", x: 300, y: 130, w: 130, h: 100, door: { x: 300, y: 180 }, type: "conference" },
        { id: "ROOM_1_05", code: "105", name: "Restroom Core West", x: 300, y: 420, w: 130, h: 170, door: { x: 300, y: 470 }, type: "restroom" },
        { id: "BRIDGE_1", code: "1-BRIDGE", name: "Skybridge Exhibition Gallery", x: 450, y: 280, w: 300, h: 180, door: { x: 600, y: 370 }, type: "bridge" },
        { id: "ROOM_1_06", code: "106", name: "CS Software Lab 101", x: 770, y: 130, w: 190, h: 160, door: { x: 890, y: 290 }, type: "lab" },
        { id: "ROOM_1_07", code: "107", name: "Network Systems Lab 102", x: 770, y: 420, w: 130, h: 170, door: { x: 900, y: 470 }, type: "lab" },
        { id: "ROOM_1_08", code: "108", name: "Electronics Prototype Lab", x: 950, y: 240, w: 130, h: 100, door: { x: 950, y: 290 }, type: "workshop" },
        { id: "ROOM_1_09", code: "109", name: "Telecom Server Room 1", x: 950, y: 420, w: 130, h: 170, door: { x: 950, y: 470 }, type: "server" }
      ]
    },
    2: {
      name: "Second Floor",
      level: 2,
      code: "2F",
      subtitle: "Lecture Theaters, Seminar Hall, Study Pods & IoT Hub",
      exits: [],
      rooms: [
        { id: "ROOM_2_01", code: "201", name: "Smart Lecture Hall 201", x: 120, y: 240, w: 130, h: 100, door: { x: 250, y: 290 }, type: "classroom" },
        { id: "ROOM_2_02", code: "202", name: "Smart Lecture Hall 202", x: 120, y: 360, w: 130, h: 100, door: { x: 250, y: 410 }, type: "classroom" },
        { id: "ROOM_2_03", code: "203", name: "Tutorial & Seminar Room", x: 120, y: 480, w: 130, h: 110, door: { x: 250, y: 535 }, type: "tutorial" },
        { id: "ROOM_2_04", code: "204", name: "Student Innovation Studio", x: 300, y: 130, w: 130, h: 100, door: { x: 300, y: 180 }, type: "studio" },
        { id: "ROOM_2_05", code: "205", name: "Restroom Core West", x: 300, y: 420, w: 130, h: 170, door: { x: 300, y: 470 }, type: "restroom" },
        { id: "BRIDGE_2", code: "2-BRIDGE", name: "Central Collaborative Pods", x: 450, y: 280, w: 300, h: 180, door: { x: 600, y: 370 }, type: "bridge" },
        { id: "ROOM_2_06", code: "206", name: "Multipurpose Seminar Hall", x: 770, y: 130, w: 190, h: 160, door: { x: 890, y: 290 }, type: "seminar" },
        { id: "ROOM_2_07", code: "207", name: "Smart Classroom 204", x: 770, y: 420, w: 130, h: 170, door: { x: 900, y: 470 }, type: "classroom" },
        { id: "ROOM_2_08", code: "208", name: "Smart Classroom 205", x: 950, y: 240, w: 130, h: 100, door: { x: 950, y: 290 }, type: "classroom" },
        { id: "ROOM_2_09", code: "209", name: "Digital Twin IoT Sensor Node", x: 950, y: 420, w: 130, h: 170, door: { x: 950, y: 470 }, type: "server" }
      ]
    },
    3: {
      name: "Third Floor",
      level: 3,
      code: "3F",
      subtitle: "Central Library, AI Research Lab & High-Performance Computing",
      exits: [],
      rooms: [
        { id: "ROOM_3_01", code: "301", name: "Department Library Stacks", x: 120, y: 240, w: 130, h: 160, door: { x: 250, y: 320 }, type: "library" },
        { id: "ROOM_3_02", code: "302", name: "Digital Library Terminals", x: 120, y: 430, w: 130, h: 160, door: { x: 250, y: 490 }, type: "library" },
        { id: "ROOM_3_03", code: "303", name: "Silent Study Cubicles", x: 300, y: 130, w: 130, h: 100, door: { x: 300, y: 180 }, type: "library" },
        { id: "ROOM_3_04", code: "304", name: "Historical Archives", x: 300, y: 420, w: 130, h: 170, door: { x: 300, y: 470 }, type: "archive" },
        { id: "BRIDGE_3", code: "3-BRIDGE", name: "Central Reading Commons", x: 450, y: 280, w: 300, h: 180, door: { x: 600, y: 370 }, type: "bridge" },
        { id: "ROOM_3_05", code: "305", name: "AI & Robotics Research Lab", x: 770, y: 130, w: 190, h: 160, door: { x: 890, y: 290 }, type: "lab" },
        { id: "ROOM_3_06", code: "306", name: "HPC Supercomputing Cluster", x: 770, y: 420, w: 130, h: 170, door: { x: 900, y: 470 }, type: "server" },
        { id: "ROOM_3_07", code: "307", name: "Embedded Systems Workshop", x: 950, y: 240, w: 130, h: 100, door: { x: 950, y: 290 }, type: "lab" },
        { id: "ROOM_3_08", code: "308", name: "UPS & Backup Generator Vault", x: 950, y: 420, w: 130, h: 170, door: { x: 950, y: 470 }, type: "utility" }
      ]
    },
    4: {
      name: "Fourth Floor",
      level: 4,
      code: "4F",
      subtitle: "Executive Boardroom, Dean Suite, Grand Auditorium & Rooftop",
      exits: [],
      rooms: [
        { id: "ROOM_4_01", code: "401", name: "Executive Boardroom", x: 120, y: 240, w: 130, h: 120, door: { x: 250, y: 300 }, type: "executive" },
        { id: "ROOM_4_02", code: "402", name: "Dean & Chancellor Suite", x: 120, y: 390, w: 130, h: 110, door: { x: 250, y: 445 }, type: "executive" },
        { id: "ROOM_4_03", code: "403", name: "VIP Delegation Lounge", x: 120, y: 520, w: 130, h: 70, door: { x: 250, y: 555 }, type: "lounge" },
        { id: "ROOM_4_04", code: "404", name: "Rooftop Access Vestibule", x: 300, y: 130, w: 130, h: 100, door: { x: 300, y: 180 }, type: "utility" },
        { id: "ROOM_4_05", code: "405", name: "Secretariat & Archives", x: 300, y: 420, w: 130, h: 170, door: { x: 300, y: 470 }, type: "office" },
        { id: "BRIDGE_4", code: "4-BRIDGE", name: "Executive Skylight Mezzanine", x: 450, y: 280, w: 300, h: 180, door: { x: 600, y: 370 }, type: "bridge" },
        { id: "ROOM_4_06", code: "406", name: "Grand Auditorium (250 cap)", x: 770, y: 130, w: 310, h: 260, door: { x: 890, y: 390 }, type: "auditorium" },
        { id: "ROOM_4_07", code: "407", name: "AV Control & Broadcast Studio", x: 770, y: 420, w: 130, h: 170, door: { x: 900, y: 470 }, type: "media" },
        { id: "ROOM_4_08", code: "408", name: "Backstage & Green Room", x: 950, y: 420, w: 130, h: 170, door: { x: 950, y: 470 }, type: "backstage" }
      ]
    }
  }
};

// Export to window or module
if (typeof window !== "undefined") {
  window.BLOCK_A_MODEL = BLOCK_A_MODEL;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = BLOCK_A_MODEL;
}

