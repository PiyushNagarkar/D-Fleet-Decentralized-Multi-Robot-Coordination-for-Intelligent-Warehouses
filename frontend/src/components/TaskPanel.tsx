/**
 * TaskPanel: Warehouse Task Queue & Autonomous Bidding Status
 */

import React, { useState } from "react";
import {
  PackageSearch,
  ArrowRight,
  LifeBuoy,
} from "lucide-react";
import { TaskInfo, TaskStatus } from "../types";

interface TaskPanelProps {
  tasks: TaskInfo[];
}

export const TaskPanel: React.FC<TaskPanelProps> = ({ tasks }) => {
  const [filter, setFilter] = useState<"ALL" | "ACTIVE" | "COMPLETED" | "FAILED">("ALL");

  const filteredTasks = tasks.filter((t) => {
    if (filter === "ACTIVE") {
      return t.status !== TaskStatus.DELIVERED && t.status !== TaskStatus.FAILED;
    }
    if (filter === "COMPLETED") {
      return t.status === TaskStatus.DELIVERED;
    }
    if (filter === "FAILED") {
      return t.status === TaskStatus.FAILED || t.status === TaskStatus.RESCUE_REQUIRED;
    }
    return true;
  });

  const getStatusBadge = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.UNASSIGNED:
        return "bg-slate-800 text-slate-300 border-slate-700";
      case TaskStatus.BIDDING:
        return "bg-purple-950 text-purple-300 border-purple-800 animate-pulse";
      case TaskStatus.CLAIMED:
        return "bg-indigo-950 text-indigo-300 border-indigo-800";
      case TaskStatus.GOING_TO_PICKUP:
      case TaskStatus.PICKED_UP:
      case TaskStatus.GOING_TO_DELIVERY:
        return "bg-cyan-950 text-cyan-300 border-cyan-800 font-bold";
      case TaskStatus.DELIVERED:
        return "bg-emerald-950 text-emerald-300 border-emerald-800 font-bold";
      case TaskStatus.RESCUE_REQUIRED:
        return "bg-rose-950 text-rose-300 border-rose-800 animate-bounce font-bold";
      case TaskStatus.FAILED:
        return "bg-slate-900 text-rose-400 border-rose-900";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-xl p-3.5 shadow-xl">
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-800">
        <h2 className="text-xs font-bold text-slate-100 flex items-center gap-2 font-mono uppercase tracking-wider">
          <PackageSearch className="w-4 h-4 text-cyan-400" />
          <span>Warehouse Tasks ({tasks.length})</span>
        </h2>

        {/* Filter buttons */}
        <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-[10px]">
          {(["ALL", "ACTIVE", "COMPLETED", "FAILED"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded font-mono font-bold cursor-pointer ${
                filter === f
                  ? "bg-cyan-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pt-2 pr-1">
        {filteredTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-28 text-slate-500 text-xs italic">
            <span>No tasks matching {filter} filter</span>
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div
              key={task.id}
              className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg hover:border-slate-700 transition-all text-xs flex flex-col gap-1.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-bold font-mono text-cyan-300">{task.id}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 bg-slate-800 text-slate-400 rounded">
                    Prio: {task.priority}
                  </span>
                  {task.status === TaskStatus.RESCUE_REQUIRED && (
                    <span className="flex items-center gap-1 px-1.5 py-0.2 bg-rose-950 border border-rose-800 text-rose-300 rounded text-[9px] font-mono font-bold">
                      <LifeBuoy className="w-3 h-3" /> RESCUE
                    </span>
                  )}
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${getStatusBadge(
                    task.status
                  )}`}
                >
                  {task.status}
                </span>
              </div>

              {/* Coordinates & Assigned Robot */}
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-300">
                <div className="flex items-center gap-1.5">
                  <span className="text-indigo-400 font-semibold">
                    ({task.pickup_location[0]}, {task.pickup_location[1]})
                  </span>
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                  <span className="text-teal-400 font-semibold">
                    ({task.delivery_location[0]}, {task.delivery_location[1]})
                  </span>
                </div>
                <div className="text-[10px]">
                  {task.assigned_robot ? (
                    <span className="text-cyan-300 font-bold bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800">
                      Assigned: {task.assigned_robot}
                    </span>
                  ) : (
                    <span className="text-slate-500 italic">Unassigned</span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
