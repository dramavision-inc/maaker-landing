export async function onRequestGet(context) {
  const { env } = context;
  const headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "public, max-age=3600",
  };

  try {
    const raw = await env.SUBSCRIBERS.get("email_list");
    const emails = raw ? JSON.parse(raw) : [];
    return new Response(JSON.stringify({ count: emails.length }), {
      status: 200,
      headers,
    });
  } catch {
    return new Response(JSON.stringify({ count: 0 }), {
      status: 200,
      headers,
    });
  }
}
