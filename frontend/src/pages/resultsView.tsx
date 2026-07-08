import Timeline from "./timeline"; 
import { type AnalyzeResponse } from "../lib/api";
import { useState } from "react";

export default function ResultsView({ result }: { result: AnalyzeResponse }) {
  const { index, confidence, quality, features, event_rates, tips, events } = result;
  const duration = quality.duration_sec ?? 0;

  const [xMin, setXMin] = useState<number>(0);
  const [xMax, setXMax] = useState<number>(duration);


  return (
    <div style={{ marginTop: 24, fontFamily: "sans-serif" }}>
      <h3>Summary</h3>
      <p>
        <strong>Index:</strong> {index.toFixed(1)} · 
        <strong> Confidence:</strong> {confidence}
      </p>
      <p style={{ color: "#666" }}>
        SNR: {quality.snr_proxy_db?.toFixed(1)} dB · 
        Speech ratio: {quality.speech_ratio?.toFixed(2)} · 
        Duration: {duration.toFixed(1)} s
      </p>

      {/* Timeline and Zoom controls */}
      <div style={{ background: "#fdfdfd", border: "1px solid #eee", padding: 12, borderRadius: 6, marginBottom: 16 }}>
        <span style={{ marginRight: 16, fontSize: 14, fontWeight: "bold" }}>Timeline Zoom Controls:</span>
        <label style={{ marginRight: 12, fontSize: 13 }}>
          Zoom start (s): 
          <input 
            type="number" 
            step="0.1"
            min="0"
            max={duration}
            value={xMin} 
            onChange={(e) => setXMin(Math.max(0, Math.min(+e.target.value, xMax - 0.1)))}
            style={{ marginLeft: 6, width: 70, padding: "2px 4px" }}
          />
        </label>
        <label style={{ fontSize: 13 }}>
          end (s): 
          <input 
            type="number" 
            step="0.1"
            min="0"
            max={duration}
            value={xMax} 
            onChange={(e) => setXMax(Math.min(duration, Math.max(+e.target.value, xMin + 0.1)))}
            style={{ marginLeft: 6, width: 70, padding: "2px 4px" }}
          />
        </label>
      </div>

      <h4>Timeline (Speech Dysfluency Distribution)</h4>
      {/* 4.1 Passing updated xRange down to Timeline component */}
      <Timeline events={events} duration={duration} xRange={[xMin, xMax]} />
      
      {/* Legend layout */}
      <div style={{ display: "flex", gap: "16px", marginTop: "8px", marginBottom: 20, fontSize: "12px", justifyContent: "center" }}>
        <span><span style={{ color: "#e34a33" }}>■</span> Blocks</span>
        <span><span style={{ color: "#fecc5c" }}>■</span> Repetitions</span>
        <span><span style={{ color: "#2b8cbe" }}>■</span> Prolongations</span>
      </div>
      
      <h4>Features</h4>
      <ul style = {{ display: "inline-block", textAlign: "center", paddingLeft: 0, listStyle: "none" }}>
        <li>Articulation rate: {features.articulation_rate?.toFixed(2)} syll/s</li>
        <li>Pause ratio: {((features.pause_ratio ?? 0) * 100).toFixed(0)}%</li>
        <li>Long pause share: {((features.long_pause_share ?? 0) * 100).toFixed(0)}%</li>
        <li>F0 CV: {features.f0_cv?.toFixed(2)}</li>
      </ul>

      <h4>Event rates (per voiced minute)</h4>
      <ul style = {{ display: "inline-block", textAlign: "center", paddingLeft: 0, listStyle: "none" }}>
        <li>Blocks: {event_rates.blocks_per_min}</li>
        <li>Repetitions: {event_rates.repetitions_per_min}</li>
        <li>Prolongations: {event_rates.prolongations_per_min}</li>
      </ul>

      <h4>Timeline (Speech Dysfluency Distribution)</h4>
      <Timeline events={events} duration={duration} />

      <h4>Tips</h4>
      <ul style = {{ display: "inline-block", textAlign: "center", paddingLeft: 0, listStyle: "none" }}>
        {tips.map((t, i) => (
          <li key={i} style={{ marginBottom: 8 }}>
            <strong>{t.title}:</strong> {t.detail}
          </li>
        ))}
      </ul>
    </div>
  );
}