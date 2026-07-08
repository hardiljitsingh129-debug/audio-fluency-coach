import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { analyzeFile, type AnalyzeResponse , type ApiError} from "../lib/api";
{/*import ResultsView from "./resultsView"; 8*/}
import ResultsView_1 from "./ResultView";

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<string>("assessment");
  

  // TanStack useMutation hook parameters
  const { mutate, data, isPending, error } = useMutation<
    AnalyzeResponse,
    ApiError,
    { file: File; mode: string }
  >({
    mutationFn: ({ file, mode }: { file: File; mode: string }) => analyzeFile(file, mode),
  });

  function getErrorText(error: ApiError | null | undefined): string {
    if (!error) return "An unknown error occurred.";
    return error.response?.data?.detail ?? error.message;
  }

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: "0 auto", fontFamily: "sans-serif" }}>
      <h2>Audio Fluency — Analyze</h2>
      
      <div style={{ padding: 20, border: "2px dashed #ccc", borderRadius: 8, marginBottom: 16 }}>
        {/* Mode dropdown option switcher component */}
        <select 
          value={mode} 
          onChange={(e) => setMode(e.target.value)} 
          style={{ marginRight: 12, padding: "6px 12px", cursor: "pointer" }}
        >
          <option value="assessment">Assessment</option>
          <option value="prolonged">Prolonged</option>
          <option value="conversation">Conversation</option>
        </select>

        <input 
          type="file" 
          accept="audio/*" 
          onChange={(e) => setFile(e.target.files?.[0] ?? null)} 
        />
        
        <button 
          disabled={!file || isPending} 
          onClick={() => file && mutate({ file, mode })} 
          style={{ marginLeft: 12, padding: "6px 12px", cursor: "pointer" }}
        >
          {isPending ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {/* Exception block notification layout bounds */}
      
      {error && (
        <p style={{ color: "red" }}>
          Error: {getErrorText(error)}
        </p>
      )}

      {/* Render evaluation timeline result matrix viewport */}
      {/* 
      {data && <ResultsView key = {data.file} result={data as AnalyzeResponse} />}
      */}
      
      {data && <ResultsView_1 key = {data.file} result={data as AnalyzeResponse} />}
    </div>
  );
}