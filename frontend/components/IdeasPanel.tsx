"use client";

import { useEffect, useState } from "react";
import { AdIdea, Brand, api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface IdeasPanelProps {
    brand: Brand;
}

export function IdeasPanel({ brand }: IdeasPanelProps) {
    const [ideas, setIdeas] = useState<AdIdea[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const reload = async () => {
        setLoading(true);
        try {
            const list = await api.listIdeas(brand.id);
            setIdeas(list);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        reload();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [brand.id]);

    const handleGenerate = async () => {
        setGenerating(true);
        setError(null);
        try {
            await api.generateIdeas(brand.id);
            await reload();
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div className="space-y-4">
            <Card>
                <CardHeader>
                    <div className="flex items-baseline justify-between">
                        <CardTitle>Ad ideas for {brand.name}</CardTitle>
                        <Button onClick={handleGenerate} disabled={generating}>
                            {generating ? "Generating (Opus 4.7, ~15s)…" : "Generate 2 ideas"}
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
                    {loading ? (
                        <p className="text-sm text-slate-500">Loading…</p>
                    ) : ideas.length === 0 ? (
                        <p className="text-sm text-slate-500">
                            No ideas yet. Click “Generate 2 ideas” once you have analyzed competitor ads.
                        </p>
                    ) : (
                        <div className="space-y-6">
                            {ideas.map((idea, i) => (
                                <IdeaCard key={idea.id} idea={idea} index={i} />
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

function IdeaCard({ idea, index }: { idea: AdIdea; index: number }) {
    const p = idea.payload;
    return (
        <div className="border rounded-lg p-4 space-y-3 bg-slate-50">
            <div className="flex items-center gap-2">
                <Badge>{p.format}</Badge>
                <span className="text-xs text-slate-500">
                    Idea #{idea.id} · generated {new Date(idea.created_at).toLocaleString()}
                </span>
            </div>

            <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                    Hook
                </div>
                <div className="text-lg font-medium italic">"{p.hook}"</div>
            </div>

            <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                    Creative concept
                </div>
                <p className="text-sm text-slate-800">{p.creative_concept}</p>
            </div>

            <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                    Why it fits {idea.brand_id ? "the brand" : ""}
                </div>
                <p className="text-sm text-slate-700">{p.brand_fit_rationale}</p>
            </div>

            <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                    Inspired by competitor ads
                </div>
                <div className="flex flex-wrap gap-1">
                    {p.inspired_by_ad_ids.map((id) => (
                        <Badge key={id} variant="outline">
                            Ad #{id}
                        </Badge>
                    ))}
                </div>
            </div>
        </div>
    );
}