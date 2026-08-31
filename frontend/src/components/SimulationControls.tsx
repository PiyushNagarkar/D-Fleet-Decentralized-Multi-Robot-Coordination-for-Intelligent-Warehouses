/**
 * SimulationControls: Top Control Toolbar
 * Controls: START/PAUSE, RESET, STEP, SPEED, 3D, RESERVATIONS, INJECT FAULT
 */

import React, { useState } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  StepForward,
  Box,
  Layers,
  AlertOctagon,
} from "lucide-react";
import { RobotTelemetry } from "../types";

interface SimulationControlsProps {
  status: "idle" | "running" | "paused" | "completed";
  currentTick: number;
  availableScenarios: string[];
  selectedScenario: string;
  speed: number;
  viewMode: "3d" | "2d";
  showReservations?: boolean;
  robots: RobotTelemetry[];
  onStart: () => void;
  onPause: () => void;
  onReset: () => void;
  onStep?: () => void;
  onSelectScenario: (scenarioId: string) => void;
  onChangeSpeed: (speed: number) => void;
  onToggleViewMode: () => void;
  onToggleReservations?: () => void;
  onInjectFailure: (robotId: string) => void;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  status,
  speed,
  viewMode,
  showReservations = true,
  robots,
  onStart,
  onPause,
  onReset,
  onStep,
  onChangeSpeed,
  onToggleViewMode,
  onToggleReservations,
  onInjectFailure,
}) => {
  const [showFailureModal, setShowFailureModal] = useState(false);
  const [selectedRobotForFailure, setSelectedRobotForFailure] = useState(
    robots[0]?.id || "R2"
  );

  const isRunning = status === "running";

  const handleTriggerFailure = (e: React.FormEvent) => {
    e.preventDefault();
    onInjectFailure(selectedRobotForFailure);
    setShowFailureModal(false);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-2 shadow-xl flex flex-wrap items-center justify-between gap-3 font-mono text-xs">
      {/* 1. Left: Pause / Start / Reset / Step */}
      <div className="flex items-center gap-2">
        {isRunning ? (
          <button
            onClick={onPause}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-lg shadow transition-all active:scale-95 cursor-pointer"
          >
            <Pause className="w-3.5 h-3.5" />
            <span>PAUSE</span>
          </button>
        ) : (
          <button
            onClick={onStart}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg shadow-lg shadow-emerald-950 transition-all active:scale-95 cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>START</span>
          </button>
        )}

        <button
          onClick={onReset}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-950/80 hover:bg-slate-800 border border-slate-700 text-slate-300 hover:text-white rounded-lg transition-all cursor-pointer"
          title="Reset Simulation"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>RESET</span>
        </button>

        <button
          onClick={onStep || onStart}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-950/80 hover:bg-slate-800 border border-slate-700 text-slate-300 hover:text-white rounded-lg transition-all cursor-pointer"
          title="Step Simulation 1 Tick"
        >
          <StepForward className="w-3.5 h-3.5" />
          <span>STEP</span>
        </button>
      </div>

      {/* 2. Center: Speed + View + Reservations */}
      <div className="flex items-center gap-4">
        {/* Speed Selector */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 border border-slate-800 rounded-lg p-1">
          <span className="text-[10px] text-slate-400 font-bold px-1">SPEED</span>
          {[0.5, 1.0, 2.0, 5.0].map((s) => (
            <button
              key={s}
              onClick={() => onChangeSpeed(s)}
              className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                speed === s
                  ? "bg-sky-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* 3D / 2D Toggle */}
        <button
          onClick={onToggleViewMode}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-bold transition-all cursor-pointer ${
            viewMode === "3d"
              ? "bg-sky-950/80 border-sky-600 text-sky-300"
              : "bg-slate-950/80 border-slate-700 text-slate-400"
          }`}
        >
          <Box className="w-3.5 h-3.5" />
          <span>{viewMode.toUpperCase()}</span>
        </button>

        {/* Spacetime Reservations Toggle */}
        <button
          onClick={onToggleReservations}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-bold transition-all cursor-pointer ${
            showReservations
              ? "bg-purple-950/80 border-purple-600 text-purple-300"
              : "bg-slate-950/80 border-slate-700 text-slate-400"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>RESERVATIONS</span>
        </button>
      </div>

      {/* 3. Right: INJECT FAULT ONLY */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setShowFailureModal(true)}
          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-rose-950/60 hover:bg-rose-900/80 border border-rose-600 text-rose-300 font-bold rounded-lg shadow-sm transition-all cursor-pointer"
        >
          <AlertOctagon className="w-3.5 h-3.5" />
          <span>INJECT FAULT</span>
        </button>
      </div>

      {/* Modal: Inject Robot Failure */}
      {showFailureModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-rose-500 rounded-xl p-5 w-80 shadow-2xl space-y-4 font-mono text-xs">
            <h3 className="text-sm font-bold text-rose-300 flex items-center gap-2">
              <AlertOctagon className="w-4 h-4" /> Inject Robot Hardware Fault
            </h3>
            <form onSubmit={handleTriggerFailure} className="space-y-3">
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">Target Robot AMR</label>
                <select
                  value={selectedRobotForFailure}
                  onChange={(e) => setSelectedRobotForFailure(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-white font-bold"
                >
                  {robots.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.id} ({r.status} - {Math.round(r.battery)}%)
                    </option>
                  ))}
                </select>
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">
                Simulates motor controller or hardware fault. Peer AMRs detect missing heartbeat and autonomously rescue active tasks.
              </p>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowFailureModal(false)}
                  className="px-3 py-1 bg-slate-800 text-slate-300 rounded hover:bg-slate-700 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3 py-1 bg-rose-600 text-white rounded font-bold hover:bg-rose-500 cursor-pointer"
                >
                  Trigger Fault
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
