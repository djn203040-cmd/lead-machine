"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function SignOutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function onClick() {
    setLoading(true);
    await createClient().auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="text-sm text-gray-500 underline-offset-2 hover:text-gray-900 hover:underline disabled:opacity-50"
    >
      {loading ? "Logger ud…" : "Log ud"}
    </button>
  );
}
