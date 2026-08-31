/**
 * ComparisonPanel: D-Fleet vs Centralized Stop-and-Go Baseline Benchmark
 * Transparent, scientific comparison with accurate Advantage/Disadvantage labelling and live run audit.
 */

import React from "react";
import { Scale, Play, Loader2, TrendingUp, TrendingDown, Award, Info, Activity } from "lucide-react";
import { SimulationMetrics } from "../types";
import { BenchmarkResult } from "../services/localSimulationEngine";

interface ComparisonPanelProps {
  metrics?: SimulationMetrics;
  benchmarkResult?: BenchmarkResult | null;
  benchmarkStatus?: string | null;
  onRunBenchmark?: () => void;
  selectedScenario?: string;
}

export const ComparisonPanel: React.FC<ComparisonPanelProps> = ({
  benchmarkResult,
  benchmarkStatus,
  onRunBenchmark,
  selectedScenario = "complete_demo.json",
}) => {
  const isRunning =
    benchmarkStatus &&
    benchmarkStatus !== "BENCHMARK COMPLETE" &&
    benchmarkStatus !== "NOT RUN";

  const isBothCompleted =
    benchmarkResult &&
    benchmarkResult.dFleetResult?.completed &&
    benchmarkResult.baselineResult?.completed;

  const overallImprovement = benchmarkResult?.comparison?.overall_improvement ?? null;

  const rows = benchmarkResult
    ? [
        {
          metric: "Completion Time",
          dfleet: benchmarkResult.dFleetResult?.completed
            ? `${benchmarkResult.dFleetResult.completionTick} ticks`
            : `${benchmarkResult.decentralized.completion_time} ticks`,
          baseline: benchmarkResult.baselineResult?.completed
            ? `${benchmarkResult.baselineResult.completionTick} ticks`
            : `INCOMPLETE (timeout at ${benchmarkResult.baselineResult?.timeoutTick || 500})`,
          advantage:
            benchmarkResult.comparison.completion_time_improvement !== null
              ? benchmarkResult.comparison.completion_time_improvement >= 0
                ? `+${benchmarkResult.comparison.completion_time_improvement.toFixed(1)}% (Faster)`
                : `${benchmarkResult.comparison.completion_time_improvement.toFixed(1)}% (${Math.abs(
                    benchmarkResult.comparison.completion_time_improvement
                  ).toFixed(1)}% Slower)`
              : "N/A",
          isPositive: (benchmarkResult.comparison.completion_time_improvement ?? 0) >= 0,
          isNA: benchmarkResult.comparison.completion_time_improvement === null,
        },
        {
          metric: "Avg Waiting Time",
          dfleet: `${benchmarkResult.decentralized.waiting_time.toFixed(1)} ticks`,
          baseline: `${benchmarkResult.baseline.waiting_time.toFixed(1)} ticks`,
          advantage:
            benchmarkResult.comparison.waiting_time_improvement !== null
              ? benchmarkResult.comparison.waiting_time_improvement >= 0
                ? `+${benchmarkResult.comparison.waiting_time_improvement.toFixed(1)}% (Less)`
                : `${benchmarkResult.comparison.waiting_time_improvement.toFixed(1)}% (${Math.abs(
                    benchmarkResult.comparison.waiting_time_improvement
                  ).toFixed(1)}% More)`
              : "N/A",
          isPositive: (benchmarkResult.comparison.waiting_time_improvement ?? 0) >= 0,
          isNA: benchmarkResult.comparison.waiting_time_improvement === null,
        },
        {
          metric: "Conflicts / Stops",
          dfleet: `${benchmarkResult.decentralized.conflicts}`,
          baseline: `${benchmarkResult.baseline.conflicts}`,
          advantage:
            benchmarkResult.comparison.conflict_improvement !== null
              ? benchmarkResult.comparison.conflict_improvement >= 0
                ? `+${benchmarkResult.comparison.conflict_improvement.toFixed(1)}% (Fewer)`
                : `${benchmarkResult.comparison.conflict_improvement.toFixed(1)}% (${Math.abs(
                    benchmarkResult.comparison.conflict_improvement
                  ).toFixed(1)}% More)`
              : "N/A",
          isPositive: (benchmarkResult.comparison.conflict_improvement ?? 0) >= 0,
          isNA: benchmarkResult.comparison.conflict_improvement === null,
        },
        {
          metric: "Task Throughput",
          dfleet: `${(benchmarkResult.decentralized.throughput / 3600).toFixed(2)} / hr`,
          baseline: `${(benchmarkResult.baseline.throughput / 3600).toFixed(2)} / hr`,
          advantage:
            benchmarkResult.comparison.throughput_improvement !== null
              ? benchmarkResult.comparison.throughput_improvement >= 0
                ? `+${benchmarkResult.comparison.throughput_improvement.toFixed(1)}% (Higher)`
                : `${benchmarkResult.comparison.throughput_improvement.toFixed(1)}% (${Math.abs(
                    benchmarkResult.comparison.throughput_improvement
                  ).toFixed(1)}% Lower)`
              : "N/A",
          isPositive: (benchmarkResult.comparison.throughput_improvement ?? 0) >= 0,
          isNA: benchmarkResult.comparison.throughput_improvement === null,
        },
        {
          metric: "Energy Consumed",
          dfleet: `${benchmarkResult.decentralized.energy_used.toFixed(1)}%`,
          baseline: `${benchmarkResult.baseline.energy_used.toFixed(1)}%`,
          advantage:
            benchmarkResult.comparison.energy_improvement !== null
              ? benchmarkResult.comparison.energy_improvement >= 0
                ? `+${benchmarkResult.comparison.energy_improvement.toFixed(1)}% (Less)`
                : `${benchmarkResult.comparison.energy_improvement.toFixed(1)}% (${Math.abs(
                    benchmarkResult.comparison.energy_improvement
                  ).toFixed(1)}% More)`
              : "N/A",
          isPositive: (benchmarkResult.comparison.energy_improvement ?? 0) >= 0,
          isNA: benchmarkResult.comparison.energy_improvement === null,
        },
        {
          metric: "Total Path Length",
          dfleet: `${benchmarkResult.decentralized.path_length} cells`,
          baseline: `${benchmarkResult.baseline.path_length} cells`,
          advantage:
            benchmarkResult.comparison.path_length_improvement !== null
              ? benchmarkResult.comparison.path_length_improvement >= 0
                ? `+${benchmarkResult.comparison.path_length_improvement.toFixed(1)}% (Shorter)`
                : `${benchmarkResult.comparison.path_length_improvement.toFixed(1)}% (${Math.abs(
                    benchmarkResult.comparison.path_length_improvement
                  ).toFixed(1)}% Longer)`
              : "N/A",
          isPositive: (benchmarkResult.comparison.path_length_improvement ?? 0) >= 0,
          isNA: benchmarkResult.comparison.path_length_improvement === null,
        },
        {
          metric: "P2P Messages",
          dfleet: `${benchmarkResult.decentralized.p2p_messages}`,
          baseline: "0 (Centralized)",
          advantage: "—",
          isPositive: true,
          isNA: false,
        },
      ]
    : [
        { metric: "Completion Time", dfleet: "—", baseline: "—", advantage: "—", isPositive: true, isNA: false },
        { metric: "Avg Waiting Time", dfleet: "—", baseline: "—", advantage: "—", isPositive: true, isNA: false },
        { metric: "Conflicts / Stops", dfleet: "—", baseline: "—", advantage: "—", isPositive: true, isNA: false },
        { metric: "Task Throughput", dfleet: "—", baseline: "—", advantage: "—", isPositive: true, isNA: false },
        { metric: "Energy Consumed", dfleet: "—", baseline: "—", advantage: "—", isPositive: true, isNA: false },
        { metric: "Total Path Length", dfleet: "—", baseline: "—", advantage: "—", isPositive: true, isNA: false },
        { metric: "P2P Messages", dfleet: "—", baseline: "0", advantage: "—", isPositive: true, isNA: false },
      ];

  return (
    <div className="flex flex-col space-y-3 font-mono text-xs select-text">
      {/* 1. Header with Scenario & Seed info */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-emerald-400" />
          <div>
            <h2 className="text-xs font-bold text-slate-100 tracking-wider">
              DECENTRALIZED VS BASELINE
            </h2>
            <p className="text-[9px] text-slate-400">
              Stop-and-Go Benchmark ({selectedScenario.replace(".json", "").toUpperCase()})
              {benchmarkResult && (
                <span className="text-cyan-400 font-bold ml-1.5">
                  • Seed {benchmarkResult.seed}
                </span>
              )}
            </p>
          </div>
        </div>

        <span
          className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase border ${
            isRunning
              ? "bg-amber-950/80 border-amber-600 text-amber-300 animate-pulse"
              : isBothCompleted
              ? "bg-purple-950/80 border-purple-600 text-purple-300"
              : benchmarkResult
              ? "bg-rose-950/80 border-rose-600 text-rose-300"
              : "bg-slate-950 border-slate-700 text-slate-400"
          }`}
        >
          {isRunning
            ? benchmarkStatus
            : isBothCompleted
            ? "BENCHMARK COMPLETE"
            : benchmarkResult
            ? "BASELINE INCOMPLETE"
            : "BENCHMARK NOT RUN"}
        </span>
      </div>

      {/* 2. PROMINENT OVERALL ADVANTAGE / DEFICIT BANNER */}
      <div className="bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950/40 border border-cyan-500/40 rounded-xl p-3 shadow-lg flex flex-col items-center justify-center text-center relative overflow-visible shrink-0">
        <div className="absolute top-2 right-2 text-cyan-400/20">
          <Award className="w-8 h-8" />
        </div>

        {/* Title with Tooltip */}
        <div className="flex items-center justify-center gap-1.5 mb-0.5">
          <span
            className={`text-[10px] font-extrabold tracking-widest uppercase ${
              overallImprovement !== null
                ? overallImprovement >= 0
                  ? "text-emerald-400"
                  : "text-rose-400"
                : "text-cyan-400"
            }`}
          >
            {overallImprovement !== null
              ? overallImprovement >= 0
                ? "D-FLEET ADVANTAGE"
                : "BASELINE ADVANTAGE"
              : "OVERALL COMPARISON"}
          </span>
          <div className="relative group cursor-help">
            <Info className="w-3.5 h-3.5 text-slate-400 hover:text-cyan-300 transition-colors" />
            <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 hidden group-hover:block w-56 p-2 bg-slate-900 border border-slate-700 text-[9px] text-slate-300 rounded shadow-2xl pointer-events-none z-50 text-center leading-relaxed">
              Normalized composite score across 5 benchmark dimensions (equal 20% weight). Positive favors D-Fleet, negative favors baseline.
            </div>
          </div>
        </div>

        {/* Big Normalized Composite Score or N/A */}
        <div className="my-1 flex items-center justify-center gap-1.5">
          {overallImprovement !== null ? (
            <>
              <span
                className={`text-2xl font-black tracking-tight ${
                  overallImprovement >= 0 ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {overallImprovement >= 0 ? `+${overallImprovement.toFixed(1)}%` : `${overallImprovement.toFixed(1)}%`}
              </span>
              {overallImprovement >= 0 ? (
                <TrendingUp className="w-5 h-5 text-emerald-400" />
              ) : (
                <TrendingDown className="w-5 h-5 text-rose-400" />
              )}
            </>
          ) : benchmarkResult ? (
            <div className="flex items-center gap-1.5">
              <span className="text-xl font-black text-rose-400 tracking-tight">N/A</span>
              <span className="text-[9px] px-1.5 py-0.5 bg-rose-950/80 border border-rose-700 rounded text-rose-300 font-bold">
                INCOMPLETE
              </span>
            </div>
          ) : (
            <span className="text-lg font-bold text-slate-500">—</span>
          )}
        </div>

        {/* Target Badge */}
        {overallImprovement !== null && overallImprovement >= 20.0 && (
          <div className="mb-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/90 border border-emerald-500/80 text-[8px] font-black text-emerald-300 uppercase tracking-wider shadow-sm animate-pulse">
            <span>TARGET ≥ 20% ACHIEVED ✓</span>
          </div>
        )}

        <p className="text-[9px] text-slate-300 max-w-[280px] leading-tight">
          {benchmarkResult?.comparison?.incomplete_reason ||
            (overallImprovement !== null
              ? overallImprovement >= 0
                ? `D-Fleet achieved a +${overallImprovement.toFixed(1)}% normalized composite advantage.`
                : `Baseline outperformed D-Fleet by ${Math.abs(overallImprovement).toFixed(1)}% in this scenario.`
              : "Click 'RUN BENCHMARK' to execute real multi-agent comparison.")}
        </p>
      </div>

      {/* 2.5 Real Simulation Execution Audit Strip */}
      {benchmarkResult && (
        <div className="bg-slate-950/90 border border-slate-800 rounded-lg p-2 space-y-1.5 shrink-0">
          <div className="text-[8px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Activity className="w-3 h-3 text-cyan-400" />
            <span>BENCHMARK RUN AUDIT (IDENTICAL FAULT & SEED)</span>
          </div>

          <div className="grid grid-cols-2 gap-1.5 text-[8.5px]">
            {/* D-Fleet Run Info */}
            <div className="bg-slate-900/80 border border-cyan-900/50 rounded p-1.5 space-y-0.5">
              <div className="font-bold text-cyan-300 flex items-center justify-between text-[9px]">
                <span>D-FLEET</span>
                <span
                  className={`px-1 rounded text-[7.5px] ${
                    benchmarkResult.dFleetResult?.completed
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                      : "bg-amber-950 text-amber-300 border border-amber-700"
                  }`}
                >
                  {benchmarkResult.dFleetResult?.status || "COMPLETED"}
                </span>
              </div>
              <div className="text-slate-400">
                Faulted: <span className="text-white font-bold">{benchmarkResult.dFleetResult?.faultedRobotId || "None"}</span>
              </div>
              <div className="text-slate-400">
                Tasks:{" "}
                <span className="text-emerald-400 font-bold">
                  {benchmarkResult.dFleetResult?.completedTasks}/{benchmarkResult.dFleetResult?.totalTasks}
                </span>
              </div>
              <div className="text-slate-400">
                Rescues: <span className="text-cyan-300 font-bold">{benchmarkResult.audit?.dfleet_rescues ?? 0}</span>
              </div>
              <div className="text-slate-400">
                Finish Tick:{" "}
                <span className="text-white font-bold">{benchmarkResult.dFleetResult?.completionTick ?? "N/A"}</span>
              </div>
              <div className="text-slate-400">
                Remaining: <span className="text-white font-bold">{(benchmarkResult.dFleetResult?.totalTasks || 0) - (benchmarkResult.dFleetResult?.completedTasks || 0)}</span>
              </div>
            </div>

            {/* Baseline Run Info */}
            <div className="bg-slate-900/80 border border-amber-900/50 rounded p-1.5 space-y-0.5">
              <div className="font-bold text-amber-300 flex items-center justify-between text-[9px]">
                <span>BASELINE</span>
                <span
                  className={`px-1 rounded text-[7.5px] ${
                    benchmarkResult.baselineResult?.completed
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                      : "bg-rose-950 text-rose-300 border border-rose-700"
                  }`}
                >
                  {benchmarkResult.baselineResult?.status || "INCOMPLETE"}
                </span>
              </div>
              <div className="text-slate-400">
                Faulted: <span className="text-white font-bold">{benchmarkResult.baselineResult?.faultedRobotId || "None"}</span>
              </div>
              <div className="text-slate-400">
                Tasks:{" "}
                <span className={benchmarkResult.baselineResult?.completed ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                  {benchmarkResult.baselineResult?.completedTasks}/{benchmarkResult.baselineResult?.totalTasks}
                </span>
              </div>
              <div className="text-slate-400">
                Rescues: <span className="text-slate-400 font-bold">{benchmarkResult.audit?.baseline_rescues ?? 0}</span>
              </div>
              <div className="text-slate-400">
                {benchmarkResult.baselineResult?.completed ? (
                  <>
                    Finish Tick: <span className="text-white font-bold">{benchmarkResult.baselineResult.completionTick}</span>
                  </>
                ) : (
                  <>
                    Timeout: <span className="text-rose-400 font-bold">{benchmarkResult.baselineResult?.timeoutTick || 500} ticks</span>
                  </>
                )}
              </div>
              <div className="text-slate-400">
                Remaining: <span className="text-white font-bold">{(benchmarkResult.baselineResult?.totalTasks || 0) - (benchmarkResult.baselineResult?.completedTasks || 0)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. Action Button Strip */}
      <div className="flex items-center justify-between gap-2 p-2 bg-slate-950/80 border border-slate-800 rounded-lg shrink-0">
        <span className="text-[10px] text-slate-400 font-semibold">
          Runs 2 full simulations with exact seed {benchmarkResult?.seed || 48291}
        </span>

        {onRunBenchmark && (
          <button
            onClick={onRunBenchmark}
            disabled={Boolean(isRunning)}
            className={`px-3 py-1.5 rounded text-[10px] font-bold shrink-0 flex items-center gap-1.5 transition-all cursor-pointer shadow-md ${
              isRunning
                ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
                : "bg-sky-600 hover:bg-sky-500 text-white border border-sky-400"
            }`}
          >
            {isRunning ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>RUNNING...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-current" />
                <span>RUN BENCHMARK</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* 4. Detailed Breakdown Comparison Table */}
      <div className="w-full pb-3">
        <table className="w-full text-[10px] font-mono text-left">
          <thead>
            <tr className="text-slate-400 border-b border-slate-800 text-[9px] uppercase">
              <th className="pb-1.5 font-semibold">METRIC</th>
              <th className="pb-1.5 text-center font-semibold">D-FLEET</th>
              <th className="pb-1.5 text-center font-semibold">BASELINE</th>
              <th className="pb-1.5 text-right font-semibold">ADVANTAGE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {rows.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                <td className="py-2 font-medium text-slate-300">{row.metric}</td>
                <td className="py-2 text-center font-bold text-cyan-300">{row.dfleet}</td>
                <td className="py-2 text-center text-slate-400">{row.baseline}</td>
                <td className="py-2 text-right font-bold">
                  {row.isNA ? (
                    <span className="text-slate-500 text-[9px] font-bold">N/A</span>
                  ) : row.advantage !== "—" ? (
                    <span
                      className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border text-[9px] ${
                        row.isPositive
                          ? "bg-emerald-950/80 border-emerald-600/60 text-emerald-300"
                          : "bg-rose-950/80 border-rose-600/60 text-rose-300"
                      }`}
                    >
                      {row.advantage}
                    </span>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
