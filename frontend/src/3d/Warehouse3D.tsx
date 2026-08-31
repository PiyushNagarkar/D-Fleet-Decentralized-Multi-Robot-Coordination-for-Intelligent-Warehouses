/**
 * Warehouse3D: Modern Bright White / Light-Gray Industrial Digital-Twin Viewport
 * Features clean epoxy flooring, high-contrast shelving aisles, distinct pickup/delivery/charging zones,
 * bright studio daylight illumination, and smooth camera tracking modes.
 */

import React, { Suspense, useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsType } from "three-stdlib";
import * as THREE from "three";
import { ShelfModel } from "./ShelfModel";
import { StationModel } from "./StationModel";
import { RobotModel } from "./RobotModel";
import { DynamicObstacleModel } from "./DynamicObstacle";
import { PathRenderer } from "./PathRenderer";
import { CommunicationGraph } from "./CommunicationGraph";
import { TelemetrySnapshot } from "../types";
import { RotateCcw, Compass, Bot, Layers, Eye } from "lucide-react";
import { gridToWorld } from "../utils/coordinate";
import { WAREHOUSE_SHELVES } from "../services/localSimulationEngine";

interface Warehouse3DProps {
  telemetry: TelemetrySnapshot;
  selectedRobotId: string | null;
  onSelectRobot: (robotId: string) => void;
  viewMode?: "3d" | "2d";
  showReservations?: boolean;
  width?: number;
  height?: number;
}

/**
 * Camera controller component that smoothly interpolates to target position and follows selected robot.
 */
const CameraManager: React.FC<{
  followRobotPos?: [number, number, number] | null;
  controlsRef: React.RefObject<OrbitControlsType | null>;
}> = ({ followRobotPos, controlsRef }) => {
  useFrame((_, delta) => {
    if (controlsRef.current) {
      if (followRobotPos) {
        // Smoothly follow selected AMR
        const currentTarget = controlsRef.current.target;
        currentTarget.x = THREE.MathUtils.lerp(currentTarget.x, followRobotPos[0], delta * 4);
        currentTarget.z = THREE.MathUtils.lerp(currentTarget.z, followRobotPos[2], delta * 4);
      }
      controlsRef.current.update();
    }
  });

  return null;
};

export const Warehouse3D: React.FC<Warehouse3DProps> = ({
  telemetry,
  selectedRobotId,
  onSelectRobot,
  viewMode = "3d",
  showReservations: initialShowRes = true,
  width = 16,
  height = 12,
}) => {
  const controlsRef = useRef<OrbitControlsType | null>(null);
  const [showPaths, setShowPaths] = useState(true);
  const [showReservations, setShowReservations] = useState(initialShowRes);
  const [followRobot, setFollowRobot] = useState(false);

  // Sync initialShowRes prop changes
  useEffect(() => {
    setShowReservations(initialShowRes);
  }, [initialShowRes]);

  // Center coordinate of the warehouse grid
  const centerX = width / 2;
  const centerZ = height / 2;

  // Extract Stations dynamically from tasks and charging points
  const stations: Array<{ x: number; y: number; type: "PICKUP" | "DELIVERY" | "CHARGING"; label?: string }> = [
    { x: 1, y: 1, type: "CHARGING", label: "C1" },
    { x: 14, y: 1, type: "CHARGING", label: "C2" },
  ];

  // Dynamic Pickups & Deliveries from active scenario tasks
  const pickupSet = new Set<string>();
  const deliverySet = new Set<string>();

  telemetry.tasks.forEach((t) => {
    const pKey = `${t.pickup_location[0]},${t.pickup_location[1]}`;
    if (!pickupSet.has(pKey)) {
      pickupSet.add(pKey);
      stations.push({
        x: t.pickup_location[0],
        y: t.pickup_location[1],
        type: "PICKUP",
        label: `P${pickupSet.size}`,
      });
    }

    const dKey = `${t.delivery_location[0]},${t.delivery_location[1]}`;
    if (!deliverySet.has(dKey)) {
      deliverySet.add(dKey);
      stations.push({
        x: t.delivery_location[0],
        y: t.delivery_location[1],
        type: "DELIVERY",
        label: `D${deliverySet.size}`,
      });
    }
  });

  // Storage shelves layout matching multi-aisle logistics warehouse with wide open lanes
  const shelves = WAREHOUSE_SHELVES;

  // Selected robot world position for follow mode
  const selectedRobot = telemetry.robots.find((r) => r.id === selectedRobotId);
  const selectedRobotWorldPos = selectedRobot
    ? gridToWorld(selectedRobot.position[0], selectedRobot.position[1], 0)
    : null;

  // Camera initial position
  const initialCameraPos: [number, number, number] =
    viewMode === "2d"
      ? [centerX, 20, centerZ]
      : [centerX, 15, centerZ + 11];

  const handleResetCamera = () => {
    setFollowRobot(false);
    if (controlsRef.current) {
      controlsRef.current.target.set(centerX, 0, centerZ);
      controlsRef.current.object.position.set(centerX, 15, centerZ + 11);
      controlsRef.current.update();
    }
  };

  const handleTopView = () => {
    setFollowRobot(false);
    if (controlsRef.current) {
      controlsRef.current.target.set(centerX, 0, centerZ);
      controlsRef.current.object.position.set(centerX, 20, centerZ);
      controlsRef.current.update();
    }
  };

  return (
    <div className="w-full h-full relative bg-slate-950 select-none overflow-hidden flex flex-col rounded-xl border border-slate-800 shadow-2xl">
      {/* 1. Top Header Banner */}
      <div className="h-9 px-3.5 bg-slate-900/95 border-b border-slate-800 flex items-center justify-between z-10 shrink-0 font-mono text-xs">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-sm shadow-cyan-400" />
          <span className="font-bold text-white tracking-wider text-[11px]">
            3D DIGITAL TWIN WAREHOUSE
          </span>
        </div>

        {/* Legend */}
        <div className="hidden sm:flex items-center gap-3 text-[10px] text-slate-300">
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded bg-sky-500 inline-block" />
            <span>Pickup</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded bg-emerald-500 inline-block" />
            <span>Delivery</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded bg-purple-500 inline-block" />
            <span>Charging</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded bg-amber-400 inline-block" />
            <span>Reservations</span>
          </div>
        </div>

        {/* Quick View Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setFollowRobot((f) => !f)}
            className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 border transition-all cursor-pointer ${
              followRobot
                ? "bg-sky-950 border-sky-400 text-sky-300 shadow-sm"
                : "bg-slate-950 border-slate-700 text-slate-400 hover:text-slate-200"
            }`}
            title="Follow selected robot"
          >
            <Eye className="w-3 h-3" />
            <span>{followRobot ? "FOLLOWING" : "FOLLOW"}</span>
          </button>

          <button
            onClick={handleTopView}
            className="px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 bg-slate-950 hover:bg-slate-850 border border-slate-700 text-slate-300 transition-all cursor-pointer"
            title="Top 2D View"
          >
            <Compass className="w-3 h-3" />
            <span>TOP</span>
          </button>

          <button
            onClick={handleResetCamera}
            className="px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 bg-slate-950 hover:bg-slate-850 border border-slate-700 text-slate-300 transition-all cursor-pointer"
            title="Reset 3D Overview Camera"
          >
            <RotateCcw className="w-3 h-3" />
            <span>RESET</span>
          </button>
        </div>
      </div>

      {/* 2. Main 3D Canvas Area */}
      <div className="flex-1 relative w-full h-full">
        <Canvas
          shadows
          camera={{ position: initialCameraPos, fov: 42 }}
          className="w-full h-full"
        >
          <Suspense fallback={null}>
            {/* Ambient & Bright Daylight Illumination */}
            <ambientLight intensity={1.2} color="#ffffff" />
            <directionalLight
              position={[centerX + 8, 24, centerZ + 14]}
              intensity={2.2}
              castShadow
              shadow-mapSize={[2048, 2048]}
              shadow-camera-left={-16}
              shadow-camera-right={16}
              shadow-camera-top={16}
              shadow-camera-bottom={-16}
              shadow-bias={-0.0001}
            />
            {/* Studio Fill Light */}
            <directionalLight
              position={[centerX - 10, 18, centerZ - 10]}
              intensity={1.0}
              color="#e0f2fe"
            />
            <hemisphereLight groundColor="#cbd5e1" color="#ffffff" intensity={0.9} />

            {/* Orbit Controls */}
            <OrbitControls
              ref={controlsRef}
              target={[centerX, 0, centerZ]}
              maxPolarAngle={Math.PI / 2.05}
              minDistance={5}
              maxDistance={35}
              enableDamping
              dampingFactor={0.08}
            />

            <CameraManager
              followRobotPos={followRobot ? selectedRobotWorldPos : null}
              controlsRef={controlsRef}
            />

            {/* 3. BRIGHT INDUSTRIAL WAREHOUSE FLOOR */}
            {/* Main Light-Gray Epoxy Floor */}
            <mesh
              position={[centerX, -0.01, centerZ]}
              rotation={[-Math.PI / 2, 0, 0]}
              receiveShadow
            >
              <planeGeometry args={[width + 4, height + 4]} />
              <meshStandardMaterial
                color="#eef2f6"
                roughness={0.25}
                metalness={0.15}
              />
            </mesh>

            {/* Subtle Navigation Grid Lines */}
            <gridHelper
              args={[width + 2, width + 2, "#94a3b8", "#cbd5e1"]}
              position={[centerX, 0.001, centerZ]}
            />

            {/* Safety Yellow Perimeter Boundary Stripe */}
            <mesh position={[centerX, 0.005, -0.1]} receiveShadow>
              <boxGeometry args={[width + 0.4, 0.01, 0.1]} />
              <meshBasicMaterial color="#eab308" />
            </mesh>
            <mesh position={[centerX, 0.005, height + 0.1]} receiveShadow>
              <boxGeometry args={[width + 0.4, 0.01, 0.1]} />
              <meshBasicMaterial color="#eab308" />
            </mesh>
            <mesh position={[-0.1, 0.005, centerZ]} receiveShadow>
              <boxGeometry args={[0.1, 0.01, height + 0.4]} />
              <meshBasicMaterial color="#eab308" />
            </mesh>
            <mesh position={[width + 0.1, 0.005, centerZ]} receiveShadow>
              <boxGeometry args={[0.1, 0.01, height + 0.4]} />
              <meshBasicMaterial color="#eab308" />
            </mesh>

            {/* 4. WAREHOUSE PERIMETER WALLS & PILLARS */}
            {/* North Wall */}
            <mesh position={[centerX, 1.5, -0.8]} receiveShadow>
              <boxGeometry args={[width + 3, 3, 0.2]} />
              <meshStandardMaterial color="#f8fafc" roughness={0.5} />
            </mesh>
            {/* South Wall */}
            <mesh position={[centerX, 1.5, height + 0.8]} receiveShadow>
              <boxGeometry args={[width + 3, 3, 0.2]} />
              <meshStandardMaterial color="#f8fafc" roughness={0.5} />
            </mesh>
            {/* West Wall */}
            <mesh position={[-0.8, 1.5, centerZ]} receiveShadow>
              <boxGeometry args={[0.2, 3, height + 3]} />
              <meshStandardMaterial color="#f8fafc" roughness={0.5} />
            </mesh>
            {/* East Wall */}
            <mesh position={[width + 0.8, 1.5, centerZ]} receiveShadow>
              <boxGeometry args={[0.2, 3, height + 3]} />
              <meshStandardMaterial color="#f8fafc" roughness={0.5} />
            </mesh>

            {/* Steel Support Columns on Corners */}
            {[
              [-0.6, -0.6],
              [width + 0.6, -0.6],
              [-0.6, height + 0.6],
              [width + 0.6, height + 0.6],
            ].map(([cx, cz], idx) => (
              <mesh key={idx} position={[cx, 1.5, cz]} castShadow receiveShadow>
                <boxGeometry args={[0.3, 3.2, 0.3]} />
                <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.3} />
              </mesh>
            ))}

            {/* 5. STATIONS (Pickups, Deliveries, Charging) */}
            {stations.map((st, idx) => (
              <StationModel
                key={`station_${idx}`}
                x={st.x}
                y={st.y}
                type={st.type}
                label={st.label}
              />
            ))}

            {/* 6. STORAGE PALLET SHELVES */}
            {shelves.map(([sx, sy], idx) => (
              <ShelfModel key={`shelf_${idx}`} x={sx} y={sy} height={1.6} />
            ))}

            {/* 7. DYNAMIC MOVING / STATIC OBSTACLES */}
            {telemetry.obstacles.map((obs) => (
              <DynamicObstacleModel
                key={obs.id}
                obstacle={obs}
              />
            ))}

            {/* 8. ROBOT PATHS, RESERVATIONS & CONFLICT ZONES */}
            <PathRenderer
              robots={telemetry.robots}
              reservations={telemetry.reservations}
              selectedRobotId={selectedRobotId}
              showReservations={showReservations}
              showConflicts={true}
              showPaths={showPaths}
            />

            {/* 9. P2P COMMUNICATION LASER BEAMS */}
            <CommunicationGraph
              recentMessages={telemetry.recent_messages}
              robots={telemetry.robots}
            />

            {/* 10. AUTONOMOUS MOBILE ROBOTS (AMRs) */}
            {telemetry.robots.map((robot) => (
              <RobotModel
                key={robot.id}
                robot={robot}
                isSelected={selectedRobotId === robot.id}
                onSelect={() => onSelectRobot(robot.id)}
              />
            ))}
          </Suspense>
        </Canvas>
      </div>

      {/* 3. Bottom View Control Floating Strip */}
      <div className="absolute bottom-2.5 left-3 z-10 flex items-center gap-2 font-mono text-[10px]">
        <button
          onClick={() => setShowPaths((p) => !p)}
          className={`px-2.5 py-1 rounded-lg border font-bold flex items-center gap-1 shadow-md transition-all cursor-pointer backdrop-blur-md ${
            showPaths
              ? "bg-sky-950/90 border-sky-400 text-sky-300"
              : "bg-slate-950/80 border-slate-700 text-slate-400"
          }`}
        >
          <Bot className="w-3 h-3" />
          <span>PATHS {showPaths ? "ON" : "OFF"}</span>
        </button>

        <button
          onClick={() => setShowReservations((r) => !r)}
          className={`px-2.5 py-1 rounded-lg border font-bold flex items-center gap-1 shadow-md transition-all cursor-pointer backdrop-blur-md ${
            showReservations
              ? "bg-purple-950/90 border-purple-400 text-purple-300"
              : "bg-slate-950/80 border-slate-700 text-slate-400"
          }`}
        >
          <Layers className="w-3 h-3" />
          <span>RESERVATIONS {showReservations ? "ON" : "OFF"}</span>
        </button>
      </div>
    </div>
  );
};
