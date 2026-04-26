// Typed API client for the Brandora backend.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types — mirror the SQLModel/Pydantic schemas on the backend
// ---------------------------------------------------------------------------

export interface BrandProfile {
    product_category: string;
    positioning: string;
    tone_of_voice: string;
    target_audience: string;
    value_propositions: string[];
    notable_claims: string[];
}

export interface Brand {
    id: number;
    name: string;
    url: string;
    profile: BrandProfile | null;
    created_at: string;
}

export interface Competitor {
    id: number;
    brand_id: number;
    name: string;
}

export interface Ad {
    id: number;
    competitor_id: number;
    meta_ad_id: string | null;
    format: string;
    creative_urls: string[];
    local_image_paths: string[];
    primary_text: string | null;
    headline: string | null;
    cta_text: string | null;
    page_name: string | null;
    scraped_at: string;
}

export interface CopyAnalysis {
    hook: string;
    cta: string | null;
    messaging_angle: string;
    emotional_tone: string;
    key_phrases: string[];
}

export interface VisualAnalysis {
    style: string;
    has_people: boolean;
    has_text_overlay: boolean;
    ugc_looking: boolean;
    product_visibility: string;
    dominant_colors: string[];
    description: string;
}

export interface AdAnalysis {
    id: number;
    ad_id: number;
    copy_analysis: CopyAnalysis | null;
    visual_analysis: VisualAnalysis | null;
    tags: string[];
    created_at: string;
}

export interface AdIdeaPayload {
    hook: string;
    creative_concept: string;
    format: string;
    brand_fit_rationale: string;
    inspired_by_ad_ids: number[];
}

export interface AdIdea {
    id: number;
    brand_id: number;
    payload: AdIdeaPayload;
    created_at: string;
}

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers: {
            "Content-Type": "application/json",
            ...(init?.headers || {}),
        },
    });
    if (!res.ok) {
        const body = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${body}`);
    }
    return res.json();
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export const api = {
    // Brand
    listBrands: () => request<Brand[]>("/brands"),
    createBrand: (name: string, url: string) =>
        request<Brand>("/brands", {
            method: "POST",
            body: JSON.stringify({ name, url }),
        }),
    getBrand: (id: number) => request<Brand>(`/brands/${id}`),

    // Competitor
    createCompetitor: (brand_id: number, name: string, facebook_url: string) =>
        request<{ competitor_id: number; competitor_name: string; ads_scraped: number; ad_ids: number[] }>(
            "/competitors",
            { method: "POST", body: JSON.stringify({ brand_id, name, facebook_url }) }
        ),
    listCompetitors: (brand_id?: number) => {
        const qs = brand_id !== undefined ? `?brand_id=${brand_id}` : "";
        return request<Competitor[]>(`/competitors${qs}`);
    },
    listCompetitorAds: (competitor_id: number) =>
        request<Ad[]>(`/competitors/${competitor_id}/ads`),



    // Analysis
    analyzeAllForCompetitor: (competitor_id: number) =>
        request<{ analyzed: number; ad_ids: number[] }>(
            `/ads/analyze-all/${competitor_id}`,
            { method: "POST" }
        ),
    getAdAnalysis: (ad_id: number) => request<AdAnalysis>(`/ads/${ad_id}/analysis`),

    // Ideas
    generateIdeas: (brand_id: number) =>
        request<AdIdea[]>(`/brands/${brand_id}/generate-ideas`, { method: "POST" }),
    listIdeas: (brand_id: number) => request<AdIdea[]>(`/brands/${brand_id}/ideas`),

    // Helper for cached images
    imageUrl: (localPath: string) => {
        // local paths look like "cache\\images\\986757004022549\\0.jpg" on Windows
        // or "cache/images/986757004022549/0.jpg" on Unix — normalize both
        const rel = localPath.replace(/\\/g, "/").replace(/^cache\/images\//, "");
        return `${API_BASE}/images/${rel}`;
    },
};