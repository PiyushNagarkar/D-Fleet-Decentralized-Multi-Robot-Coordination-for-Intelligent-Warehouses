/**
 * StationModel: Modern 3D Pickup, Delivery, and Charging Station Platforms
 * Features high-contrast floor pads, 3D cargo containers, roller conveyors, and induction charging coils.
 */

import React from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { gridToWorld } from "../utils/coordinate";

export type StationType = "PICKUP" | "DELIVERY" | "CHARGING" | "INTERSECTION";

interface StationModelProps {
  x: number;
  y: number;
  type: StationType;
  label?: string;
}

export const StationModel: React.FC<StationModelProps> = ({
  x,
  y,
  type,
  label,
}) => {
  const [wx, , wz] = gridToWorld(x, y, 0);

  const getStationConfig = () => {
    switch (type) {
      case "PICKUP":
        return {
          padColor: "#0284c7",
          borderColor: "#38bdf8",
          title: "PICKUP ZONE",
          code: label || "P1",
          borderBadge: "border-sky-400",
          bgBadge: "bg-sky-950/90 text-sky-200",
        };
      case "DELIVERY":
        return {
          padColor: "#16a34a",
          borderColor: "#4ade80",
          title: "DELIVERY DROP",
          code: label || "D1",
          borderBadge: "border-emerald-400",
          bgBadge: "bg-emerald-950/90 text-emerald-200",
        };
      case "CHARGING":
        return {
          padColor: "#9333ea",
          borderColor: "#c084fc",
          title: "CHARGE PAD",
          code: label || "C1",
          borderBadge: "border-purple-400",
          bgBadge: "bg-purple-950/90 text-purple-200",
        };
      default:
        return {
          padColor: "#475569",
          borderColor: "#94a3b8",
          title: "STATION",
          code: label || "S1",
          borderBadge: "border-slate-400",
          bgBadge: "bg-slate-900/90 text-slate-200",
        };
    }
  };

  const config = getStationConfig();

  return (
    <group position={[wx, 0.01, wz]}>
      {/* 1. Base Ground Pad */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[1.2, 1.2]} />
        <meshStandardMaterial
          color={config.padColor}
          transparent
          opacity={0.35}
          roughness={0.3}
          metalness={0.1}
        />
      </mesh>

      {/* 2. Illuminated Glowing Border Strip */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <ringGeometry args={[0.55, 0.60, 4]} />
        <meshBasicMaterial color={config.borderColor} side={THREE.DoubleSide} />
      </mesh>

      {/* 3. Station-Specific Physical Geometry */}
      {type === "PICKUP" && (
        <group position={[0, 0.1, 0]}>
          {/* Wooden Pallet Base */}
          <mesh position={[0, 0.04, 0]} castShadow receiveShadow>
            <boxGeometry args={[0.7, 0.08, 0.7]} />
            <meshStandardMaterial color="#b45309" roughness={0.8} />
          </mesh>
          {/* Stacked Cargo Box A */}
          <mesh position={[-0.15, 0.22, -0.15]} castShadow receiveShadow>
            <boxGeometry args={[0.32, 0.26, 0.32]} />
            <meshStandardMaterial color="#0284c7" roughness={0.6} metalness={0.2} />
          </mesh>
          {/* Stacked Cargo Box B */}
          <mesh position={[0.15, 0.20, 0.15]} castShadow receiveShadow>
            <boxGeometry args={[0.28, 0.22, 0.28]} />
            <meshStandardMaterial color="#d97706" roughness={0.7} />
          </mesh>
        </group>
      )}

      {type === "DELIVERY" && (
        <group position={[0, 0.05, 0]}>
          {/* Automated Roller Conveyor Rails */}
          <mesh position={[-0.32, 0.06, 0]} castShadow>
            <boxGeometry args={[0.06, 0.12, 0.8]} />
            <meshStandardMaterial color="#64748b" metalness={0.8} roughness={0.3} />
          </mesh>
          <mesh position={[0.32, 0.06, 0]} castShadow>
            <boxGeometry args={[0.06, 0.12, 0.8]} />
            <meshStandardMaterial color="#64748b" metalness={0.8} roughness={0.3} />
          </mesh>
          {/* Conveyor Bed */}
          <mesh position={[0, 0.04, 0]}>
            <boxGeometry args={[0.58, 0.04, 0.76]} />
            <meshStandardMaterial color="#334155" metalness={0.6} roughness={0.5} />
          </mesh>
        </group>
      )}

      {type === "CHARGING" && (
        <group position={[0, 0.02, 0]}>
          {/* Wireless Inductive Charging Ring */}
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.25, 0.38, 32]} />
            <meshBasicMaterial color="#c084fc" />
          </mesh>
          {/* Center Power Core */}
          <mesh position={[0, 0.02, 0]}>
            <cylinderGeometry args={[0.12, 0.12, 0.04, 16]} />
            <meshStandardMaterial color="#7e22ce" metalness={0.9} roughness={0.2} emissive="#a855f7" emissiveIntensity={0.6} />
          </mesh>
        </group>
      )}

      {/* 4. Floating Holographic Station Sign */}
      <Html position={[0, 0.95, 0]} center distanceFactor={14}>
        <div className="flex flex-col items-center pointer-events-none select-none font-mono">
          <div
            className={`px-2 py-0.5 rounded-full border text-[10px] font-black uppercase tracking-wider shadow-lg flex items-center gap-1 backdrop-blur-md ${config.borderBadge} ${config.bgBadge}`}
          >
            <span>{type === "PICKUP" ? "📦" : type === "DELIVERY" ? "🎯" : "⚡"}</span>
            <span>{config.code}</span>
          </div>
        </div>
      </Html>
    </group>
  );
};
