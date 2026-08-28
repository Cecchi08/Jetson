import type { Message } from '../types';

interface OpenClawChoice {
  message?: {
    content?: unknown;
  };
}

interface OpenClawResponse {
  choices?: OpenClawChoice[];
}

export interface AssistantService {
  sendMessage(messages: Message[]): Promise<string>;
}

const endpoint = import.meta.env.VITE_OPENCLAW_URL?.replace(/\/$/, '');
const token = import.meta.env.VITE_OPENCLAW_TOKEN;
const model = import.meta.env.VITE_OPENCLAW_MODEL;

function isOpenClawResponse(value: unknown): value is OpenClawResponse {
  if (!value || typeof value !== 'object') return false;
  const response = value as { choices?: unknown };
  return Array.isArray(response.choices);
}

function getErrorMessage(error: unknown): string {
  if (error instanceof TypeError) return 'No se pudo conectar con el asistente. Verificá que OpenClaw esté ejecutándose.';
  if (error instanceof Error && error.message === 'OPENCLAW_HTTP_ERROR') return 'OpenClaw rechazó la solicitud. Verificá la URL y el token configurados.';
  if (error instanceof Error && error.message === 'OPENCLAW_CONFIG_ERROR') return 'Falta configurar la URL, el token o el modelo de OpenClaw.';
  return 'No se pudo obtener una respuesta del asistente. Intentá nuevamente.';
}

export const openClawService: AssistantService = {
  async sendMessage(messages) {
    try {
      if (!endpoint || !token || !model) throw new Error('OPENCLAW_CONFIG_ERROR');
      const response = await fetch(`${endpoint}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ model, messages: messages.map(({ role, content }) => ({ role, content })) }),
      });
      if (!response.ok) throw new Error('OPENCLAW_HTTP_ERROR');
      const data: unknown = await response.json();
      if (!isOpenClawResponse(data) || typeof data.choices?.[0]?.message?.content !== 'string') throw new Error('OPENCLAW_RESPONSE_ERROR');
      return data.choices[0].message.content;
    } catch (error) {
      if (error instanceof Error && error.message === 'OPENCLAW_CONFIG_ERROR') {
        throw new Error(getErrorMessage(error));
      }
      throw new Error(getErrorMessage(error));
    }
  },
};