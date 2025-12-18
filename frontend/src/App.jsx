import { useMemo, useState } from "react";
import AuthPanel from "./components/AuthPanel";
import DocumentUploader from "./components/DocumentUploader";
import QueryPanel from "./components/QueryPanel";
import SowPanel from "./components/SowPanel";

const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export default function App() {
  const [tokens, setTokens] = useState(() => ({
    access: localStorage.getItem("access_token") || "",
    refresh: localStorage.getItem("refresh_token") || "",
  }));
  const [messages, setMessages] = useState([]);
  const [context, setContext] = useState([]);

  const authHeaders = useMemo(
    () => ({
      Authorization: `Bearer ${tokens.access}`,
    }),
    [tokens]
  );

  const handleLogin = (access, refresh) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    setTokens({ access, refresh });
    setMessages((prev) => [...prev, { type: "success", text: "Logged in" }]);
  };

  const handleSearch = async (query) => {
    const res = await fetch(`${apiBase}/documents/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error("Search failed");
    const data = await res.json();
    setContext(data);
  };

  return (
    <div className="app">
      <header>
        <h1>Triage System</h1>
        <p>Ingest, retrieve, and generate SoWs backed by Databricks</p>
      </header>

      <section className="grid">
        <div>
          <AuthPanel apiBase={apiBase} onLogin={handleLogin} />
          <DocumentUploader apiBase={apiBase} headers={authHeaders} />
          <QueryPanel onSearch={handleSearch} context={context} />
        </div>
        <div>
          <SowPanel apiBase={apiBase} headers={authHeaders} context={context} />
          <div className="messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={msg.type}>
                {msg.text}
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
