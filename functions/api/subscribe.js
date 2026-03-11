export async function onRequestPost(context) {
  const { request, env } = context;

  // CORS
  const headers = {
    "Access-Control-Allow-Origin": "https://maaker.ai",
    "Content-Type": "application/json",
  };

  try {
    const { email } = await request.json();

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return new Response(JSON.stringify({ error: "邮箱格式不正确" }), {
        status: 400,
        headers,
      });
    }

    const normalizedEmail = email.toLowerCase().trim();

    // Check if already subscribed
    const existing = await env.SUBSCRIBERS.get(normalizedEmail);
    if (existing) {
      return new Response(
        JSON.stringify({ ok: true, message: "你已经订阅过了" }),
        { status: 200, headers }
      );
    }

    // Store subscriber (单 key 用于去重)
    await env.SUBSCRIBERS.put(
      normalizedEmail,
      JSON.stringify({
        email: normalizedEmail,
        subscribedAt: new Date().toISOString(),
      })
    );

    // 同步更新 email_list (供 dispatch 批量读取)
    const raw = await env.SUBSCRIBERS.get("email_list");
    const emailList = raw ? JSON.parse(raw) : [];
    if (!emailList.includes(normalizedEmail)) {
      emailList.push(normalizedEmail);
      await env.SUBSCRIBERS.put("email_list", JSON.stringify(emailList));
    }

    // 发送欢迎邮件（不阻塞响应）
    context.waitUntil(
      fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.RESEND_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          from: "AI 日报 <ai-daily@maaker.ai>",
          to: normalizedEmail,
          subject: "订阅成功 — AI 日报",
          html: `<div style="max-width:480px;margin:0 auto;font-family:-apple-system,sans-serif;color:#333;">
  <h2 style="color:#0D9488;">订阅成功！</h2>
  <p>你好，感谢订阅 AI 日报 👋</p>
  <p>从明天起，你将在<strong>每天早上 8:00</strong> 收到一封邮件，内容包括：</p>
  <ul style="line-height:1.8;">
    <li>AI 工具与应用的最新动态</li>
    <li>值得关注的开源项目</li>
    <li>大模型和 Agent 的前沿进展</li>
    <li>开发者生态的有趣资讯</li>
  </ul>
  <p>所有内容由 AI 从 X/Twitter 上的科技大 V 动态中自动整理，中文呈现，帮你高效掌握 AI 领域最新信息。</p>
  <p style="color:#999;font-size:13px;margin-top:24px;">— 小马哥 / <a href="https://maaker.ai" style="color:#0D9488;">Maaker.AI</a></p>
</div>`,
        }),
      }).catch(() => {})
    );

    return new Response(
      JSON.stringify({ ok: true, message: "订阅成功！欢迎邮件已发送，请查收" }),
      { status: 200, headers }
    );
  } catch (e) {
    return new Response(JSON.stringify({ error: "服务器错误" }), {
      status: 500,
      headers,
    });
  }
}

export async function onRequestOptions() {
  return new Response(null, {
    headers: {
      "Access-Control-Allow-Origin": "https://maaker.ai",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}
