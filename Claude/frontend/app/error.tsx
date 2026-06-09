"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // In production this is where you'd report to an error service.
    console.error("App error boundary:", error);
  }, [error]);

  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
        <AlertTriangle className="h-7 w-7" />
      </div>
      <div>
        <h1 className="font-serif text-xl font-semibold">Terjadi kesalahan</h1>
        <p className="mt-1 max-w-md text-sm text-muted-foreground">
          Aplikasi mengalami galat tak terduga. Coba muat ulang halaman. Jika
          berlanjut, periksa konsol peramban dan status backend.
        </p>
      </div>
      <Button onClick={reset}>
        <RefreshCw className="h-4 w-4" />
        Muat ulang
      </Button>
    </div>
  );
}
