import React, { useState } from "react";

function App() {
  const [report, setReport] = useState({ title: "", description: "", location: "" });
  const [result, setResult] = useState<string>("");

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const res = await fetch("http://localhost:8000/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    });
    const json = await res.json();
    setResult(JSON.stringify(json, null, 2));
  };

  return (
    <div style={{ fontFamily: "Arial, sans-serif", padding: 24 }}>
      <h1>Hoos Alert Prototype</h1>
      <form onSubmit={submit} style={{ display: "grid", gap: 10, maxWidth: 420 }}>
        <input value={report.title} placeholder="Title" onChange={(e) => setReport({ ...report, title: e.target.value })} />
        <input value={report.location} placeholder="Location" onChange={(e) => setReport({ ...report, location: e.target.value })} />
        <textarea value={report.description} placeholder="Description" onChange={(e) => setReport({ ...report, description: e.target.value })} />
        <button type="submit">Submit</button>
      </form>
      <pre style={{ whiteSpace: "pre-wrap", marginTop: 16 }}>{result}</pre>
    </div>
  );
}

export default App;
