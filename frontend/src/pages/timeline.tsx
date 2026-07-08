type Events = { 
  blocks: [number, number][]; 
  repetitions: [number, number][]; 
  prolongations: [number, number][]; 
};

interface TimelineProps {
  events: Events;
  duration: number;
  xRange?: [number, number];
}

export default function Timeline({ events, duration, xRange }: TimelineProps) {
  const width = 900;
  const height = 40;
  
  const [xMin, xMax] = xRange ?? [0, duration];
  const span =- Math.max(1e-6, xMax - xMin); //Not zero to avoid division by zero

  const scale = (t: number) => ((t - xMin) / span) * width;
  const clip = (s: number, e: number) => [Math.max(s, xMin), Math.min(e, xMax)] as [number, number];

  const visible = <T extends [number, number]>(arr: T[]) => 
    arr.filter(([s, e]) => e > xMin && s < xMax);

  const Bar = ({ s, e, color }: { s: number; e: number; color: string }) => {
    const [cs, ce] = clip(s, e);
    const w = Math.max(2, scale(ce) - scale(cs));
    return (
      <rect 
        x={scale(cs)} 
        y={5} 
        width={w} 
        height={30} 
        fill={color} 
        opacity={0.8} 
      />
    );
  };

  return (
    <div style={{ width: "100%", overflow: "hidden", margin: "12px 0" }}>
      <svg 
        width="100%" 
        viewBox={`0 0 ${width} ${height}`} 
        style={{ background: "#f7f7f7", border: "1px solid #ddd", borderRadius: 4 }}
      >
        {visible(events.blocks).map(([s, e], i) => (
          <Bar key={`b-${i}`} s={s} e={e} color="#e34a33" />
        ))}
        {visible(events.repetitions).map(([s, e], i) => (
          <Bar key={`r-${i}`} s={s} e={e} color="#fecc5c" />
        ))}
        {visible(events.prolongations).map(([s, e], i) => (
          <Bar key={`p-${i}`} s={s} e={e} color="#2b8cbe" />
        ))}
      </svg>
    </div>
  );
}