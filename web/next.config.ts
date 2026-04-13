import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/workspace/:path*",
        destination: "http://127.0.0.1:8000/workspace/:path*",
      },
    ];
  },
};

export default nextConfig;
