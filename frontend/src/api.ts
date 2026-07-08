export type Lang = "en" | "te" | "hi";

export interface Soil {
  ph: number | null;
  clay_pct: number | null;
  sand_pct: number | null;
  soc_g_kg: number | null;
  texture: string | null;
}

export interface Region {
  id: string;
  name: string;
  district: string | null;
  state: string | null;
  mp: string | null;
  zoom: number;
  plot_count: number;
  center: [number, number];
}

export interface Plot {
  id: string;
  region: string;
  farmer: string;
  village: string;
  mandal: string;
  crop_current: string;
  area_ha: number;
  lon: number;
  lat: number;
  geometry: { type: string; coordinates: number[][][] };
  irrigation: string | null;
  soil: Soil | null;
  groundwater: {
    category: string;
    pre_monsoon_dtw_m: number;
    post_monsoon_dtw_m: number;
  } | null;
}

export interface Indicator {
  date: string;
  ndvi: number | null;
  ndmi: number | null;
  rain_mm: number | null;
  et0_mm: number | null;
  soil_moisture: number | null;
}

export interface ForecastDay {
  date: string;
  rain_mm: number | null;
  et0_mm: number | null;
  tmax_c?: number | null;
  tmin_c?: number | null;
}

export interface Alert {
  type: string;
  severity: string;
  sms: Record<Lang, string>;
  [k: string]: unknown;
}

export interface AlertsResponse {
  plot_id: string;
  mode: string;
  replay_note: string | null;
  days: ForecastDay[];
  dry_spell: { start: string; length_days: number; severity: string } | null;
  water_balance: {
    etc_mm: number;
    rain_eff_mm: number;
    soil_buffer_mm: number;
    irrigation_mm: number;
    level: string;
  };
  alerts: Alert[];
}

export interface Recommendation {
  crop: string;
  labels: Record<Lang, string>;
  score: number;
  breakdown: { water: number; groundwater: number; ph: number; texture: number };
  water_need_mm: number;
  water_available_mm: number;
  duration_days: number;
  rainfed_ok: string;
  reasons: string[];
  is_current: boolean;
}

export interface RecommendResponse {
  season: string;
  season_rain_mm: number;
  irrigation_capacity_mm: number;
  groundwater_category: string | null;
  recommendations: Recommendation[];
}

export interface FertilizerPlan {
  plot_id: string;
  crop_label: Record<Lang, string>;
  source: string;
  oc_pct: number | null;
  oc_status: string | null;
  ph: number | null;
  doses: { nutrient: string; kg_ha: number }[];
  urea_kg_ha: number;
  dap_kg_ha: number;
  mop_kg_ha: number;
  amendments: string[];
  notes: string[];
}

export interface NdviDriver {
  feature: string;
  label: string;
  value: number;
  typical: number;
  effect: number;
  direction: "below" | "above";
}

export interface NdviForecast {
  plot_id: string;
  current_date: string;
  current_ndvi: number;
  predicted_date: string;
  predicted_ndvi: number;
  delta: number;
  baseline_ndvi: number | null;
  stress_warning: boolean;
  stress_reason: "drop" | "seasonal" | "both" | null;
  drivers: NdviDriver[];
}

export interface NdviEval {
  model: string;
  cv: string;
  horizon_days: number;
  model_rmse: number;
  persistence_rmse: number;
  skill_vs_persistence_pct: number;
  n_samples: number;
  n_plots: number;
  features: { feature: string; label: string }[];
  top_drivers: { feature: string; label: string }[];
}

export interface HealthLogEntry {
  id: number;
  created_at: string;
  source: string;
  transcript: string | null;
  photo_url: string | null;
  diagnosis: string | null;
  confidence: number | null;
  severity: string | null;
  treatment: string | null;
  escalated: boolean;
  expert_reply: string | null;
  replied_at: string | null;
  degraded?: boolean;
  plot?: { farmer: string; village: string; crop: string };
}

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

async function postForm<T>(url: string, form: FormData): Promise<T> {
  const r = await fetch(url, { method: "POST", body: form });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

async function postBlob(url: string, body: unknown): Promise<Blob> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.blob();
}

export const api = {
  regions: () => get<Region[]>("/api/regions"),
  plots: (region?: string) => get<Plot[]>(`/api/plots${region ? `?region=${region}` : ""}`),
  ndviForecast: (id: string) => get<NdviForecast>(`/api/forecast/ndvi?plot_id=${id}`),
  ndviEval: () => get<NdviEval>("/api/forecast/ndvi/eval"),
  tts: (text: string, lang: Lang) => postBlob("/api/tts", { text, lang }),
  indicators: (id: string) => get<Indicator[]>(`/api/plots/${id}/indicators`),
  alerts: (id: string, mode: string) =>
    get<AlertsResponse>(`/api/alerts?plot_id=${id}&mode=${mode}`),
  recommend: (id: string) => get<RecommendResponse>(`/api/recommend?plot_id=${id}`),
  advisory: (body: { plot_id: string; question: string; lang: Lang }) =>
    post<{ answer: string; transcript: string | null; degraded: boolean }>(
      "/api/advisory",
      body,
    ),
  advisoryVoice: (form: FormData) =>
    postForm<{ answer: string; transcript: string | null; degraded: boolean }>(
      "/api/advisory/voice",
      form,
    ),
  healthLogs: (id: string) => get<HealthLogEntry[]>(`/api/health-log?plot_id=${id}`),
  createHealthLog: (form: FormData) => postForm<HealthLogEntry>("/api/health-log", form),
  rskCases: () => get<HealthLogEntry[]>("/api/rsk/cases"),
  rskReply: (id: number, reply: string) =>
    post<HealthLogEntry>(`/api/rsk/cases/${id}/reply`, { reply }),
  smsInbound: (body: { plot_id: string; text: string; lang: Lang }) =>
    post<{ reply: string; lang: Lang; segments: number }>("/api/sms/inbound", body),
  fertilizer: (id: string) => get<FertilizerPlan>(`/api/fertilizer?plot_id=${id}`),
  sensors: (id: string) =>
    get<{ ts: string; metric: string; value: number }[]>(`/api/sensors?plot_id=${id}`),
  addSensorReading: (body: { plot_id: string; metric: string; value: number }) =>
    post<{ id: number; ts: string }>("/api/sensors/reading", body),
};
