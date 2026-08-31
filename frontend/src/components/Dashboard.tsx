/**
 * Dashboard: Hero 3D Warehouse Digital Twin & Autonomous Fleet Operations Center
 * Connected to authoritative live simulation telemetry state and genuine Stop-and-Go baseline runner.
 */

import React, { useState, useEffect } from "react";
import {
  Bot,
  Package,
  Radio,
  Scale,
  Calendar,
  RadioTower,
} from "lucide-react";
import { useSimulationSocket } from "../hooks/useSimulationSocket";
import { useRobotState } from "../hooks/useRobotState";
import { SimulationControls } from "./SimulationControls";
import { TaskPanel } from "./TaskPanel";
import { MetricsPanel } from "./MetricsPanel";
import { EventLog } from "./EventLog";
import { CommunicationPanel } from "./CommunicationPanel";
import { ComparisonPanel } from "./ComparisonPanel";
import { RobotInspector } from "./RobotInspector";
import { Warehouse3D } from "../3d/Warehouse3D";
import { BenchmarkResult, executeBenchmark } from "../services/localSimulationEngine";

export const Dashboard: React.FC = () => {
  const {
    telemetry,
    availableScenarios,
    selectedScenario,
    activeSpeed,
    setActiveSpeed,
    controls,
  } = useSimulationSocket();

  const {
    robots,
    selectedRobotId,
    selectedRobot,
    setSelectedRobotId,
  } = useRobotState(telemetry.robots);

  const [activeTab, setActiveTab] = useState<"FLEET" | "TASKS" | "P2P" | "EVENTS" | "BENCHMARK">("BENCHMARK");
  const [viewMode, setViewMode] = useState<"3d" | "2d">("3d");
  const [showReservations, setShowReservations] = useState(true);

  // Genuine Benchmark Execution State
  const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkResult | null>(null);
  const [benchmarkStatus, setBenchmarkStatus] = useState<string | null>(null);

  const isCompleted =
    telemetry.status === "completed" ||
    (telemetry.tasks.length > 0 &&
      telemetry.metrics.total_tasks_completed === telemetry.tasks.length);

  const handleRunBenchmark = async () => {
    try {
      setBenchmarkStatus("BENCHMARK RUNNING");
      const liveEngine = controls.getLiveEngine();
      const res = await executeBenchmark(
        selectedScenario,
        48291,
        (status: string) => {
          setBenchmarkStatus(status);
        },
        liveEngine
      );
      setBenchmarkResult(res);
    } catch (err) {
      console.error("Benchmark error:", err);
      setBenchmarkStatus("BENCHMARK FAILED");
    }
  };

  // Reset benchmark on scenario change to avoid stale comparison data
  useEffect(() => {
    setBenchmarkResult(null);
    setBenchmarkStatus("BENCHMARK NOT RUN");
  }, [selectedScenario]);

  // When live simulation reaches 100% completion, sync benchmark with the exact completed live run
  useEffect(() => {
    if (isCompleted) {
      const liveEngine = controls.getLiveEngine();
      setBenchmarkStatus("BENCHMARK RUNNING");
      executeBenchmark(selectedScenario, 48291, undefined, liveEngine)
        .then((res) => {
          setBenchmarkResult(res);
          setBenchmarkStatus("BENCHMARK COMPLETE");
        })
        .catch(() => {
          setBenchmarkStatus("BENCHMARK FAILED");
        });
    }
  }, [isCompleted]);

  // Default to selected robot or R1
  const currentSelectedRobot = selectedRobot || robots.find((r) => r.id === selectedRobotId) || robots[0];

  // Sim time formatter
  const formatSimTime = (ticks: number) => {
    const totalSecs = ticks * 0.5;
    const mins = Math.floor(totalSecs / 60);
    const secs = (totalSecs % 60).toFixed(1);
    return `${mins.toString().padStart(2, "0")}:${secs.padStart(4, "0")}`;
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden select-none font-sans">
      {/* 1. TOP HEADER */}
      <header className="h-12 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between shrink-0 font-mono text-xs shadow-md">
        {/* Brand & Subtitle */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-7 h-7 rounded-lg bg-sky-600 border border-sky-400 flex items-center justify-center text-white shadow-lg shadow-sky-950">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-black tracking-wider text-white leading-none">
              D-FLEET
            </h1>
            <p className="text-[9px] text-slate-400 font-medium tracking-tight">
              Decentralized Multi-Robot Coordination System
            </p>
          </div>
        </div>

        {/* Compact System Telemetry Stat Row */}
        <div className="hidden md:flex items-center gap-5 text-xs">
          <div className="flex flex-col items-center">
            <span className="text-[9px] text-slate-400 font-extrabold tracking-wider">SIMULATION</span>
            <span
              className={`font-black tracking-wide ${
                isCompleted
                  ? "text-purple-400"
                  : telemetry.status === "running"
                  ? "text-emerald-400"
                  : telemetry.status === "paused"
                  ? "text-amber-400"
                  : "text-slate-300"
              }`}
            >
              {isCompleted ? "COMPLETED" : telemetry.status.toUpperCase()}
            </span>
          </div>

          <div className="w-px h-5 bg-slate-800" />

          <div className="flex flex-col items-center">
            <span className="text-[9px] text-slate-400 font-extrabold tracking-wider">TICK</span>
            <span className="text-white font-bold">{telemetry.tick}</span>
          </div>

          <div className="w-px h-5 bg-slate-800" />

          <div className="flex flex-col items-center">
            <span className="text-[9px] text-slate-400 font-extrabold tracking-wider">SIM TIME</span>
            <span className="text-white font-bold">{formatSimTime(telemetry.tick)}</span>
          </div>

          <div className="w-px h-5 bg-slate-800" />

          <div className="flex flex-col items-center">
            <span className="text-[9px] text-slate-400 font-extrabold tracking-wider">SCENARIO</span>
            <select
              value={selectedScenario}
              onChange={(e) => controls.loadScenario(e.target.value)}
              className="bg-transparent text-white font-bold text-xs cursor-pointer focus:outline-none"
            >
              {availableScenarios.map((sc) => (
                <option key={sc} value={sc} className="bg-slate-900 text-white">
                  {sc.replace(".json", "").toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {selectedScenario === "random.json" && (
            <>
              <div className="w-px h-5 bg-slate-800" />
              <div className="flex items-center gap-2 bg-indigo-950/80 border border-indigo-500/50 px-2.5 py-1 rounded-lg">
                <span className="text-[10px] text-indigo-300 font-black tracking-wider">RANDOM SCENARIO</span>
                <span className="text-[10px] text-slate-300">Seed: <strong className="text-white">{controls.getLiveEngine().getSeed()}</strong></span>
                <button
                  onClick={() => controls.randomizeScenario()}
                  title="Generate New Random Scenario"
                  className="flex items-center gap-1 bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-0.5 rounded text-[10px] font-bold transition-all shadow-sm cursor-pointer active:scale-95"
                >
                  <span>🎲 Randomize</span>
                </button>
              </div>
            </>
          )}

          <div className="w-px h-5 bg-slate-800" />

          <div className="flex flex-col items-center">
            <span className="text-[9px] text-slate-400 font-extrabold tracking-wider">ROBOTS</span>
            <span className="text-white font-bold">{robots.length}</span>
          </div>

          <div className="w-px h-5 bg-slate-800" />

          <div className="flex flex-col items-center">
            <span className="text-[9px] text-slate-400 font-extrabold tracking-wider">TASKS</span>
            <span className="text-white font-bold">{telemetry.tasks.length}</span>
          </div>

          <div className="w-px h-5 bg-slate-800" />

          <div className="flex flex-col items-center">
            <span className="text-[9px] text-slate-400 font-extrabold tracking-wider">OBSTACLES</span>
            <span className="text-white font-bold">{telemetry.obstacles.length}</span>
          </div>

          <div className="w-px h-5 bg-slate-800" />

          <div className="flex flex-col items-center">
            <span className="text-[9px] text-slate-400 font-extrabold tracking-wider">MODE</span>
            <span className="text-cyan-300 font-bold">DECENTRALIZED</span>
          </div>
        </div>

        {/* Far Right: Active Indicator */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full font-bold text-[11px] shadow-sm ${
            isCompleted
              ? "bg-purple-950/80 border border-purple-600 text-purple-300"
              : telemetry.status === "running"
              ? "bg-cyan-950/80 border border-cyan-700 text-cyan-300"
              : "bg-slate-900 border border-slate-700 text-slate-400"
          }`}
        >
          <RadioTower className={`w-3.5 h-3.5 ${telemetry.status === "running" ? "animate-pulse text-cyan-400" : ""}`} />
          <span>{isCompleted ? "SIMULATION COMPLETE" : telemetry.status === "running" ? "SIMULATION ACTIVE" : "SIMULATION PAUSED"}</span>
        </div>
      </header>

      {/* 2. SECOND CONTROL TOOLBAR */}
      <section className="px-4 py-1.5 shrink-0">
        <SimulationControls
          status={telemetry.status}
          currentTick={telemetry.tick}
          availableScenarios={availableScenarios}
          selectedScenario={selectedScenario}
          speed={activeSpeed}
          viewMode={viewMode}
          showReservations={showReservations}
          robots={robots}
          onStart={controls.start}
          onPause={controls.pause}
          onReset={controls.reset}
          onStep={controls.step}
          onSelectScenario={controls.loadScenario}
          onChangeSpeed={setActiveSpeed}
          onToggleViewMode={() => setViewMode((v) => (v === "3d" ? "2d" : "3d"))}
          onToggleReservations={() => setShowReservations((r) => !r)}
          onInjectFailure={controls.injectFailure}
        />
      </section>

      {/* 3. MAIN HERO WORKSPACE (DOMINANT 3D WAREHOUSE 72% / OPERATIONS PANEL 28%) */}
      <div className="flex-1 flex min-h-0 px-4 py-1 gap-3 overflow-hidden">
        {/* Left: Dominant 3D Warehouse Hero Canvas */}
        <main className="w-[70%] lg:w-[72%] flex flex-col h-full">
          <Warehouse3D
            telemetry={telemetry}
            selectedRobotId={selectedRobotId || (currentSelectedRobot ? currentSelectedRobot.id : null)}
            onSelectRobot={(id) =>
              setSelectedRobotId((prev) => (prev === id ? null : id))
            }
            viewMode={viewMode}
            showReservations={showReservations}
          />
        </main>

        {/* Right: Tabbed Operations Panel (Single Source for Benchmark, Fleet, Tasks, P2P, Events) */}
        <aside className="w-[30%] lg:w-[28%] flex flex-col h-full min-h-0 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-2.5 font-mono text-xs z-10 pointer-events-auto overflow-hidden">
          {/* Tab Header Strip */}
          <div className="flex items-center gap-1 p-1 bg-slate-950/80 border border-slate-800 rounded-lg shrink-0 mb-2">
            <button
              onClick={() => setActiveTab("FLEET")}
              className={`flex-1 py-1 text-[11px] font-bold rounded transition-all flex items-center justify-center gap-1 cursor-pointer ${
                activeTab === "FLEET"
                  ? "bg-sky-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Bot className="w-3 h-3" /> FLEET
            </button>
            <button
              onClick={() => setActiveTab("TASKS")}
              className={`flex-1 py-1 text-[11px] font-bold rounded transition-all flex items-center justify-center gap-1 cursor-pointer ${
                activeTab === "TASKS"
                  ? "bg-sky-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Package className="w-3 h-3" /> TASKS
            </button>
            <button
              onClick={() => setActiveTab("P2P")}
              className={`flex-1 py-1 text-[11px] font-bold rounded transition-all flex items-center justify-center gap-1 cursor-pointer ${
                activeTab === "P2P"
                  ? "bg-sky-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Radio className="w-3 h-3" /> P2P
            </button>
            <button
              onClick={() => setActiveTab("EVENTS")}
              className={`flex-1 py-1 text-[11px] font-bold rounded transition-all flex items-center justify-center gap-1 cursor-pointer ${
                activeTab === "EVENTS"
                  ? "bg-sky-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Calendar className="w-3 h-3" /> EVENTS
            </button>
            <button
              onClick={() => setActiveTab("BENCHMARK")}
              className={`flex-1 py-1 text-[11px] font-bold rounded transition-all flex items-center justify-center gap-1 cursor-pointer ${
                activeTab === "BENCHMARK"
                  ? "bg-sky-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Scale className="w-3 h-3" /> BENCHMARK
            </button>
          </div>

          {/* Tab Body Container with clean bounded layout */}
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            {activeTab === "FLEET" && currentSelectedRobot && (
              <RobotInspector
                robot={currentSelectedRobot}
                selectedRobotId={selectedRobotId || currentSelectedRobot.id}
                onSelectRobot={(id) => setSelectedRobotId(id)}
                totalReservationsCount={telemetry.reservations.length}
                recentMessages={telemetry.recent_messages}
                allRobots={telemetry.robots}
                allTasks={telemetry.tasks}
                onClose={() => setSelectedRobotId(null)}
              />
            )}
            {activeTab === "TASKS" && <TaskPanel tasks={telemetry.tasks} />}
            {activeTab === "P2P" && (
              <CommunicationPanel
                recentMessages={telemetry.recent_messages}
                totalSent={telemetry.metrics.messages_sent}
                totalReceived={telemetry.metrics.messages_received}
                totalDropped={telemetry.metrics.messages_dropped}
              />
            )}
            {activeTab === "EVENTS" && <EventLog events={telemetry.events} />}
            {activeTab === "BENCHMARK" && (
              <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-1 select-text overscroll-contain">
                <ComparisonPanel
                  metrics={telemetry.metrics}
                  benchmarkResult={benchmarkResult}
                  benchmarkStatus={benchmarkStatus}
                  onRunBenchmark={handleRunBenchmark}
                  selectedScenario={selectedScenario}
                />
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* 4. PRIMARY KPI METRIC ROW DIRECTLY UNDERNEATH MAIN WORKSPACE (FULL WIDTH) */}
      <section className="px-4 py-2 shrink-0 border-t border-slate-800/80 bg-slate-950/90">
        <MetricsPanel metrics={telemetry.metrics} />
      </section>
    </div>
  );
};
