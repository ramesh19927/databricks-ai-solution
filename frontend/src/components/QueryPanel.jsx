import { useState } from "react";

export default function QueryPanel({ onSearch, context }) {
  const [query, setQuery] = useState("Scope of work");
  const [status, setStatus] = useState("");

  const run = async () => {
    setStatus("Searching...");
    try {
      await onSearch(query);
      setStatus("Done");
    } catch (err) {
      setStatus(err.message);
    }
  };

  return (
    <div className="panel">
      <h2>Retrieve</h2>
      <input value={query} onChange={(e) => setQuery(e.target.value)} />
      <button onClick={run}>Search</button>
      <p className="muted">{status}</p>
      <ul className="context-list">
        {context.map((item) => (
          <li key={item.id}>{item.content.slice(0, 120)}...</li>
        ))}
      </ul>
    </div>
  );
}
