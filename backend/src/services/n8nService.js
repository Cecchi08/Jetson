const N8N_WEBHOOK_URL =
  'http://host.docker.internal:5678/webhook-test/archivo/upload';

const N8N_TIMEOUT = Number(
  process.env.N8N_TIMEOUT || 120000
);

export async function callN8n({
  id_user,
  session_id,
  message,
  file,
}) {
  const controller = new AbortController();

  const timer = setTimeout(
    () => controller.abort(),
    N8N_TIMEOUT
  );

  try {
    const formData = new FormData();

    formData.append('id_user', id_user);
    formData.append('session_id', session_id);
    formData.append('message', message);

    if (file?.buffer) {
      const blob = new Blob([file.buffer], {
        type: file.mimetype || 'application/octet-stream',
      });

      formData.append(
        'file',
        blob,
        file.originalname || 'archivo'
      );
    }

    const response = await fetch(N8N_WEBHOOK_URL, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        payload?.error ||
        `n8n respondió con HTTP ${response.status}`
      );
    }

    if (payload === null || payload === undefined) {
      throw new Error('Respuesta vacía de n8n');
    }

    const data =
      Array.isArray(payload) && payload.length === 1
        ? payload[0]
        : payload;

    const result =
      data?.response ??
      data?.mensaje ??
      data?.message;

    if (typeof result === 'string' && result.trim()) {
      return result.trim();
    }

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
