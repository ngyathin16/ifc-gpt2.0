const API = "";

export interface FeatureItem {
  id: string;
  category: string;
  label: string;
  description: string;
  default_for: string[];
  conflicts_with?: string[];
}

export interface InferredDefaults {
  building_type: string;
  num_storeys: number;
  floor_to_floor_height: number;
  default_features: string[];
}

async function assertOk(res: Response): Promise<Response> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${res.statusText}${body ? ` — ${body}` : ""}`);
  }
  return res;
}

export async function getFeatures(): Promise<FeatureItem[]> {
  const res = await fetch(`${API}/api/features`).then(assertOk);
  return res.json();
}

export async function inferFeatures(message: string): Promise<InferredDefaults> {
  const res = await fetch(`${API}/api/features/infer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  }).then(assertOk);
  return res.json();
}

export async function generateFromText(message: string, selectedFeatures?: string[]) {
  const res = await fetch(`${API}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, selected_features: selectedFeatures }),
  }).then(assertOk);
  return res.json();
}

export async function buildFromPlan(plan: object) {
  const res = await fetch(`${API}/api/build-from-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan }),
  }).then(assertOk);
  return res.json();
}

export async function modifyElement(guid: string, instruction: string, ifcUrl: string) {
  const res = await fetch(`${API}/api/modify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ guid, instruction, ifc_url: ifcUrl }),
  }).then(assertOk);
  return res.json();
}

export async function submitVoice(audioBlob: Blob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  const res = await fetch(`${API}/api/voice`, {
    method: "POST",
    body: formData,
  }).then(assertOk);
  return res.json();
}

export async function uploadFloorPlan(
  file: File,
  numStoreys: number = 1,
  floorToFloorHeight: number = 3.0,
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("num_storeys", String(numStoreys));
  formData.append("floor_to_floor_height", String(floorToFloorHeight));
  const res = await fetch(`${API}/api/floorplan`, {
    method: "POST",
    body: formData,
  }).then(assertOk);
  return res.json();
}

export function getIfcUrl(path: string): string {
  return `${API}${path}`;
}
