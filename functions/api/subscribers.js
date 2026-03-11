export async function onRequestGet(context) {
  const { request, env } = context;

  const headers = { "Content-Type": "application/json" };

  // Bearer Token 鉴权
  const authHeader = request.headers.get("Authorization");
  if (!authHeader || authHeader !== `Bearer ${env.DISPATCH_SECRET}`) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers,
    });
  }

  try {
    const raw = await env.SUBSCRIBERS.get("email_list");
    const emails = raw ? JSON.parse(raw) : [];

    return new Response(
      JSON.stringify({ ok: true, count: emails.length }),
      { status: 200, headers }
    );
  } catch (e) {
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500, headers }
    );
  }
}
