import React, { useState, useRef, useEffect } from "react";
import {
  Terminal,
  Bot,
  AlertTriangle,
  Radio,
  PackageCheck,
  Compass,
} from "lucide-react";
import { SimulationEvent } from "../types";

interface EventLogProps {
  events: SimulationEvent[];
}

export const EventLog: React.FC<EventLogProps> = ({ events }) => {
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [autoScroll, setAutoScroll] = useState(true);
  const listContainerRef = useRef<HTMLDivElement | null>(null);
  const isNearBottomRef = useRef<boolean>(true);

  // Monitor manual scroll position to respect user inspection of older events
  const handleScroll = () => {
    if (!listContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = listContainerRef.current;
    // Near bottom if within 40px of bottom
    isNearBottomRef.current = scrollHeight - scrollTop - clientHeight < 40;
  };

  useEffect(() => {
    if (autoScroll && isNearBottomRef.current && listContainerRef.current) {
      listContainerRef.current.scrollTop = listContainerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const filteredEvents = events.filter((e) => {
    const type = e.event_type.toUpperCase();
    if (categoryFilter === "TASKS") {
      return type.includes("TASK") || type.includes("PICK") || type.includes("DELIVER") || type.includes("ITEM");
    }
    if (categoryFilter === "P2P") {
      return (
        type.includes("MESSAGE") ||
        type.includes("BID") ||
        type.includes("CLAIM") ||
        type.includes("YIELD") ||
        type.includes("HEARTBEAT") ||
        type.includes("BROADCAST")
      );
    }
    if (categoryFilter === "CONFLICTS") {
      return (
        type.includes("CONFLICT") ||
        type.includes("DEADLOCK") ||
        type.includes("RESERVATION") ||
        type.includes("YIELD") ||
        type.includes("NEGOTIAT")
      );
    }
    if (categoryFilter === "OBSTACLES") {
      return type.includes("OBSTACLE");
    }
    if (categoryFilter === "FAILURES") {
      return type.includes("FAIL") || type.includes("RESCUE") || type.includes("FAULT");
    }
    if (categoryFilter === "PLANNING") {
      return (
        type.includes("PLAN") ||
        type.includes("REPLAN") ||
        type.includes("DSTAR") ||
        type.includes("PATH") ||
        type.includes("ROUTE")
      );
    }
    return true;
  });

  return (
    <div className="flex flex-col h-full min-h-0 bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-xl font-mono text-xs overflow-hidden">
      {/* 1. Header Toolbar (Fixed) */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2 text-slate-200 font-bold">
          <Terminal className="w-3.5 h-3.5 text-sky-400" />
          <span className="text-xs tracking-wider uppercase font-black">
            LIVE EVENT TIMELINE ({filteredEvents.length})
          </span>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 text-[10px]">
          {["ALL", "TASKS", "P2P", "CONFLICTS", "OBSTACLES", "FAILURES", "PLANNING"].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-2 py-0.5 rounded font-bold transition-all cursor-pointer ${
                categoryFilter === cat
                  ? "bg-sky-600 text-white shadow-sm"
                  : "bg-slate-950/80 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              {cat}
            </button>
          ))}

          <label className="flex items-center gap-1 ml-2 text-[10px] text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-sky-500 focus:ring-0 w-3 h-3 cursor-pointer"
            />
            <span>Auto-scroll</span>
          </label>
        </div>
      </div>

      {/* 2. Timeline List (Scrollable Area with bounded height and 2D scrolling) */}
      <div
        ref={listContainerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-x-auto overflow-y-auto space-y-1.5 mt-2 pr-1 select-text overscroll-contain"
      >
        {filteredEvents.length > 0 ? (
          filteredEvents.map((evt, idx) => {
            const isObstacle = evt.event_type.includes("OBSTACLE");
            const isFailure = evt.event_type.includes("FAIL") || evt.event_type.includes("FAULT");
            const isP2P = evt.event_type.includes("MESSAGE") || evt.event_type.includes("BID") || evt.event_type.includes("YIELD");
            const isTask = evt.event_type.includes("TASK") || evt.event_type.includes("ITEM") || evt.event_type.includes("DELIVER");
            const isPlanning = evt.event_type.includes("PLAN") || evt.event_type.includes("DSTAR");

            const timeStr = `T+${evt.tick}`;

            return (
              <div
                key={evt.event_id || idx}
                className="flex items-center gap-2.5 text-[10px] py-0.5 hover:bg-slate-800/40 px-1 rounded transition-colors whitespace-nowrap min-w-max"
              >
                <span className="text-slate-500 shrink-0 min-w-[36px]">{timeStr}</span>

                <div className="flex items-center gap-1 shrink-0 min-w-[70px]">
                  {isObstacle || isFailure ? (
                    <AlertTriangle className="w-3 h-3 text-rose-400" />
                  ) : isTask ? (
                    <PackageCheck className="w-3 h-3 text-emerald-400" />
                  ) : isP2P ? (
                    <Radio className="w-3 h-3 text-purple-400" />
                  ) : isPlanning ? (
                    <Compass className="w-3 h-3 text-amber-400" />
                  ) : (
                    <Bot className="w-3 h-3 text-sky-400" />
                  )}
                  <span className={`font-bold ${isObstacle || isFailure ? "text-rose-400" : evt.robot_id ? "text-sky-300" : "text-slate-400"}`}>
                    {evt.robot_id || (isObstacle ? "OBSTACLE" : "SYSTEM")}
                  </span>
                </div>

                <span className={`text-slate-300 ${isObstacle ? "text-rose-300 font-semibold" : isFailure ? "text-rose-400 font-bold" : ""}`}>
                  <strong className="text-slate-200">{evt.event_type.replace(/_/g, " ")}</strong>: {JSON.stringify(evt.payload || {}).replace(/[{""}]/g, " ")}
                </span>
              </div>
            );
          })
        ) : (
          <div className="text-slate-600 text-center py-6 text-xs italic">
            No events found matching {categoryFilter} filter.
          </div>
        )}
      </div>
    </div>
  );
};

