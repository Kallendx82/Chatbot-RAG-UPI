import type { Metadata, Viewport } from "next";
import { Spectral, Asap, JetBrains_Mono } from "next/font/google";

import { ThemeProvider } from "@/components/layout/ThemeProvider";
import "@/styles/globals.css";
import "highlight.js/styles/github-dark.css";

/**
 * Type system (deliberately not Inter/Roboto):
 *  - Spectral: a refined scholarly serif for display/headings + brand.
 *  - Asap: a characterful humanist sans for body text.
 *  - JetBrains Mono: code + metrics.
 */
const display = Spectral({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

const body = Asap({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Asisten Informasi UPI — Chatbot RAG",
  description:
    "Chatbot sumber informasi sivitas Universitas Pendidikan Indonesia berbasis Retrieval-Augmented Generation.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7f4ee" },
    { media: "(prefers-color-scheme: dark)", color: "#0e131f" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" suppressHydrationWarning>
      <body
        className={`${display.variable} ${body.variable} ${mono.variable}`}
      >
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
