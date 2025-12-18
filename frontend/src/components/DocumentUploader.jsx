import { useState } from "react";

export default function DocumentUploader({ apiBase, headers }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");

  const upload = async () => {
    if (!file) return;
    setStatus("Uploading...");
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${apiBase}/documents/upload`, {
      method: "POST",
      headers,
      body: form,
    });
    if (!res.ok) {
      setStatus("Upload failed");
      return;
    }
    const data = await res.json();
    setStatus(`Uploaded. Chunks: ${data.chunk_count}`);
  };

  return (
    <div className="panel">
      <h2>Ingest Materials</h2>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0])} />
      <button onClick={upload}>Upload</button>
      <p className="muted">{status}</p>
    </div>
  );
}
