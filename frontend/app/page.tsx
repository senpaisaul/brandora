"use client";

import { useEffect, useState } from "react";
import { Brand, api } from "@/lib/api";
import { BrandPanel } from "@/components/BrandPanel";
import { CompetitorPanel } from "@/components/CompetitorPanel";
import { IdeasPanel } from "@/components/IdeasPanel";

type TabKey = "brand" | "competitors" | "ideas";

export default function Home() {
  const [brand, setBrand] = useState<Brand | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<TabKey>("competitors");

  useEffect(() => {
    api
      .listBrands()
      .then((brands) => setBrand(brands[0] || null))
      .catch(() => setBrand(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-500">Loading…</p>
      </main>
    );
  }

  if (!brand) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="w-full max-w-xl">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Brandora</h1>
          <p className="text-sm text-slate-600 mb-6">
            Competitive ad intelligence for D2C brands. Create a brand to get started.
          </p>
          <BrandPanel brand={null} onBrandCreated={setBrand} />
        </div>
      </main>
    );
  }

  const tabs: { key: TabKey; label: string; hint: string }[] = [
    { key: "brand", label: "Brand", hint: "Profile" },
    { key: "competitors", label: "Competitors", hint: "Ad library" },
    { key: "ideas", label: "Ideas", hint: "AI-generated" },
  ];

  return (
    <main className="min-h-screen bg-slate-50 flex">
      {/* Sticky sidebar — always visible, full viewport height */}
      <aside className="w-64 shrink-0 border-r border-slate-200 bg-white sticky top-0 h-screen flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <h1 className="text-xl font-bold tracking-tight">Brandora</h1>
          <p className="text-xs text-slate-500 mt-1">Competitive ad intelligence</p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {tabs.map((t) => {
            const active = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={
                  "w-full text-left px-3 py-2 rounded-md transition-colors " +
                  (active
                    ? "bg-slate-900 text-white"
                    : "text-slate-700 hover:bg-slate-100")
                }
              >
                <div className="text-sm font-medium">{t.label}</div>
                <div
                  className={
                    "text-xs " + (active ? "text-slate-300" : "text-slate-500")
                  }
                >
                  {t.hint}
                </div>
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="text-xs text-slate-500">Current brand</div>
          <div className="text-sm font-medium text-slate-800">{brand.name}</div>
          <a
            href={brand.url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-blue-600 hover:underline"
          >
            {brand.url}
          </a>
        </div>
      </aside>

      {/* Main content — scrolls independently */}
      <div className="flex-1 min-w-0">
        <div className="p-6 md:p-10">
          {tab === "brand" && (
            <div className="max-w-3xl">
              <BrandPanel brand={brand} onBrandCreated={setBrand} />
            </div>
          )}
          {tab === "competitors" && <CompetitorPanel brand={brand} />}
          {tab === "ideas" && (
            <div className="max-w-4xl">
              <IdeasPanel brand={brand} />
            </div>
          )}
        </div>
      </div>
    </main>
  );
}