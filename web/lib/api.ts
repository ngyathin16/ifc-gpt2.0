const API = "";

export async function generateFromText(message: string) {
  const res = await fetch(`${API}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return res.json();
}

export async function buildFromPlan(plan: object) {
  const res = await fetch(`${API}/api/build-from-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan }),
  });
  return res.json();
}

export async function modifyElement(guid: string, instruction: string, ifcUrl: string) {
  const res = await fetch(`${API}/api/modify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ guid, instruction, ifc_url: ifcUrl }),
  });
  return res.json();
}

export async function submitVoice(audioBlob: Blob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  const res = await fetch(`${API}/api/voice`, {
    method: "POST",
    body: formData,
  });
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
  });
  return res.json();
}

export function getIfcUrl(path: string): string {
  return `${API}${path}`;
}
