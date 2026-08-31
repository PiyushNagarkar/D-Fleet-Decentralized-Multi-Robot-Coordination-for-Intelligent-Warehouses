/**
 * useSimulationSocket: Consumes real-time dashboard telemetry from /ws/simulation
 * with Seamless Auto-Execution Engine
 *
 * CRITICAL ARCHITECTURAL MANDATE:
 * - Read-only telemetry OUT to the frontend.
 * - Outbound actions invoke REST simulation environment endpoints, never robot control commands.
 * - Guarantees continuous live simulation execution under all network and offline environments.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { TelemetrySnapshot, RobotStatus, TaskStatus } from "../types";
import * as api from "../services/api";
import { LocalSimulationEngine, SCENARIOS } from "../services/localSimulationEngine";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/simulation";

export function useSimulationSocket() {
  const localEngineRef = useRef<LocalSimulationEngine>(new LocalSimulationEngine("complete_demo.json"));
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot>(() => localEngineRef.current.getSnapshot());
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [availableScenarios, setAvailableScenarios] = useState<string[]>(Object.keys(SCENARIOS));
  const [selectedScenario, setSelectedScenario] = useState<string>("complete_demo.json");
  const [activeSpeed, setActiveSpeedState] = useState<number>(1.0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const localLoopRef = useRef<NodeJS.Timeout | null>(null);
  const isRunningRef = useRef<boolean>(false);

  // Load scenarios from backend if available
  useEffect(() => {
    api.fetchScenarios()
      .then((scenarios) => {
        if (scenarios && scenarios.length > 0) {
          setAvailableScenarios(scenarios);
          if (!scenarios.includes(selectedScenario)) {
            setSelectedScenario(scenarios[0]);
          }
        }
      })
      .catch(() => {
        setAvailableScenarios(Object.keys(SCENARIOS));
      });
  }, [selectedScenario]);

  // Connect to WebSocket telemetry stream
  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        // Clear local runner loop when live backend is connected
        if (localLoopRef.current) {
          clearInterval(localLoopRef.current);
          localLoopRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const snap = data.data || data.payload || data;
          if (snap && snap.robots && Array.isArray(snap.robots)) {
            setTelemetry({
              tick: snap.tick ?? 0,
              status: snap.status ?? "idle",
              robots: snap.robots.map((r: any) => ({
                id: r.id || r.robot_id,
                position: r.position || [0, 0],
                status: (r.status as RobotStatus) || RobotStatus.IDLE,
                battery: r.battery ?? 100.0,
                carrying_item: r.carrying_item,
                task_id: r.task_id,
                priority: r.priority ?? 1,
                current_path: r.current_path || r.path || [],
              })),
              tasks: (snap.tasks || []).map((t: any) => ({
                id: t.id || t.task_id,
                pickup_location: t.pickup_location || t.pickup_position || [0, 0],
                delivery_location: t.delivery_location || t.delivery_position || [0, 0],
                status: (t.status as TaskStatus) || TaskStatus.UNASSIGNED,
                priority: t.priority ?? 1,
                item_type: t.item_type || "standard_pod",
                assigned_robot: t.assigned_robot,
                spawn_tick: t.spawn_tick ?? 0,
              })),
              obstacles: (snap.obstacles || []).map((o: any) => ({
                id: o.id || `obs_${o.x}_${o.y}`,
                x: o.x ?? (o.position ? o.position[0] : 0),
                y: o.y ?? (o.position ? o.position[1] : 0),
                type: o.type || "STATIC",
                start_tick: o.start_tick ?? 0,
                duration: o.duration ?? 50,
              })),
              reservations: snap.reservations || [],
              recent_messages: snap.recent_messages || [],
              events: snap.events || snap.recent_events || [],
              active_negotiations: snap.active_negotiations || [],
              metrics: {
                total_tasks_completed: snap.metrics?.total_tasks_completed ?? 0,
                total_tasks_spawned: snap.metrics?.total_tasks_spawned ?? (snap.tasks?.length || 0),
                throughput_tasks_per_hour: snap.metrics?.throughput_tasks_per_hour ?? 0,
                average_completion_time_ticks: snap.metrics?.average_completion_time_ticks ?? 0,
                average_waiting_time_ticks: snap.metrics?.average_waiting_time_ticks ?? 0,
                conflicts_detected: snap.metrics?.conflicts_detected ?? 0,
                conflicts_resolved: snap.metrics?.conflicts_resolved ?? 0,
                deadlocks_detected: snap.metrics?.deadlocks_detected ?? 0,
                deadlocks_resolved: snap.metrics?.deadlocks_resolved ?? 0,
                replanning_events: snap.metrics?.replanning_events ?? 0,
                collisions_detected: snap.metrics?.collisions_detected ?? 0,
                messages_sent: snap.metrics?.messages_sent ?? 0,
                messages_received: snap.metrics?.messages_received ?? 0,
                messages_dropped: snap.metrics?.messages_dropped ?? 0,
                average_battery_consumed: snap.metrics?.average_battery_consumed ?? 0,
                charging_events_count: snap.metrics?.charging_events_count ?? 0,
                robot_failures_count: snap.metrics?.robot_failures_count ?? 0,
                rescue_operations_count: snap.metrics?.rescue_operations_count ?? 0,
              },
            });
          }
        } catch {
          // Ignore malformed payloads
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // If simulation was active, resume local simulation loop seamlessly
        if (isRunningRef.current && !localLoopRef.current) {
          startLocalLoop();
        }
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2500);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setIsConnected(false);
    }
  }, []);

  const startLocalLoop = useCallback(() => {
    if (localLoopRef.current) clearInterval(localLoopRef.current);
    const intervalMs = Math.max(50, Math.round(500 / activeSpeed));
    localLoopRef.current = setInterval(() => {
      if (isRunningRef.current) {
        const snap = localEngineRef.current.step();
        setTelemetry({ ...snap });
      }
    }, intervalMs);
  }, [activeSpeed]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
      if (localLoopRef.current) clearInterval(localLoopRef.current);
    };
  }, [connect]);

  // Handle speed updates
  useEffect(() => {
    if (isRunningRef.current && !isConnected) {
      startLocalLoop();
    }
  }, [activeSpeed, isConnected, startLocalLoop]);

  // Simulation environment controls
  const handleStart = async () => {
    isRunningRef.current = true;
    localEngineRef.current.start();
    if (isConnected) {
      try {
        await api.startSimulation();
      } catch {
        startLocalLoop();
      }
    } else {
      startLocalLoop();
    }
    setTelemetry(localEngineRef.current.getSnapshot());
  };

  const handlePause = async () => {
    isRunningRef.current = false;
    localEngineRef.current.pause();
    if (localLoopRef.current) {
      clearInterval(localLoopRef.current);
      localLoopRef.current = null;
    }
    if (isConnected) {
      try {
        await api.pauseSimulation();
      } catch {
        // Handled
      }
    }
    setTelemetry((prev) => ({ ...prev, status: "paused" }));
  };

  const handleReset = async () => {
    isRunningRef.current = false;
    if (localLoopRef.current) {
      clearInterval(localLoopRef.current);
      localLoopRef.current = null;
    }
    localEngineRef.current.reset();
    if (isConnected) {
      try {
        await api.resetSimulation();
      } catch {
        // Handled
      }
    }
    setTelemetry(localEngineRef.current.getSnapshot());
  };

  const handleStep = async () => {
    const snap = localEngineRef.current.step();
    setTelemetry({ ...snap });
  };

  const handleLoadScenario = async (scenarioId: string) => {
    setSelectedScenario(scenarioId);
    localEngineRef.current.loadScenario(scenarioId);
    if (isConnected) {
      try {
        await api.loadScenario(scenarioId);
      } catch {
        // Handled
      }
    }
    setTelemetry(localEngineRef.current.getSnapshot());
  };

  const handleSetSpeed = (newSpeed: number) => {
    setActiveSpeedState(newSpeed);
    if (isConnected) {
      api.setSimulationSpeed(newSpeed).catch(() => {});
    }
  };

  const handleInjectObstacle = async (obstacle: {
    obstacle_id: string;
    x: number;
    y: number;
    duration?: number;
    obstacle_type?: string;
  }) => {
    localEngineRef.current.injectObstacle(obstacle.x, obstacle.y, obstacle.obstacle_id);
    if (isConnected) {
      try {
        await api.injectObstacle(obstacle);
      } catch {
        // Handled
      }
    }
    setTelemetry(localEngineRef.current.getSnapshot());
  };

  const handleInjectFailure = async (robotId: string) => {
    localEngineRef.current.injectFailure(robotId);
    if (isConnected) {
      try {
        await api.injectFailure(robotId);
      } catch {
        // Handled
      }
    }
    setTelemetry(localEngineRef.current.getSnapshot());
  };

  const handleRandomizeScenario = (customSeed?: number) => {
    const seed = customSeed !== undefined ? customSeed : Math.floor(Math.random() * 900000) + 10000;
    setSelectedScenario("random.json");
    localEngineRef.current.loadScenario("random.json", seed);
    setTelemetry(localEngineRef.current.getSnapshot());
  };

  return {
    telemetry,
    isConnected,
    availableScenarios,
    selectedScenario,
    activeSpeed,
    setActiveSpeed: handleSetSpeed,
    controls: {
      start: handleStart,
      pause: handlePause,
      reset: handleReset,
      step: handleStep,
      loadScenario: handleLoadScenario,
      randomizeScenario: handleRandomizeScenario,
      injectObstacle: handleInjectObstacle,
      injectFailure: handleInjectFailure,
      getLiveEngine: () => localEngineRef.current,
    },
  };
}
