/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The frontend talks to the FastAPI backend. In dev we proxy /backend-api/*
  // to the backend origin so the browser never hits CORS during local work.
  // In production, set NEXT_PUBLIC_API_BASE_URL to the deployed backend URL.
  async rewrites() {
    const backend = process.env.BACKEND_ORIGIN || "http://localhost:8000";
    return [
      { source: "/backend-api/:path*", destination: `${backend}/:path*` },
    ];
  },
};
export default nextConfig;
