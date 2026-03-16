export default function Home() {
  return (
    <main style={{ 
      minHeight: "100vh", 
      display: "flex", 
      flexDirection: "column", 
      alignItems: "center", 
      justifyContent: "center",
      fontFamily: "system-ui, -apple-system, sans-serif",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    }}>
      <div style={{
        background: "white",
        padding: "3rem",
        borderRadius: "1rem",
        boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
        textAlign: "center"
      }}>
        <h1 style={{ 
          fontSize: "2.5rem", 
          fontWeight: "800",
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          marginBottom: "1rem"
        }}>
          Vikki
        </h1>
        <p style={{ color: "#6b7280", fontSize: "1.125rem", marginBottom: "2rem" }}>
          Fullstack Platform • FastAPI + Next.js
        </p>
        <div style={{ 
          display: "flex", 
          gap: "1rem",
          justifyContent: "center"
        }}>
          <a 
            href="/api/health" 
            style={{
              display: "inline-block",
              padding: "0.75rem 1.5rem",
              background: "#667eea",
              color: "white",
              textDecoration: "none",
              borderRadius: "0.5rem",
              fontWeight: "600",
              transition: "background 0.2s"
            }}
          >
            API Health
          </a>
          <a 
            href="/docs" 
            style={{
              display: "inline-block",
              padding: "0.75rem 1.5rem",
              background: "#f3f4f6",
              color: "#374151",
              textDecoration: "none",
              borderRadius: "0.5rem",
              fontWeight: "600",
              transition: "background 0.2s"
            }}
          >
            API Docs
          </a>
        </div>
      </div>
    </main>
  );
}
