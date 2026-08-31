/**
 * REST API client for D-Fleet Simulation Environment Infrastructure
 *
 * CRITICAL SAFETY MANDATE:
 * Frontend controls ONLY communicate with simulation environment endpoints.
 * Never send instructions that assign tasks, command paths, or resolve robot conflicts.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export async function fetchSimulationStatus() {
  const res = await fetch(`${BASE_URL}/simulation/status`);
  if (!res.ok) throw new Error("Failed to fetch simulation status");
  return res.json();
}

export async function startSimulation() {
  const res = await fetch(`${BASE_URL}/simulation/start`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start simulation");
  return res.json();
}

export async function pauseSimulation() {
  const res = await fetch(`${BASE_URL}/simulation/pause`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to pause simulation");
  return res.json();
}

export async function resetSimulation() {
  const res = await fetch(`${BASE_URL}/simulation/reset`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to reset simulation");
  return res.json();
}

export async function setSimulationSpeed(speed: number) {
  const res = await fetch(`${BASE_URL}/simulation/speed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed }),
  });
  if (!res.ok) throw new Error("Failed to set simulation speed");
  return res.json();
}

export async function fetchScenarios(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/scenarios`);
  if (!res.ok) throw new Error("Failed to fetch scenarios");
  const data = await res.json();
  if (Array.isArray(data)) {
    return data.map((s: any) => (typeof s === "string" ? s : s.filename || `${s.id}.json`));
  }
  return [];
}

export async function loadScenario(scenarioId: string) {
  const res = await fetch(`${BASE_URL}/scenarios/${scenarioId}/load`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to load scenario ${scenarioId}`);
  return res.json();
}

export async function injectObstacle(obstacle: {
  obstacle_id: string;
  x: number;
  y: number;
  duration?: number;
  obstacle_type?: string;
}) {
  const res = await fetch(`${BASE_URL}/obstacles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(obstacle),
  });
  if (!res.ok) throw new Error("Failed to inject obstacle");
  return res.json();
}

export async function injectFailure(robotId: string, reason: string = "simulated_hardware_fault") {
  const res = await fetch(`${BASE_URL}/failures/${robotId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error(`Failed to inject failure on ${robotId}`);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${BASE_URL}/metrics`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}
