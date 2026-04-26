"use client";

import { useState } from "react";
import { Brand, api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface BrandPanelProps {
    brand: Brand | null;
    onBrandCreated: (brand: Brand) => void;
}

export function BrandPanel({ brand, onBrandCreated }: BrandPanelProps) {
    const [name, setName] = useState("Ridge");
    const [url, setUrl] = useState("https://ridge.com");
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleCreate = async () => {
        setCreating(true);
        setError(null);
        try {
            const b = await api.createBrand(name, url);
            onBrandCreated(b);
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setCreating(false);
        }
    };

    if (!brand) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Create brand</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="brand-name">Brand name</Label>
                        <Input
                            id="brand-name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Ridge"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="brand-url">Website URL</Label>
                        <Input
                            id="brand-url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://ridge.com"
                        />
                    </div>
                    <Button onClick={handleCreate} disabled={creating || !name || !url}>
                        {creating ? "Scraping + profiling…" : "Create brand"}
                    </Button>
                    {error && <p className="text-sm text-red-600">{error}</p>}
                </CardContent>
            </Card>
        );
    }

    const profile = brand.profile;

    return (
        <Card>
            <CardHeader>
                <div className="flex items-baseline justify-between">
                    <div>
                        <CardTitle>{brand.name}</CardTitle>
                        <a
                            href={brand.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-blue-600 hover:underline"
                        >
                            {brand.url}
                        </a>
                    </div>
                    <span className="text-xs text-slate-500">Brand #{brand.id}</span>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {!profile ? (
                    <p className="text-sm text-slate-500">No profile yet.</p>
                ) : (
                    <>
                        <ProfileRow label="Product category" value={profile.product_category} />
                        <ProfileRow label="Positioning" value={profile.positioning} />
                        <ProfileRow label="Tone of voice" value={profile.tone_of_voice} />
                        <ProfileRow label="Target audience" value={profile.target_audience} />

                        <div>
                            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                                Value propositions
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {profile.value_propositions.map((vp, i) => (
                                    <Badge key={i} variant="secondary">
                                        {vp}
                                    </Badge>
                                ))}
                            </div>
                        </div>

                        {profile.notable_claims.length > 0 && (
                            <div>
                                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                                    Notable claims
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {profile.notable_claims.map((c, i) => (
                                        <Badge key={i} variant="outline">
                                            {c}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    );
}

function ProfileRow({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                {label}
            </div>
            <div className="text-sm text-slate-800">{value}</div>
        </div>
    );
}