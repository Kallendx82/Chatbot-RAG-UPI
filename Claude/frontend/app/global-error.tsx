"use client";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="id">
      <body style={{ fontFamily: "system-ui, sans-serif", padding: 40, textAlign: "center" }}>
        <h1 style={{ fontSize: 22, fontWeight: 600 }}>Kesalahan fatal</h1>
        <p style={{ color: "#666", marginTop: 8 }}>
          Aplikasi gagal dimuat. Silakan muat ulang halaman.
        </p>
        <button
          onClick={reset}
          style={{
            marginTop: 16, padding: "8px 16px", borderRadius: 8,
            background: "#1b3a6b", color: "white", border: "none", cursor: "pointer",
          }}
        >
          Muat ulang
        </button>
      </body>
    </html>
  );
}
