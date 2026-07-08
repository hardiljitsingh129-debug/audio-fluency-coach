type Span = [number, number];
type Events = {
  blocks: Span[];
  repetitions: Span[];
  prolongations: Span[];
};

export default function Timeline_1({
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

  const visible = (arr: Span[]) => arr.filter(([s, e]) => e > xmin && s < xmax);
  const clip = (s: number, e: number): Span => [Math.max(s, xmin), Math.min(e, xmax)];

  const Bar = ({ s, e, color }: { s: number; e: number; color: string }) => {
    const [cs, ce] = clip(s, e);
    const x = scale(cs);
    const w = Math.max(2, scale(ce) - scale(cs)); // keep thin ticks visible
    return <rect x={x} y={5} width={w} height={30} fill={color} opacity={0.75} rx={2} />;
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
      {visible(events.blocks).map(([s, e], i) => (
        <Bar key={`b${i}`} s={s} e={e} color="#e34a33" />
      ))}
      {/* Repetitions (yellow) */}
      {visible(events.repetitions).map(([s, e], i) => (
        <Bar key={`r${i}`} s={s} e={e} color="#fecc5c" />
      ))}
      {/* Prolongations (blue) */}
      {visible(events.prolongations).map(([s, e], i) => (
        <Bar key={`p${i}`} s={s} e={e} color="#2b8cbe" />
      ))}

      {/* Baseline */}
      <line x1={0} y1={39} x2={width} y2={39} stroke="#666" strokeWidth={1} />
    </svg>
  );
}
