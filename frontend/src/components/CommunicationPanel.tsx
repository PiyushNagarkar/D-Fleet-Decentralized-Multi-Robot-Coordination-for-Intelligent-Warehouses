/**
 * CommunicationPanel: P2P Network Telemetry & Message Traffic Inspector
 */

import React from "react";
import {
  Radio,
  Send,
  Inbox,
  ArrowRightLeft,
  AlertOctagon,
} from "lucide-react";
import { CommunicationEvent } from "../types";

interface CommunicationPanelProps {
  recentMessages: CommunicationEvent[];
  totalSent: number;
  totalReceived: number;
  totalDropped: number;
}

export const CommunicationPanel: React.FC<CommunicationPanelProps> = ({
  recentMessages,
  totalSent,
  totalReceived,
  totalDropped,
}) => {
  const dropRate = totalSent > 0 ? ((totalDropped / totalSent) * 100).toFixed(1) : "0.0";

  return (
    <div className="flex flex-col h-full bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
          <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span>P2P Communication Layer</span>
        </h2>
        <span className="text-[10px] text-slate-400 font-mono px-2 py-0.5 bg-slate-950 border border-slate-800 rounded">
          Decentralized Mesh
        </span>
      </div>

      {/* Network Health Cards */}
      <div className="grid grid-cols-3 gap-2 my-3 font-mono">
        <div className="p-2.5 bg-slate-950/60 border border-slate-800 rounded-lg">
          <div className="flex items-center justify-between text-slate-500 text-[10px] mb-1">
            <span>Sent</span>
            <Send className="w-3 h-3 text-cyan-400" />
          </div>
          <span className="text-sm font-bold text-slate-200">{totalSent}</span>
        </div>

        <div className="p-2.5 bg-slate-950/60 border border-slate-800 rounded-lg">
          <div className="flex items-center justify-between text-slate-500 text-[10px] mb-1">
            <span>Delivered</span>
            <Inbox className="w-3 h-3 text-emerald-400" />
          </div>
          <span className="text-sm font-bold text-emerald-400">{totalReceived}</span>
        </div>

        <div className="p-2.5 bg-slate-950/60 border border-slate-800 rounded-lg">
          <div className="flex items-center justify-between text-slate-500 text-[10px] mb-1">
            <span>Loss Rate</span>
            <AlertOctagon className="w-3 h-3 text-amber-400" />
          </div>
          <span
            className={`text-sm font-bold ${
              Number(dropRate) > 5 ? "text-amber-400" : "text-slate-200"
            }`}
          >
            {dropRate}%
          </span>
        </div>
      </div>

      {/* Recent Live Messages List */}
      <div className="flex-1 overflow-y-auto space-y-2 pt-1 font-mono text-xs">
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
          Recent Peer-to-Peer Envelopes
        </span>
        {recentMessages.length === 0 ? (
          <div className="text-slate-600 text-center py-6 text-xs italic">
            No P2P messages exchanged yet.
          </div>
        ) : (
          recentMessages.map((msg, idx) => (
            <div
              key={msg.id || idx}
              className="p-2 bg-slate-950/60 border border-slate-800/80 rounded-lg flex items-center justify-between gap-2"
            >
              <div className="flex items-center gap-2">
                <span className="text-slate-500 text-[10px]">[T+{msg.tick}]</span>
                <span className="font-bold text-cyan-300">{msg.from}</span>
                <ArrowRightLeft className="w-3 h-3 text-slate-600" />
                <span className="font-bold text-indigo-300">{msg.to || "BROADCAST"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded text-[10px]">
                  {msg.type}
                </span>
                <span
                  className={`text-[9px] px-1 py-0.5 rounded ${
                    msg.status === "DELIVERED"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : "bg-amber-950 text-amber-400 border border-amber-800"
                  }`}
                >
                  {msg.status}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
