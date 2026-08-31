/**
 * CommunicationGraph: Transient High-Legibility P2P Connection Links
 * Renders sleek, unobtrusive laser connections between communicating AMRs without large text bubbles.
 */

import React, { useState, useEffect } from "react";
import { Line } from "@react-three/drei";
import { gridToWorld, getRobotColor } from "../utils/coordinate";
import { CommunicationEvent, RobotTelemetry } from "../types";

interface TransientBeam {
  id: string;
  from: string;
  to: string;
  type: string;
  fromPos: [number, number, number];
  toPos: [number, number, number];
  color: string;
  createdAt: number;
}

interface CommunicationGraphProps {
  recentMessages: CommunicationEvent[];
  robots: RobotTelemetry[];
}

export const CommunicationGraph: React.FC<CommunicationGraphProps> = ({
  recentMessages,
  robots,
}) => {
  const [activeBeams, setActiveBeams] = useState<TransientBeam[]>([]);

  useEffect(() => {
    if (!recentMessages || recentMessages.length === 0) return;

    const robotPosMap = new Map<string, [number, number]>();
    robots.forEach((r) => robotPosMap.set(r.id, r.position));

    const now = Date.now();
    const newBeams: TransientBeam[] = [];

    // Ingest recent message events
    recentMessages.slice(-5).forEach((msg) => {
      const fromGrid = robotPosMap.get(msg.from);
      const toGrid = msg.to ? robotPosMap.get(msg.to) : null;

      if (fromGrid && toGrid && msg.from !== msg.to) {
        const fromPos = gridToWorld(fromGrid[0], fromGrid[1], 0.25);
        const toPos = gridToWorld(toGrid[0], toGrid[1], 0.25);

        newBeams.push({
          id: `${msg.id || msg.from}_${msg.to}_${msg.tick}_${now}_${Math.random()}`,
          from: msg.from,
          to: msg.to,
          type: msg.type,
          fromPos,
          toPos,
          color: getRobotColor(msg.from),
          createdAt: now,
        });
      }
    });

    if (newBeams.length > 0) {
      setActiveBeams((prev) => {
        const merged = [...prev, ...newBeams];
        return merged.slice(-6);
      });
    }
  }, [recentMessages, robots]);

  // Clean up expired laser links after 1.4 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      setActiveBeams((prev) => prev.filter((b) => now - b.createdAt < 1400));
    }, 200);

    return () => clearInterval(timer);
  }, []);

  return (
    <group>
      {activeBeams.map((beam) => (
        <Line
          key={beam.id}
          points={[beam.fromPos, beam.toPos]}
          color={beam.color}
          lineWidth={2.5}
          transparent
          opacity={0.85}
        />
      ))}
    </group>
  );
};
