import axios, { type AxiosError } from "axios";

export type ApiError = AxiosError<{ detail?: string }>;

export type EventSpan = {
  start: number;
  end: number;
  confidence: number;
}

export type AnalyzeResponse = {
  api_version: string;
  file: string;
  index: number;
  confidence: "high" | "moderate" | "low";
  quality: Record<string, number>;
  features: Record<string, number>;
  events: { 
    //blocks: [number, number][]; 
    //repetitions: [number, number][]; 
    //prolongations: [number, number][]; 
    blocks: { start: number; end: number; confidence: number }[];
    repetitions: { start: number; end: number; confidence: number }[];
    prolongations: { start: number; end: number; confidence: number }[];
  };
  event_rates: Record<string, number>;
  targets: { articulation_rate: [number, number]; mode: string };
  tips: { title: string; detail: string }[];

  thresholds? : {
    sim_thresh: number;
    refractory_s: number;
    flux_thresh: number;
    f0_cv_max: number;
    min_ms: number;
  }
};

const API = import.meta.env.VITE_API_URL as string;

export async function analyzeFile(file: File, mode: string): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);

  // string backticks configured properly
  const { data } = await axios.post(`${API}/analyze?mode=${encodeURIComponent(mode)}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data as AnalyzeResponse;
}