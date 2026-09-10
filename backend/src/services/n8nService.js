const N8N_WEBHOOK_URL =
  process.env.N8N_WEBHOOK_URL ||
  'http://host.docker.internal:5678/webhook/orion-ai';

const N8N_TIMEOUT = Number(process.env.N8N_TIMEOUT || 120000);

export async function callN8n({ message }) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), N8N_TIMEOUT);

  try {
    const response = await fetch(N8N_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        mode: 'chat',
        message,
      }),
      signal: controller.signal,
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        payload?.error ||
        `n8n respondió con error HTTP ${response.status}`
      );
    }

    const result = Array.isArray(payload)
      ? payload[0]?.response
      : payload?.response;

    if (typeof result !== 'string' || !result.trim()) {
      throw new Error('Respuesta inválida de n8n');
    }

    return result;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw Object.assign(
        new Error('n8n tardó demasiado en responder'),
        { name: 'TimeoutError' }
      );
    }

    throw error;
  } finally {
    clearTimeout(timer);
  }
}
