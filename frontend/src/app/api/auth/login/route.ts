import { NextRequest, NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

type LoginRequestBody =
  | {
      type: "oauth";
      provider: "google" | "azure";
      redirectTo?: string;
    }
  | {
      type: "password";
      email: string;
      password: string;
    }
  | {
      type: "magic_link";
      email: string;
      redirectTo?: string;
    };

function getCallbackUrl(request: NextRequest, redirectTo?: string): string {
  const callback = new URL("/auth/callback", request.url);
  if (redirectTo) {
    callback.searchParams.set("next", redirectTo);
  }
  return callback.toString();
}

export async function POST(request: NextRequest) {
  const supabase = createSupabaseServerClient();
  const body = (await request.json()) as LoginRequestBody;

  if (body.type === "oauth") {
    const callbackUrl = getCallbackUrl(request, body.redirectTo);
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: body.provider,
      options: { redirectTo: callbackUrl },
    });

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json({ url: data.url }, { status: 200 });
  }

  if (body.type === "password") {
    const { error } = await supabase.auth.signInWithPassword({
      email: body.email,
      password: body.password,
    });

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json({ status: "ok" }, { status: 200 });
  }

  const callbackUrl = getCallbackUrl(request, body.redirectTo);
  const { error } = await supabase.auth.signInWithOtp({
    email: body.email,
    options: { emailRedirectTo: callbackUrl },
  });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }

  return NextResponse.json({ status: "ok" }, { status: 200 });
}
