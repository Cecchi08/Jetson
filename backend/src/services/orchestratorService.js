const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://orchestrator:9080';
const ORCHESTRATOR_TIMEOUT = Number(process.env.ORCHESTRATOR_TIMEOUT || 120000);

export async function callOrchestrator({ message, history = [] }) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ORCHESTRATOR_TIMEOUT);

  try {
    const response = await fetch(`${ORCHESTRATOR_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
      signal: controller.signal,
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(payload?.error || `Orquestador respondió con error ${response.status}`);
    }

    if (typeof payload?.response !== 'string' || !payload.response.trim()) {
      throw new Error('La respuesta del orquestador es inválida');
    }

    return payload.response;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw Object.assign(new Error('El orquestador tardó demasiado en responder'), { name: 'TimeoutError' });
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
