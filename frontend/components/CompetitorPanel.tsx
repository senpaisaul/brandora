"use client";

import { useEffect, useState } from "react";
import { Ad, Brand, Competitor, api } from "@/lib/api";
import { AdCard } from "@/components/AdCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface CompetitorPanelProps {
    brand: Brand;
}

export function CompetitorPanel({ brand }: CompetitorPanelProps) {
    const [competitors, setCompetitors] = useState<Competitor[]>([]);
    const [adsByCompetitor, setAdsByCompetitor] = useState<Record<number, Ad[]>>({});
    const [loading, setLoading] = useState(true);

    // Form state
    const [name, setName] = useState("");
    const [fbUrl, setFbUrl] = useState("");
    const [scraping, setScraping] = useState(false);
    const [analyzing, setAnalyzing] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    const reload = async () => {
        setLoading(true);
        try {
            const comps = await api.listCompetitors(brand.id);
            setCompetitors(comps);
            const ads: Record<number, Ad[]> = {};
            for (const c of comps) {
                ads[c.id] = await api.listCompetitorAds(c.id);
            }
            setAdsByCompetitor(ads);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        reload();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [brand.id]);

    const handleCreate = async () => {
        setScraping(true);
        setError(null);
        try {
            await api.createCompetitor(brand.id, name, fbUrl);
            setName("");
            setFbUrl("");
            await reload();
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setScraping(false);
        }
    };

    const handleAnalyze = async (competitorId: number) => {
        setAnalyzing(competitorId);
        setError(null);
        try {
            await api.analyzeAllForCompetitor(competitorId);
            await reload();
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setAnalyzing(null);
        }
    };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Add competitor</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="comp-name">Competitor name</Label>
                            <Input
                                id="comp-name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Bellroy"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="comp-url">Facebook page URL</Label>
                            <Input
                                id="comp-url"
                                value={fbUrl}
                                onChange={(e) => setFbUrl(e.target.value)}
                                placeholder="https://www.facebook.com/bellroy.official/"
                            />
                        </div>
                    </div>
                    <Button onClick={handleCreate} disabled={scraping || !name || !fbUrl}>
                        {scraping ? "Scraping ads (~60-120s)…" : "Scrape competitor ads"}
                    </Button>
                    {error && <p className="text-sm text-red-600">{error}</p>}
                </CardContent>
            </Card>

            {loading && <p className="text-sm text-slate-500">Loading competitors…</p>}

            {competitors.map((c) => {
                const ads = adsByCompetitor[c.id] || [];
                return (
                    <Card key={c.id}>
                        <CardHeader>
                            <div className="flex items-baseline justify-between">
                                <CardTitle>{c.name}</CardTitle>
                                <div className="flex items-center gap-3">
                                    <span className="text-xs text-slate-500">
                                        {ads.length} {ads.length === 1 ? "ad" : "ads"}
                                    </span>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleAnalyze(c.id)}
                                        disabled={analyzing === c.id || ads.length === 0}
                                    >
                                        {analyzing === c.id ? "Analyzing…" : "Re-analyze all"}
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            {ads.length === 0 ? (
                                <p className="text-sm text-slate-500">No ads yet.</p>
                            ) : (
                                <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                    {ads.map((ad) => (
                                        <AdCard key={ad.id} ad={ad} />
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                );
            })}
        </div>
    );
}