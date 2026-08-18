// Anonymous Supabase client for the public letter surfaces (redirect, landing,
// opt-out). No cookies, no session — everything goes through the three
// SECURITY DEFINER RPCs from migration 0012, so anon can never read the tables.

import "server-only";

import { createClient } from "@supabase/supabase-js";
import type { Database } from "@/lib/database.types";

export function publicClient() {
  return createClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { persistSession: false, autoRefreshToken: false } },
  );
}

export type LandingPayload = {
  slug: string;
  company_name: string;
  first_name: string | null;
  arm: string;
  landing_video_url: string | null;
  landing_headline: string | null;
  observation_text: string | null;
  focus_text: string | null;
  opted_out: boolean;
  branchekode: string | null;
};

/** Slugs are lower-case a–z0–9 (see slugify). Anything else is not ours. */
export const SLUG_RE = /^[a-z0-9]{2,32}$/;

/** Loom / YouTube share links → embeddable iframe src. Unknown hosts: null. */
export function embedUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    if (u.hostname.endsWith("loom.com")) {
      const id = u.pathname.split("/").filter(Boolean).pop();
      return id ? `https://www.loom.com/embed/${id}` : null;
    }
    if (u.hostname === "youtu.be") return `https://www.youtube-nocookie.com/embed/${u.pathname.slice(1)}`;
    if (u.hostname.endsWith("youtube.com")) {
      const id = u.searchParams.get("v") ?? u.pathname.split("/").filter(Boolean).pop();
      return id ? `https://www.youtube-nocookie.com/embed/${id}` : null;
    }
    if (u.hostname.endsWith("vimeo.com")) {
      const id = u.pathname.split("/").filter(Boolean).pop();
      return id ? `https://player.vimeo.com/video/${id}` : null;
    }
  } catch {
    return null;
  }
  return null;
}
