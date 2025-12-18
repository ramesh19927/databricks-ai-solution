import { useState } from "react";

export default function SowPanel({ apiBase, headers, context }) {
  const [projectId, setProjectId] = useState("demo-project");
  const [requirements, setRequirements] = useState("Ingest docs\nGenerate SoW");
  const [constraints, setConstraints] = useState("");
  const [tone, setTone] = useState("professional");
  const [sow, setSow] = useState("");
  const [status, setStatus] = useState("");

  const generate = async () => {
    setStatus("Generating...");
    const body = {
      project_id: projectId,
      requirements: requirements.split("\n").filter(Boolean),
      constraints: constraints ? constraints.split("\n") : [],
      tone,
      include_retrieval: true,
      query: projectId,
    };
    const res = await fetch(`${apiBase}/sow/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      setStatus("Failed to generate");
      return;
    }
    const data = await res.json();
    setSow(data.body);
    setStatus(`Generated at ${data.created_at}`);
  };

  return (
    <div className="panel">
      <h2>Generate SoW</h2>
      <label>Project ID</label>
      <input value={projectId} onChange={(e) => setProjectId(e.target.value)} />
      <label>Requirements</label>
      <textarea rows={4} value={requirements} onChange={(e) => setRequirements(e.target.value)} />
      <label>Constraints</label>
      <textarea rows={2} value={constraints} onChange={(e) => setConstraints(e.target.value)} />
      <label>Tone</label>
      <input value={tone} onChange={(e) => setTone(e.target.value)} />
      <button onClick={generate}>Generate SoW</button>
      <p className="muted">{status}</p>
      {context.length > 0 && (
        <details>
          <summary>Context used ({context.length})</summary>
          <ul>
            {context.map((item) => (
              <li key={item.id}>{item.content.slice(0, 80)}...</li>
            ))}
          </ul>
        </details>
      )}
      {sow && (
        <div className="sow-preview">
          <h3>Preview</h3>
          <pre>{sow}</pre>
        </div>
      )}
    </div>
  );
}
