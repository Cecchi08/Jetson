const N8N_WEBHOOK_URL =
  process.env.N8N_WEBHOOK_URL ||
  'http://host.docker.internal:5678/webhook/orion-ai';

const N8N_TIMEOUT = Number(process.env.N8N_TIMEOUT || 120000);

export async function callN8n({ message, mode = 'chat' }) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), N8N_TIMEOUT);

  try {
    const response = await fetch(N8N_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        mode,
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

    if (payload === null || payload === undefined) {
      throw new Error('Respuesta vacía de n8n');
    }

    // CHAT / WEB / ASK
    if (mode === 'chat' || mode === 'web' || mode === 'ask') {
      const result = Array.isArray(payload)
        ? payload[0]?.response
        : payload?.response;

      if (typeof result !== 'string' || !result.trim()) {
        throw new Error('Respuesta inválida de n8n');
      }

      return result.trim();
    }

    // PDF mantiene respuesta estructurada
    return payload;

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
