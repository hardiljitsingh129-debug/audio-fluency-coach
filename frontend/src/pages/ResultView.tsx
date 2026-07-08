import { useMemo, useState } from "react";
{/*import Timeline from "./Timeline"; */ }
import Timeline_1 from "./Timeline_1";
import type { AnalyzeResponse } from "../lib/api";

type Props = { result: AnalyzeResponse };

export default function ResultsView({ result }: Props) {
  const duration = result.quality.duration_sec ?? 0;

  // Default view: full range
  const [xmin, setXmin] = useState(0);
  const [xmax, setXmax] = useState(duration);

  // Keep range valid and snap to 0.1s
  const step = 0.1;
  const onMinChange = (v: number) => setXmin(Math.max(0, Math.min(v, xmax - step)));
  const onMaxChange = (v: number) => setXmax(Math.min(duration, Math.max(v, xmin + step)));

  // Pretty helpers
  const snr = safeNum(result.quality.snr_proxy_db);
  const speechRatio = safeNum(result.quality.speech_ratio);
  const voicedMin = useMemo(
    () => (safeNum(result.features.voiced_duration) / 60) || 0,
    [result.features.voiced_duration]
  );

  return (
    <div style={{ marginTop: 24 }}>
      <Section title="Summary">
        <p>
          <b>Index:</b> {fmt1(result.index)} · <b>Confidence:</b> {result.confidence}
          <br />
          <b>SNR:</b> {fmt1(snr)} dB · <b>Speech ratio:</b> {fmt2(speechRatio)} ·{" "}
          <b>Duration:</b> {fmt1(duration)} s
        </p>
      </Section>

      <Section title="Timeline Zoom">
        <RangeRow
          duration={duration}
          xmin={xmin}
          xmax={xmax}
          step={step}
          onMinChange={onMinChange}
          onMaxChange={onMaxChange}
        />
      </Section>

      <Section title="Timeline (Speech Disfluency Distribution)">
        <Timeline_1 events={result.events} duration={duration} xRange={[xmin, xmax]} />
        <p style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
          Legend: <Swatch color="#e34a33" /> Blocks · <Swatch color="#fecc5c" /> Repetitions ·{" "}
          <Swatch color="#2b8cbe" /> Prolongations
        </p>
      </Section>

    

      <Section title="Features">
        <ul>
          <li>Articulation rate: {fmt2(result.features.articulation_rate)} syll/s</li>
          <li>Pause ratio: {pct(result.features.pause_ratio)}</li>
          <li>Long pause share: {pct(result.features.long_pause_share)}</li>
          <li>F0 CV: {fmt2(result.features.f0_cv)}</li>
        </ul>
      </Section>

      <Section title="Event rates (per voiced minute)">
        <ul>
          <li>Blocks: {fmt2(result.event_rates.blocks_per_min)}</li>
          <li>Repetitions: {fmt2(result.event_rates.repetitions_per_min)}</li>
          <li>Prolongations: {fmt2(result.event_rates.prolongations_per_min)}</li>
        </ul>
      </Section>

      <Section title="Tips">
        <ul>
          {result.tips?.map((t, i) => (
            <li key={i}>
              <b>{t.title}:</b> {t.detail}
            </li>
          ))}
          {!result.tips?.length && <li>No tips for this clip.</li>}
        </ul>
      </Section>

      <Section title="Targets & Thresholds">
        <p style={{ marginBottom: 6 }}>
          <b>Targets</b> — Articulation {result.targets.articulation_rate[0]}–
          {result.targets.articulation_rate[1]} syll/s ({result.targets.mode}); Pause 7–10%;
          F0 CV 0.05–0.20
        </p>
        {result.thresholds && (
          <p>
            <b>Thresholds</b> — Reps sim {result.thresholds.sim_thresh}, ref{" "}
            {result.thresholds.refractory_s}s · Pros flux {result.thresholds.flux_thresh}, F0‑CV{" "}
            {result.thresholds.f0_cv_max} · Blocks min {result.thresholds.min_ms}ms
          </p>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 18 }}>
      <h4 style={{ margin: "8px 0" }}>{title}</h4>
      {children}
    </div>
  );
}

function RangeRow({
  duration,
  xmin,
  xmax,
  step,
  onMinChange,
  onMaxChange,
}: {
  duration: number;
  xmin: number;
  xmax: number;
  step: number;
  onMinChange: (v: number) => void;
  onMaxChange: (v: number) => void;
}) {
  if (!isFinite(duration) || duration <= 0) {
    return <p style={{ color: "#666" }}>No duration available.</p>;
  }
  const toPct = (t: number) => (t / duration) * 100;
  const fromValue = (v: string) => Number(v);

  return (
    <div style={{ maxWidth: 920 }}>
      {/* Sliders share the same 0..duration scale */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ width: 70, textAlign: "right" }}>Start</span>
        <input
          type="range"
          min={0}
          max={duration}
          step={step}
          value={xmin}
          onChange={(e) => onMinChange(fromValue(e.target.value))}
          style={{ flex: 1 }}
        />
        <span style={{ width: 62 }}>{fmt1(xmin)} s</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 6 }}>
        <span style={{ width: 70, textAlign: "right" }}>End</span>
        <input
          type="range"
          min={0}
          max={duration}
          step={step}
          value={xmax}
          onChange={(e) => onMaxChange(fromValue(e.target.value))}
          style={{ flex: 1 }}
        />
        <span style={{ width: 62 }}>{fmt1(xmax)} s</span>
      </div>
      {/* Visual guide bar (optional): shows the selected window proportionally */}
      <div style={{ marginTop: 6, height: 6, background: "#eee", position: "relative", borderRadius: 3 }}>
        <div
          style={{
            position: "absolute",
            left: `${toPct(xmin)}%`,
            width: `${Math.max(0, toPct(xmax) - toPct(xmin))}%`,
            top: 0,
            bottom: 0,
            background: "#c5e1fa",
            borderRadius: 3,
          }}
        />
      </div>
    </div>
  );
}

function Swatch({ color }: { color: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        background: color,
        marginRight: 4,
        verticalAlign: "middle",
      }}
    />
  );
}

function pct(x: unknown) {
  const v = safeNum(x);
  if (!isFinite(v)) return "—";
  return `${Math.round(v * 100)}%`;
}
function fmt1(x: unknown) {
  const v = safeNum(x);
  return isFinite(v) ? v.toFixed(1) : "—";
}
function fmt2(x: unknown) {
  const v = safeNum(x);
  return isFinite(v) ? v.toFixed(2) : "—";
}
function safeNum(x: unknown): number {
  const n = typeof x === "number" ? x : Number(x);
  return Number.isFinite(n) ? n : NaN;
}