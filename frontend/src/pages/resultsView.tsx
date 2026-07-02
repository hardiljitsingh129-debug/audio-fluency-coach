import Timeline from "./timeline"; 
import { type AnalyzeResponse } from "../lib/api";

export default function ResultsView({ result }: { result: AnalyzeResponse }) {
  const { index, confidence, quality, features, event_rates, tips, events } = result;
  const duration = quality.duration_sec ?? 0;

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