/**
 * PathRenderer: High-Visibility 3D Trajectories, Spacetime Reservations & Pulsating Conflict Zones
 */

import React from "react";
import { Line, Html } from "@react-three/drei";
import * as THREE from "three";
import { gridToWorld, getRobotColor } from "../utils/coordinate";
import { RobotTelemetry } from "../types";

interface PathRendererProps {
  robots: RobotTelemetry[];
  reservations?: Array<{ x: number; y: number; tick: number; owner: string; priority?: number }>;
  selectedRobotId?: string | null;
  showReservations?: boolean;
  showConflicts?: boolean;
  showPaths?: boolean;
}

export const PathRenderer: React.FC<PathRendererProps> = ({
  robots,
  reservations = [],
  selectedRobotId,
  showReservations = true,
  showConflicts = true,
  showPaths = true,
}) => {
  // Find potential intersection conflicts
  const conflictMap = new Map<string, string[]>();
  for (const r of robots) {
    if (r.current_path && r.current_path.length > 0) {
      const nextP = r.current_path[0];
      const key = `${nextP[0]},${nextP[1]}`;
      if (!conflictMap.has(key)) conflictMap.set(key, []);
      conflictMap.get(key)!.push(r.id);
    }
  }

  const conflicts: Array<{ x: number; y: number; robots: string[] }> = [];
  for (const [key, robotList] of conflictMap.entries()) {
    if (robotList.length > 1) {
      const [x, y] = key.split(",").map(Number);
      conflicts.push({ x, y, robots: robotList });
    }
  }

  return (
    <group>
      {/* 1. Planned Path Ribbons */}
      {showPaths &&
        robots.map((robot) => {
          if (!robot.current_path || robot.current_path.length === 0) return null;

          const isSelected = selectedRobotId === robot.id;
          const color = getRobotColor(robot.id);

          const points: [number, number, number][] = [
            gridToWorld(robot.position[0], robot.position[1], 0.1),
            ...robot.current_path.map((pos) => gridToWorld(pos[0], pos[1], 0.1)),
          ];

          return (
            <group key={`path_${robot.id}`}>
              {/* Glowing Path Line */}
              <Line
                points={points}
                color={color}
                lineWidth={isSelected ? 5 : 3}
                dashed={false}
                transparent
                opacity={isSelected ? 0.95 : 0.7}
              />

              {/* Waypoint Waymarkers */}
              {robot.current_path.map((pos, idx) => {
                const [wx, wy, wz] = gridToWorld(pos[0], pos[1], 0.04);
                return (
                  <mesh key={`wp_${robot.id}_${idx}`} position={[wx, wy, wz]} rotation={[-Math.PI / 2, 0, 0]}>
                    <circleGeometry args={[0.12, 16]} />
                    <meshBasicMaterial
                      color={color}
                      transparent
                      opacity={Math.max(0.3, 0.85 - idx * 0.07)}
                      side={THREE.DoubleSide}
                    />
                  </mesh>
                );
              })}
            </group>
          );
        })}

      {/* 2. Spacetime Reservations Floor Markers (Orange Tint) */}
      {showReservations &&
        reservations.map((res, idx) => {
          const [wx, wy, wz] = gridToWorld(res.x, res.y, 0.02);

          return (
            <group key={`res_${idx}_${res.owner}_${res.tick}`} position={[wx, wy, wz]}>
              <mesh rotation={[-Math.PI / 2, 0, 0]}>
                <planeGeometry args={[0.85, 0.85]} />
                <meshBasicMaterial
                  color="#f59e0b"
                  transparent
                  opacity={0.15}
                  side={THREE.DoubleSide}
                />
              </mesh>
              <mesh rotation={[-Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.36, 0.4, 4]} />
                <meshBasicMaterial
                  color="#f59e0b"
                  transparent
                  opacity={0.6}
                  side={THREE.DoubleSide}
                />
              </mesh>
            </group>
          );
        })}

      {/* 3. Pulsating Red Conflict Zones */}
      {showConflicts &&
        conflicts.map((conf, idx) => {
          const [wx, , wz] = gridToWorld(conf.x, conf.y, 0.03);

          return (
            <group key={`conflict_${idx}`} position={[wx, 0.03, wz]}>
              {/* Red Floor Highlight */}
              <mesh rotation={[-Math.PI / 2, 0, 0]}>
                <planeGeometry args={[1.2, 1.2]} />
                <meshBasicMaterial color="#ef4444" transparent opacity={0.35} />
              </mesh>
              <mesh rotation={[-Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.55, 0.6, 4]} />
                <meshBasicMaterial color="#f87171" side={THREE.DoubleSide} />
              </mesh>

              {/* Floating CONFLICT Badge */}
              <Html position={[0, 0.65, 0]} center distanceFactor={18}>
                <div className="flex items-center px-2 py-0.5 rounded bg-rose-950/95 border border-rose-500 text-rose-300 font-mono text-[10px] font-black tracking-widest uppercase shadow-2xl animate-pulse">
                  CONFLICT
                </div>
              </Html>
            </group>
          );
        })}
    </group>
  );
};
