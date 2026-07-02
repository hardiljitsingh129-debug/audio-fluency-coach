type Events = { 
  blocks: [number, number][]; 
  repetitions: [number, number][]; 
  prolongations: [number, number][]; 
};

export default function Timeline({ events, duration }: { events: Events; duration: number }) {
  const width = 900;
  const height = 40;
  
  const scale = (t: number) => (duration > 0 ? (t / duration) * width : 0);

  const Bar = ({ s, e, color }: { s: number; e: number; color: string }) => (
    <rect 
      x={scale(s)} 
      y={5} 
      width={Math.max(2, scale(e) - scale(s))} 
      height={30} 
      fill={color} 
      opacity={0.8} 
    />
  );

  return (
    <div>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} style={{ background: "#f7f7f7", border: "1px solid #ddd", borderRadius: 4 }}>
        {events.blocks.map(([s, e], i) => (
          <Bar key={`b-${i}`} s={s} e={e} color="#e34a33" />
        ))}
        {events.repetitions.map(([s, e], i) => (
          <Bar key={`r-${i}`} s={s} e={e} color="#fecc5c" />
        ))}
        {events.prolongations.map(([s, e], i) => (
          <Bar key={`p-${i}`} s={s} e={e} color="#2b8cbe" />
        ))}
      </svg>
      <div style={{ display: "flex", gap: "16px", marginTop: "8px", fontSize: "12px" }}>
        <span><span style={{ color: "#e34a33" }}>■</span> Blocks</span>
        <span><span style={{ color: "#fecc5c" }}>■</span> Repetitions</span>
        <span><span style={{ color: "#2b8cbe" }}>■</span> Prolongations</span>
      </div>
    </div>
  );
}