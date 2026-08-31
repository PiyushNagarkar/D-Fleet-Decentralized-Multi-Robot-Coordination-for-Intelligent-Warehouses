/**
 * ShelfModel: Modern Industrial Warehouse Pallet Racking System
 * Clean light-gray industrial steel frame with multi-tier storage decks and diverse colored cartons.
 */

import React from "react";
import { gridToWorld } from "../utils/coordinate";

interface ShelfModelProps {
  x: number;
  y: number;
  height?: number;
}

export const ShelfModel: React.FC<ShelfModelProps> = ({
  x,
  y,
  height = 1.6,
}) => {
  const [wx, , wz] = gridToWorld(x, y, 0);

  return (
    <group position={[wx, 0, wz]}>
      {/* 1. Industrial Steel Upright Corner Posts (Light-Gray Powder-Coated Metal) */}
      <mesh position={[-0.38, height / 2, -0.38]} castShadow receiveShadow>
        <boxGeometry args={[0.04, height, 0.04]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.7} roughness={0.3} />
      </mesh>
      <mesh position={[0.38, height / 2, -0.38]} castShadow receiveShadow>
        <boxGeometry args={[0.04, height, 0.04]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.7} roughness={0.3} />
      </mesh>
      <mesh position={[-0.38, height / 2, 0.38]} castShadow receiveShadow>
        <boxGeometry args={[0.04, height, 0.04]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.7} roughness={0.3} />
      </mesh>
      <mesh position={[0.38, height / 2, 0.38]} castShadow receiveShadow>
        <boxGeometry args={[0.04, height, 0.04]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.7} roughness={0.3} />
      </mesh>

      {/* Cross Bracing Bars */}
      <mesh position={[0, height / 2, -0.38]} rotation={[0, 0, 0.6]}>
        <boxGeometry args={[0.02, height * 1.1, 0.02]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.5} roughness={0.4} />
      </mesh>
      <mesh position={[0, height / 2, 0.38]} rotation={[0, 0, -0.6]}>
        <boxGeometry args={[0.02, height * 1.1, 0.02]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.5} roughness={0.4} />
      </mesh>

      {/* 2. Steel Shelf Beam Decks (Tier 1, Tier 2, Tier 3) */}
      <mesh position={[0, 0.06, 0]} receiveShadow>
        <boxGeometry args={[0.82, 0.03, 0.82]} />
        <meshStandardMaterial color="#64748b" metalness={0.6} roughness={0.4} />
      </mesh>
      <mesh position={[0, 0.78, 0]} receiveShadow>
        <boxGeometry args={[0.82, 0.03, 0.82]} />
        <meshStandardMaterial color="#64748b" metalness={0.6} roughness={0.4} />
      </mesh>
      <mesh position={[0, height, 0]}>
        <boxGeometry args={[0.82, 0.03, 0.82]} />
        <meshStandardMaterial color="#64748b" metalness={0.6} roughness={0.4} />
      </mesh>

      {/* 3. Tier 1 Stocked Packages (Realistic Multi-Colored Logistics Cartons) */}
      {/* Box A: Kraft Brown Carton */}
      <mesh position={[-0.18, 0.40, -0.18]} castShadow receiveShadow>
        <boxGeometry args={[0.32, 0.55, 0.32]} />
        <meshStandardMaterial color="#d97706" roughness={0.8} metalness={0.05} />
      </mesh>
      {/* Box B: Industrial Blue Container */}
      <mesh position={[0.18, 0.36, -0.18]} castShadow receiveShadow>
        <boxGeometry args={[0.30, 0.48, 0.30]} />
        <meshStandardMaterial color="#2563eb" roughness={0.6} metalness={0.2} />
      </mesh>
      {/* Box C: Safety Yellow Carton */}
      <mesh position={[-0.18, 0.34, 0.18]} castShadow receiveShadow>
        <boxGeometry args={[0.30, 0.44, 0.30]} />
        <meshStandardMaterial color="#eab308" roughness={0.7} metalness={0.1} />
      </mesh>
      {/* Box D: Clean White / Gray Carton with Label */}
      <mesh position={[0.18, 0.42, 0.18]} castShadow receiveShadow>
        <boxGeometry args={[0.32, 0.60, 0.32]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.6} metalness={0.1} />
      </mesh>

      {/* 4. Tier 2 Stocked Packages */}
      {/* Box E: Emerald Green Carton */}
      <mesh position={[-0.18, 1.16, -0.18]} castShadow receiveShadow>
        <boxGeometry args={[0.30, 0.52, 0.30]} />
        <meshStandardMaterial color="#10b981" roughness={0.7} metalness={0.1} />
      </mesh>
      {/* Box F: Kraft Brown Carton */}
      <mesh position={[0.18, 1.12, -0.18]} castShadow receiveShadow>
        <boxGeometry args={[0.32, 0.44, 0.32]} />
        <meshStandardMaterial color="#b45309" roughness={0.8} metalness={0.05} />
      </mesh>
      {/* Box G: Industrial Gray Tote */}
      <mesh position={[-0.18, 1.10, 0.18]} castShadow receiveShadow>
        <boxGeometry args={[0.28, 0.40, 0.28]} />
        <meshStandardMaterial color="#475569" roughness={0.6} metalness={0.2} />
      </mesh>
      {/* Box H: High-Tech Cyan Carton */}
      <mesh position={[0.18, 1.18, 0.18]} castShadow receiveShadow>
        <boxGeometry args={[0.31, 0.58, 0.31]} />
        <meshStandardMaterial color="#0284c7" roughness={0.6} metalness={0.2} />
      </mesh>

      {/* 5. Safety Yellow Crash Guard Base Trim */}
      <mesh position={[0, 0.02, 0.41]}>
        <boxGeometry args={[0.86, 0.04, 0.04]} />
        <meshStandardMaterial color="#eab308" metalness={0.3} roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.02, -0.41]}>
        <boxGeometry args={[0.86, 0.04, 0.04]} />
        <meshStandardMaterial color="#eab308" metalness={0.3} roughness={0.5} />
      </mesh>
    </group>
  );
};
