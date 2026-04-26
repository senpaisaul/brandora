"use client";

import { useEffect, useState } from "react";
import { Ad, AdAnalysis, api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface AdCardProps {
    ad: Ad;
}

export function AdCard({ ad }: AdCardProps) {
    const [analysis, setAnalysis] = useState<AdAnalysis | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        api
            .getAdAnalysis(ad.id)
            .then((a) => {
                if (!cancelled) setAnalysis(a);
            })
            .catch(() => {
                if (!cancelled) setAnalysis(null);
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => {
            cancelled = true;
        };
    }, [ad.id]);

    const imgSrc = ad.local_image_paths[0] ? api.imageUrl(ad.local_image_paths[0]) : null;

    return (
        <Card className="overflow-hidden">
            <CardHeader className="p-0">
                {imgSrc ? (
                    <img
                        src={imgSrc}
                        alt={ad.headline || "Ad creative"}
                        className="w-full aspect-square object-cover bg-slate-100"
                    />
                ) : (
                    <div className="w-full aspect-square bg-slate-200 flex items-center justify-center text-slate-500 text-sm">
                        No image
                    </div>
                )}
            </CardHeader>

            <CardContent className="p-4 space-y-3">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-xs">
                            {ad.format}
                        </Badge>
                        <span className="text-xs text-slate-500">Ad #{ad.id}</span>
                    </div>
                    {ad.headline && (
                        <CardTitle className="text-base leading-tight">{ad.headline}</CardTitle>
                    )}
                </div>

                {ad.primary_text && (
                    <p className="text-sm text-slate-700 line-clamp-4">{ad.primary_text}</p>
                )}

                {ad.cta_text && (
                    <div className="inline-block px-2 py-1 text-xs bg-slate-900 text-white rounded">
                        {ad.cta_text}
                    </div>
                )}

                <div className="border-t pt-3 mt-3">
                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                        AI Analysis
                    </div>
                    {loading ? (
                        <p className="text-xs text-slate-400">Loading…</p>
                    ) : analysis ? (
                        <div className="space-y-2 text-xs">
                            {analysis.copy_analysis && (
                                <div>
                                    <div className="font-medium text-slate-600">Copy</div>
                                    <div className="text-slate-700">
                                        Hook: <span className="italic">"{analysis.copy_analysis.hook}"</span>
                                    </div>
                                    <div className="text-slate-700">
                                        Angle: {analysis.copy_analysis.messaging_angle}
                                    </div>
                                    <div className="text-slate-700">
                                        Tone: {analysis.copy_analysis.emotional_tone}
                                    </div>
                                </div>
                            )}
                            {analysis.visual_analysis && (
                                <div>
                                    <div className="font-medium text-slate-600">Visual</div>
                                    <div className="text-slate-700">Style: {analysis.visual_analysis.style}</div>
                                    <div className="text-slate-700">
                                        {analysis.visual_analysis.description}
                                    </div>
                                </div>
                            )}
                            {analysis.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1 pt-1">
                                    {analysis.tags.map((t) => (
                                        <Badge key={t} variant="outline" className="text-xs">
                                            {t}
                                        </Badge>
                                    ))}
                                </div>
                            )}
                        </div>
                    ) : (
                        <p className="text-xs text-slate-400">No analysis yet.</p>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}