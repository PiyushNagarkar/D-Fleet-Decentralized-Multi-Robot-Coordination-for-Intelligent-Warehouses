/**
 * BaselineTableCard: Decentralized vs Stop-and-Go Baseline Comparison Table
 * Powered by genuine simulation runs under identical initial conditions and seed.
 */

import React from "react";
import { Scale, Play, TrendingDown, TrendingUp, Loader2 } from "lucide-react";
import { BenchmarkResult } from "../services/localSimulationEngine";

interface BaselineTableCardProps {
  benchmarkResult?: BenchmarkResult | null;
  benchmarkStatus?: string | null;
  onRunBenchmark?: () => void;
  selectedScenario?: string;
}

export const BaselineTableCard: React.FC<BaselineTableCardProps> = ({
  benchmarkResult,
  benchmarkStatus,
  onRunBenchmark,
  selectedScenario = "complete_demo.json",
}) => {
  const isRunning =
    benchmarkStatus &&
    benchmarkStatus !== "BENCHMARK COMPLETE" &&
    benchmarkStatus !== "NOT RUN";

  const rows = benchmarkResult
    ? [
        {
          metric: "Task Throughput",
          decentralized: `${(benchmarkResult.decentralized.throughput / 3600).toFixed(2)} / hr`,
          baseline: `${(benchmarkResult.baseline.throughput / 3600).toFixed(2)} / hr`,
          advantage:
            benchmarkResult.comparison.throughput_improvement !== null
              ? `${benchmarkResult.comparison.throughput_improvement >= 0 ? "↑" : "↓"} ${Math.abs(
                  benchmarkResult.comparison.throughput_improvement
                ).toFixed(1)}%`
              : "N/A",
          isPositive: (benchmarkResult.comparison.throughput_improvement ?? 0) >= 0,
        },
        {
          metric: "Completion Time",
          decentralized: benchmarkResult.dFleetResult?.completed
            ? `${benchmarkResult.dFleetResult.completionTick} t`
            : `${benchmarkResult.decentralized.completion_time} t`,
          baseline: benchmarkResult.baselineResult?.completed
            ? `${benchmarkResult.baselineResult.completionTick} t`
            : `INCOMPLETE (${benchmarkResult.baselineResult?.timeoutTick || 500}t limit)`,
          advantage:
            benchmarkResult.comparison.completion_time_improvement !== null
              ? `${benchmarkResult.comparison.completion_time_improvement >= 0 ? "↓" : "↑"} ${Math.abs(
                  benchmarkResult.comparison.completion_time_improvement
                ).toFixed(1)}%`
              : "N/A",
          isPositive: (benchmarkResult.comparison.completion_time_improvement ?? 0) >= 0,
        },
        {
          metric: "Average Waiting Time",
          decentralized: `${benchmarkResult.decentralized.waiting_time.toFixed(1)} t`,
          baseline: `${benchmarkResult.baseline.waiting_time.toFixed(1)} t`,
          advantage:
            benchmarkResult.comparison.waiting_time_improvement !== null
              ? `${benchmarkResult.comparison.waiting_time_improvement >= 0 ? "↓" : "↑"} ${Math.abs(
                  benchmarkResult.comparison.waiting_time_improvement
                ).toFixed(1)}%`
              : "N/A",
          isPositive: (benchmarkResult.comparison.waiting_time_improvement ?? 0) >= 0,
        },
        {
          metric: "Conflicts / Stops",
          decentralized: `${benchmarkResult.decentralized.conflicts}`,
          baseline: `${benchmarkResult.baseline.conflicts}`,
          advantage:
            benchmarkResult.comparison.conflict_improvement !== null
              ? `${benchmarkResult.comparison.conflict_improvement >= 0 ? "↓" : "↑"} ${Math.abs(
                  benchmarkResult.comparison.conflict_improvement
                ).toFixed(1)}%`
              : "N/A",
          isPositive: (benchmarkResult.comparison.conflict_improvement ?? 0) >= 0,
        },
        {
          metric: "P2P Messages",
          decentralized: `${benchmarkResult.decentralized.p2p_messages}`,
          baseline: "0",
          advantage: "—",
          isPositive: true,
        },
        {
          metric: "Energy Used (avg)",
          decentralized: `${benchmarkResult.decentralized.energy_used.toFixed(1)}%`,
          baseline: `${benchmarkResult.baseline.energy_used.toFixed(1)}%`,
          advantage:
            benchmarkResult.comparison.energy_improvement !== null
              ? `${benchmarkResult.comparison.energy_improvement >= 0 ? "↓" : "↑"} ${Math.abs(
                  benchmarkResult.comparison.energy_improvement
                ).toFixed(1)}%`
              : "N/A",
          isPositive: (benchmarkResult.comparison.energy_improvement ?? 0) >= 0,
        },
      ]
    : [
        { metric: "Task Throughput", decentralized: "—", baseline: "—", advantage: "—", isPositive: true },
        { metric: "Completion Time", decentralized: "—", baseline: "—", advantage: "—", isPositive: true },
        { metric: "Average Waiting Time", decentralized: "—", baseline: "—", advantage: "—", isPositive: true },
        { metric: "Conflicts / Stops", decentralized: "—", baseline: "—", advantage: "—", isPositive: true },
        { metric: "P2P Messages", decentralized: "—", baseline: "0", advantage: "—", isPositive: true },
        { metric: "Energy Used (avg)", decentralized: "—", baseline: "—", advantage: "—", isPositive: true },
      ];

  return (
    <div className="flex flex-col h-full bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-xl font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-1.5 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          <Scale className="w-3.5 h-3.5 text-sky-400" />
          <div>
            <h3 className="text-xs font-bold text-white tracking-wider">
              DECENTRALIZED VS BASELINE
            </h3>
            <p className="text-[9px] text-slate-400">
              Stop-and-Go Baseline ({selectedScenario.replace(".json", "").toUpperCase()})
              {benchmarkResult && (
                <span className="text-cyan-400 font-bold ml-1.5">
                  • Seed {benchmarkResult.seed}
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Action button & Status */}
        <div className="flex items-center gap-2">
          <span
            className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase border ${
              isRunning
                ? "bg-amber-950/80 border-amber-600 text-amber-300 animate-pulse"
                : benchmarkResult
                ? "bg-purple-950/80 border-purple-600 text-purple-300"
                : "bg-slate-950 border-slate-700 text-slate-400"
            }`}
          >
            {benchmarkStatus || "BENCHMARK NOT RUN"}
          </span>

          {onRunBenchmark && (
            <button
              onClick={onRunBenchmark}
              disabled={Boolean(isRunning)}
              className={`px-2.5 py-1 rounded text-[10px] font-bold flex items-center gap-1 transition-all cursor-pointer shadow-sm ${
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
      </div>

      {/* Comparison Table */}
      <div className="flex-1 overflow-y-auto mt-2">
        <table className="w-full text-left text-[10px]">
          <thead>
            <tr className="text-slate-400 border-b border-slate-800/80 uppercase">
              <th className="pb-1 font-semibold">METRIC</th>
              <th className="pb-1 font-semibold text-center text-cyan-400">D-FLEET</th>
              <th className="pb-1 font-semibold text-center text-slate-400">STOP-AND-GO</th>
              <th className="pb-1 font-semibold text-right text-emerald-400">ADVANTAGE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/40 text-slate-300">
            {rows.map((r, idx) => (
              <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                <td className="py-1 text-slate-300">{r.metric}</td>
                <td className="py-1 text-center font-bold text-cyan-300">{r.decentralized}</td>
                <td className="py-1 text-center text-slate-400">{r.baseline}</td>
                <td className="py-1 text-right font-bold">
                  {r.advantage !== "—" ? (
                    <span
                      className={`inline-flex items-center gap-0.5 justify-end ${
                        r.isPositive ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {r.advantage.startsWith("↑") ? (
                        <TrendingUp className="w-2.5 h-2.5" />
                      ) : (
                        <TrendingDown className="w-2.5 h-2.5" />
                      )}
                      {r.advantage}
                    </span>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!benchmarkResult && !isRunning && (
          <div className="text-center py-2 text-[10px] text-slate-500 italic">
            Click &quot;RUN BENCHMARK&quot; to execute D-Fleet and Stop-and-Go under identical conditions.
          </div>
        )}
      </div>
    </div>
  );
};
