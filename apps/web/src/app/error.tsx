"use client";

import { useEffect } from "react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <section className="page-stack">
      <div className="panel unavailable-state" role="alert">
        <p className="eyebrow">Data unavailable</p>
        <h1>The Opportunity API could not be loaded</h1>
        <p>{error.message || "The backend did not return a usable response."}</p>
        <button onClick={reset} type="button">
          Retry
        </button>
      </div>
    </section>
  );
}
