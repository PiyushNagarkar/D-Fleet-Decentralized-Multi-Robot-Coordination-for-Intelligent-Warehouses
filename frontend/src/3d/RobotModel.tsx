/**
 * RobotModel: High-Fidelity 3D Autonomous Mobile Robot (AMR)
 * Features sleek industrial chassis, rotating LiDAR scanner, drive wheels,
 * top cargo payload container, smooth position/heading interpolation,
 * and compact non-obtrusive transient status indicators.
 */

import React, { useRef, useState, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { gridToWorld, getRobotColor } from "../utils/coordinate";
import { RobotTelemetry, RobotStatus } from "../types";

interface RobotModelProps {
  robot: RobotTelemetry;
  isSelected?: boolean;
  onSelect?: () => void;
}

export const RobotModel: React.FC<RobotModelProps> = ({
  robot,
  isSelected = false,
  onSelect,
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const lidarRef = useRef<THREE.Mesh>(null);
  const wheelsRef = useRef<THREE.Group>(null);

  // Target world coordinates
  const [targetX, targetY, targetZ] = gridToWorld(robot.position[0], robot.position[1], 0.16);

  const baseAccentColor = getRobotColor(robot.id);
  const isMoving =
    robot.status === RobotStatus.MOVING_TO_PICKUP ||
    robot.status === RobotStatus.MOVING_TO_DELIVERY;
  const isCharging = robot.status === RobotStatus.CHARGING;
  const isFailed = robot.status === RobotStatus.FAILED;

  const targetHeadingRef = useRef<number>(0);

  // Transient Status Flash (show PICKUP / DELIVERING only briefly for 2.2s on state transitions)
  const prevStatusRef = useRef<RobotStatus>(robot.status);
  const [transientStatus, setTransientStatus] = useState<string | null>(null);

  useEffect(() => {
    if (robot.status !== prevStatusRef.current) {
      if (robot.status === RobotStatus.MOVING_TO_PICKUP) {
        setTransientStatus("PICKUP");
      } else if (robot.status === RobotStatus.MOVING_TO_DELIVERY) {
        setTransientStatus("DELIVERY");
      } else if (robot.status === RobotStatus.CHARGING) {
        setTransientStatus("CHARGING");
      }
      prevStatusRef.current = robot.status;

      const timer = setTimeout(() => {
        setTransientStatus(null);
      }, 2200);
      return () => clearTimeout(timer);
    }
  }, [robot.status]);

  // Smooth position & rotation interpolation
  useFrame((state, delta) => {
    if (groupRef.current) {
      const currentPos = groupRef.current.position;

      // Calculate direction of movement to slerp heading rotation
      const dx = targetX - currentPos.x;
      const dz = targetZ - currentPos.z;
      const moveDist = Math.sqrt(dx * dx + dz * dz);

      if (moveDist > 0.05) {
        targetHeadingRef.current = Math.atan2(dx, dz);
      }

      // Smooth position lerp
      currentPos.x = THREE.MathUtils.lerp(currentPos.x, targetX, delta * 12);
      currentPos.z = THREE.MathUtils.lerp(currentPos.z, targetZ, delta * 12);
      currentPos.y = isMoving
        ? targetY + Math.sin(state.clock.elapsedTime * 16) * 0.015
        : targetY;

      // Smooth heading rotation slerp
      const currentRot = groupRef.current.rotation.y;
      let diff = targetHeadingRef.current - currentRot;
      while (diff < -Math.PI) diff += Math.PI * 2;
      while (diff > Math.PI) diff -= Math.PI * 2;
      groupRef.current.rotation.y += diff * Math.min(1, delta * 10);
    }

    // Active spinning LiDAR scanner
    if (lidarRef.current) {
      lidarRef.current.rotation.y += delta * (isFailed ? 0 : 10);
    }

    // Rotating drive wheels during movement
    if (wheelsRef.current && isMoving) {
      wheelsRef.current.rotation.x += delta * 15;
    }
  });

  const getStatusBorder = () => {
    if (isFailed) return "border-rose-500 bg-rose-950/90 text-rose-300";
    if (isCharging) return "border-purple-500 bg-purple-950/90 text-purple-300";
    if (robot.status === RobotStatus.WAITING || robot.status === RobotStatus.YIELDING) {
      return "border-amber-500 bg-amber-950/90 text-amber-300";
    }
    return "border-slate-700 bg-slate-950/90 text-slate-300";
  };

  return (
    <group ref={groupRef} position={[targetX, targetY, targetZ]} onClick={onSelect}>
      {/* 1. Selection Highlight Ring */}
      {isSelected && (
        <mesh position={[0, -0.14, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.52, 0.60, 32]} />
          <meshBasicMaterial color="#38bdf8" side={THREE.DoubleSide} />
        </mesh>
      )}

      {/* 2. Main AMR Chassis (Industrial Powder-Coated Light Matte Aluminum) */}
      <mesh position={[0, 0, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.62, 0.18, 0.76]} />
        <meshStandardMaterial
          color={isFailed ? "#991b1b" : "#f1f5f9"}
          metalness={0.6}
          roughness={0.25}
        />
      </mesh>

      {/* Robot-Specific Colored Accent Trim Strip */}
      <mesh position={[0, 0.091, 0]}>
        <boxGeometry args={[0.58, 0.01, 0.72]} />
        <meshStandardMaterial color={baseAccentColor} metalness={0.8} roughness={0.2} />
      </mesh>

      {/* 3. Front Optical Sensor / Headlight Bar */}
      <mesh position={[0, 0.02, 0.385]}>
        <boxGeometry args={[0.42, 0.05, 0.02]} />
        <meshBasicMaterial color={isFailed ? "#ef4444" : isMoving ? "#38bdf8" : "#94a3b8"} />
      </mesh>

      {/* Rear Brake/Status Light Bar */}
      <mesh position={[0, 0.02, -0.385]}>
        <boxGeometry args={[0.42, 0.05, 0.02]} />
        <meshBasicMaterial color={isCharging ? "#c084fc" : "#ef4444"} />
      </mesh>

      {/* 4. Drive Wheels Group */}
      <group ref={wheelsRef}>
        <mesh position={[-0.32, -0.04, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.10, 0.10, 0.06, 16]} />
          <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.3} />
        </mesh>
        <mesh position={[0.32, -0.04, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.10, 0.10, 0.06, 16]} />
          <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.3} />
        </mesh>
      </group>

      {/* Front & Rear Castor Gliders */}
      <mesh position={[0, -0.10, 0.28]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshStandardMaterial color="#475569" metalness={0.9} roughness={0.1} />
      </mesh>
      <mesh position={[0, -0.10, -0.28]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshStandardMaterial color="#475569" metalness={0.9} roughness={0.1} />
      </mesh>

      {/* 5. Top Center Rotating LiDAR Mast */}
      <mesh position={[0, 0.14, 0.18]}>
        <cylinderGeometry args={[0.05, 0.05, 0.08, 16]} />
        <meshStandardMaterial color="#334155" metalness={0.8} roughness={0.2} />
      </mesh>
      <mesh ref={lidarRef} position={[0, 0.19, 0.18]}>
        <cylinderGeometry args={[0.07, 0.07, 0.04, 16]} />
        <meshStandardMaterial color="#0284c7" emissive="#38bdf8" emissiveIntensity={0.5} />
      </mesh>

      {/* 6. Cargo Payload Pod (Visibly mounted when transporting item) */}
      {robot.carrying_item && (
        <group position={[0, 0.22, -0.10]}>
          <mesh castShadow receiveShadow>
            <boxGeometry args={[0.48, 0.24, 0.48]} />
            <meshStandardMaterial color="#0284c7" metalness={0.4} roughness={0.4} />
          </mesh>
          <mesh position={[0, 0.125, 0]}>
            <boxGeometry args={[0.50, 0.02, 0.50]} />
            <meshStandardMaterial color="#f59e0b" roughness={0.6} />
          </mesh>
        </group>
      )}

      {/* 7. Clean, Compact Holographic AMR Label (Non-obstructive) */}
      <Html position={[0, 0.65, 0]} center distanceFactor={14}>
        <div
          className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md border text-[9px] font-mono font-black shadow-lg backdrop-blur-md pointer-events-none select-none transition-all duration-200 ${getStatusBorder()} ${
            isSelected ? "scale-110 ring-1 ring-sky-400" : "opacity-90"
          }`}
        >
          {/* Robot ID */}
          <span className="text-white font-extrabold">{robot.id}</span>

          {/* Transient Status indicator (only shown briefly for 2s during transitions) */}
          {transientStatus && (
            <span className="text-[8px] px-1 py-0.2 rounded bg-sky-900 text-sky-200 font-bold uppercase animate-pulse">
              {transientStatus}
            </span>
          )}

          {/* Fault Indicator */}
          {isFailed && (
            <span className="text-[8px] text-rose-300 font-bold uppercase animate-pulse">
              FAULT
            </span>
          )}
        </div>
      </Html>
    </group>
  );
};
