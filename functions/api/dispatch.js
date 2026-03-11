export async function onRequestPost(context) {
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
    const { subject, htmlContent } = await request.json();

    if (!subject || !htmlContent) {
      return new Response(
        JSON.stringify({ error: "Missing subject or htmlContent" }),
        { status: 400, headers }
      );
    }

    // 从 KV 读取订阅者列表
    const raw = await env.SUBSCRIBERS.get("email_list");
    const emails = raw ? JSON.parse(raw) : [];

    if (emails.length === 0) {
      return new Response(
        JSON.stringify({ ok: true, sent: 0, failed: 0, message: "No subscribers" }),
        { status: 200, headers }
      );
    }

    // 批量发送邮件
    let sent = 0;
    let failed = 0;
    const errors = [];

    // Resend 免费版不支持 batch API，逐个发送
    // 并发控制：每批最多 10 个
    const batchSize = 10;
    for (let i = 0; i < emails.length; i += batchSize) {
      const batch = emails.slice(i, i + batchSize);
      const results = await Promise.allSettled(
        batch.map(async (email) => {
          const res = await fetch("https://api.resend.com/emails", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${env.RESEND_API_KEY}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              from: "AI 日报 <ai-daily@maaker.ai>",
              to: email,
              subject,
              html: htmlContent,
            }),
          });

          if (!res.ok) {
            const body = await res.text();
            throw new Error(`${res.status}: ${body}`);
          }
          return res.json();
        })
      );

      for (const result of results) {
        if (result.status === "fulfilled") {
          sent++;
        } else {
          failed++;
          errors.push(result.reason?.message || "Unknown error");
        }
      }
    }

    return new Response(
      JSON.stringify({
        ok: true,
        total: emails.length,
        sent,
        failed,
        errors: errors.length > 0 ? errors.slice(0, 10) : undefined,
      }),
      { status: 200, headers }
    );
  } catch (e) {
    return new Response(
      JSON.stringify({ error: "Internal server error", detail: e.message }),
      { status: 500, headers }
    );
  }
}
