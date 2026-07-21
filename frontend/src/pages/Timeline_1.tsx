// Timeline_1.tsx
type Span = { start: number; end: number; confidence: number };

type Events = {
  blocks: Span[];
  repetitions: Span[];
  prolongations: Span[];
};

export default function Timeline({
  events,
  duration,
  xRange,
}: {
  events: Events;
  duration: number;
  xRange?: [number, number];
}) {
  const width = 920;
  const height = 40;

  const xmin = xRange?.[0] ?? 0;
  const xmax = xRange?.[1] ?? duration;
  const span = Math.max(1e-6, xmax - xmin);

  const scale = (t: number) => ((t - xmin) / span) * width;

  const visible = (arr: Span[]) =>
    arr.filter((ev) => ev.end > xmin && ev.start < xmax);

  const clipRange = (s: number, e: number): [number, number] => [
    Math.max(s, xmin),
    Math.min(e, xmax),
  ];

  const Bar = ({ ev, color }: { ev: Span; color: string }) => {
    const [cs, ce] = clipRange(ev.start, ev.end);
    const x = scale(cs);
    const w = Math.max(2, scale(ce) - scale(cs)); // keep thin ticks visible
    const opacity = 0.25 + 0.65 * Math.max(0, Math.min(1, ev.confidence ?? 1));
    return <rect x={x} y={5} width={w} height={30} fill={color} opacity={opacity} rx={2} />;
  };

  return (
    <svg
      role="img"
      aria-label="Disfluency timeline"
      width={width}
      height={height}
      style={{ background: "#f7f7f7", border: "1px solid #ddd", borderRadius: 4 }}
    >
      {/* Blocks (red) */}
      {visible(events.blocks).map((ev, i) => (
        <Bar key={`b${i}`} ev={ev} color="#e34a33" />
      ))}
      {/* Repetitions (yellow) */}
      {visible(events.repetitions).map((ev, i) => (
        <Bar key={`r${i}`} ev={ev} color="#fecc5c" />
      ))}
      {/* Prolongations (blue) */}
      {visible(events.prolongations).map((ev, i) => (
        <Bar key={`p${i}`} ev={ev} color="#2b8cbe" />
      ))}

      {/* Baseline */}
      <line x1={0} y1={39} x2={width} y2={39} stroke="#666" strokeWidth={1} />
    </svg>
  );
}
