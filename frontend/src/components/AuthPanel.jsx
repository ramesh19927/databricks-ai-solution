import { useState } from "react";

export default function AuthPanel({ apiBase, onLogin }) {
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("password123");
  const [status, setStatus] = useState("");

  const register = async () => {
    setStatus("Registering...");
    await fetch(`${apiBase}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setStatus("Registered. You can login now.");
  };

  const login = async () => {
    setStatus("Logging in...");
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const res = await fetch(`${apiBase}/auth/login`, { method: "POST", body: form });
    if (!res.ok) {
      setStatus("Login failed");
      return;
    }
    const data = await res.json();
    onLogin(data.access_token, data.refresh_token);
    setStatus("Logged in");
  };

  return (
    <div className="panel">
      <h2>Authenticate</h2>
      <label>Email</label>
      <input value={email} onChange={(e) => setEmail(e.target.value)} />
      <label>Password</label>
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <div className="row">
        <button onClick={register}>Register</button>
        <button onClick={login}>Login</button>
      </div>
      <p className="muted">{status}</p>
    </div>
  );
}
