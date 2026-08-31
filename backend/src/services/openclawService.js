export async function sendToOpenClaw(messages) {
  const url = process.env.OPENCLAW_URL;
  const token = process.env.OPENCLAW_TOKEN;
  const model = process.env.OPENCLAW_MODEL;

  if (!url || !token || !model) {
    throw new Error('OPENCLAW: Variables de entorno no configuradas');
  }

  try {
    const response = await fetch(`${url}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        model,
        messages,
      }),
    });

    if (!response.ok) {
      throw new Error(`OPENCLAW: HTTP ${response.status}`);
    }

    const data = await response.json();

    if (!data.choices || !data.choices[0] || typeof data.choices[0].message?.content !== 'string') {
      throw new Error('OPENCLAW: Respuesta inesperada');
    }

    return data.choices[0].message.content;
  } catch (error) {
    throw new Error(`OPENCLAW: ${error.message}`);
  }
}
