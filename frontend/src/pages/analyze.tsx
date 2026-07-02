import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { analyzeFile } from "../lib/api";
import ResultsView from "./resultsView"; 

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  
  const { mutate, data, isPending, error } = useMutation({ 
    mutationFn: analyzeFile 
  });

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: "0 auto", fontFamily: "sans-serif" }}>
      <h2>Audio Fluency — Analyze</h2>

      <div style={{ padding: 20, border: "2px dashed #ccc", borderRadius: 8, marginBottom: 16 }}>
        <input type="file" accept="audio/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button 
          disabled={!file || isPending} 
          onClick={() => file && mutate(file)} 
          style={{ marginLeft: 12, padding: "6px 12px", cursor: "pointer" }}
        >
          {isPending ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error && <p style={{ color: "red" }}>Error: {(error as Error).message}</p>}
      
      {data && <ResultsView result={data} />}
    </div>
  );
}