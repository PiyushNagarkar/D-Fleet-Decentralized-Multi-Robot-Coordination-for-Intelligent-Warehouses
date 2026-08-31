/**
 * DynamicObstacle: 3D Dynamic Warehouse Obstacles (Spills & Moving Forklifts)
 */

import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { gridToWorld } from "../utils/coordinate";
import { DynamicObstacle as ObstacleData } from "../types";

interface DynamicObstacleProps {
  obstacle: ObstacleData;
}

export const DynamicObstacleModel: React.FC<DynamicObstacleProps> = ({ obstacle }) => {
  const beaconRef = useRef<THREE.Mesh>(null);
  const [wx, , wz] = gridToWorld(obstacle.x, obstacle.y, 0);

  // Animated flashing beacon
  useFrame((state) => {
    if (beaconRef.current) {
      const pulse = (Math.sin(state.clock.elapsedTime * 8) + 1) / 2;
      beaconRef.current.scale.set(1 + pulse * 0.3, 1 + pulse * 0.3, 1 + pulse * 0.3);
    }
  });

  const isMoving = obstacle.type === "MOVING";

  return (
    <group position={[wx, 0, wz]}>
      {isMoving ? (
        /* Forklift / Moving Vehicle Model */
        <group position={[0, 0.3, 0]}>
          {/* Chassis */}
          <mesh castShadow position={[0, 0, 0]}>
            <boxGeometry args={[0.75, 0.38, 0.55]} />
            <meshStandardMaterial color="#ca8a04" roughness={0.3} metalness={0.6} />
          </mesh>

          {/* Protective Overhead Cage */}
          <mesh castShadow position={[-0.12, 0.34, 0]}>
            <boxGeometry args={[0.4, 0.38, 0.5]} />
            <meshStandardMaterial color="#0f172a" wireframe />
          </mesh>

          {/* Mast & Forks */}
          <mesh castShadow position={[0.4, 0.22, 0]}>
            <boxGeometry args={[0.09, 0.65, 0.44]} />
            <meshStandardMaterial color="#334155" metalness={0.7} />
          </mesh>
          <mesh position={[0.52, -0.12, 0]}>
            <boxGeometry args={[0.24, 0.04, 0.38]} />
            <meshStandardMaterial color="#020617" />
          </mesh>

          {/* Warning Flashing Beacon */}
          <mesh ref={beaconRef} position={[-0.12, 0.58, 0]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshBasicMaterial color="#f97316" />
          </mesh>

          {/* Floating Label */}
          <Html position={[0, 0.85, 0]} center distanceFactor={16}>
            <div className="px-2 py-0.5 rounded bg-yellow-950 border border-yellow-500 text-yellow-200 text-[10px] font-mono font-extrabold shadow-xl pointer-events-none whitespace-nowrap animate-pulse">
              ⚠ FORKLIFT TRAFFIC
            </div>
          </Html>
        </group>
      ) : (
        /* Static Spill / Safety Hazard Cone */
        <group position={[0, 0.02, 0]}>
          {/* Slick Oil Puddle */}
          <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
            <circleGeometry args={[0.45, 32]} />
            <meshStandardMaterial
              color="#451a03"
              roughness={0.05}
              metalness={0.95}
              transparent
              opacity={0.88}
            />
          </mesh>

          {/* Safety Hazard Cone */}
          <mesh position={[0, 0.2, 0]} castShadow>
            <coneGeometry args={[0.18, 0.4, 16]} />
            <meshStandardMaterial color="#ea580c" roughness={0.4} />
          </mesh>
          <mesh position={[0, 0.18, 0]}>
            <cylinderGeometry args={[0.14, 0.15, 0.08, 16]} />
            <meshBasicMaterial color="#ffffff" />
          </mesh>

          {/* Flashing Warning Beacon */}
          <mesh ref={beaconRef} position={[0, 0.44, 0]}>
            <sphereGeometry args={[0.06, 12, 12]} />
            <meshBasicMaterial color="#ff4400" />
          </mesh>

          {/* Floating Label */}
          <Html position={[0, 0.65, 0]} center distanceFactor={16}>
            <div className="px-2 py-0.5 rounded bg-orange-950 border border-orange-500 text-orange-200 text-[10px] font-mono font-extrabold shadow-xl pointer-events-none whitespace-nowrap animate-pulse">
              ⚠ OIL SPILL HAZARD
            </div>
          </Html>
        </group>
      )}
    </group>
  );
};
