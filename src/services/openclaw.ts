import type { Message } from '../types';

interface OpenClawChoice {
  message?: {
    content?: unknown;
  };
}

interface OpenClawResponse {
  choices?: OpenClawChoice[];
}

interface OpenClawErrorResponse {
  error?: {
    message?: unknown;
    type?: unknown;
    code?: unknown;
  };
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

function getServerErrorMessage(value: unknown): string | null {
  if (!value || typeof value !== 'object') return null;

  const response = value as OpenClawErrorResponse;

  if (
    response.error &&
    typeof response.error === 'object' &&
    typeof response.error.message === 'string'
  ) {
    return response.error.message;
  }

  return null;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    if (error.message === 'OPENCLAW_CONFIG_ERROR') {
      return 'Falta configurar la URL, el token o el modelo de OpenClaw.';
    }

    if (error.message === 'OPENCLAW_NETWORK_ERROR') {
      return 'No se pudo conectar con OpenClaw. Verificá que el gateway esté funcionando.';
    }

    if (error.message === 'OPENCLAW_RESPONSE_ERROR') {
      return 'OpenClaw respondió con un formato inesperado.';
    }
  }

  return 'No se pudo obtener una respuesta del asistente. Intentá nuevamente.';
}

export const openClawService: AssistantService = {
  async sendMessage(messages) {
    console.log('[OpenClaw] configuración:', {
      endpoint,
      tokenPresent: Boolean(token),
      model,
    });

    try {
      if (!endpoint || !token || !model) {
        console.error('[OpenClaw] configuración incompleta', {
          endpoint,
          tokenPresent: Boolean(token),
          model,
        });

        throw new Error('OPENCLAW_CONFIG_ERROR');
      }

      const requestBody = {
        model,
        messages: messages.map(({ role, content }) => ({
          role,
          content,
        })),
      };

      console.log('[OpenClaw] enviando petición:', {
        url: `${endpoint}/v1/chat/completions`,
        model,
        messageCount: requestBody.messages.length,
      });

      const response = await fetch(`${endpoint}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(requestBody),
      });

      console.log('[OpenClaw] respuesta HTTP:', {
        status: response.status,
        ok: response.ok,
      });

      const responseText = await response.text();

      console.log('[OpenClaw] respuesta del servidor:', responseText);

      let data: unknown = null;

      try {
        data = JSON.parse(responseText);
      } catch {
        console.warn('[OpenClaw] la respuesta no es JSON válido');
      }

      if (!response.ok) {
        const serverMessage = getServerErrorMessage(data);

        console.error('[OpenClaw] ERROR REAL DEL SERVIDOR:', {
          status: response.status,
          message: serverMessage,
          body: data,
        });

        throw new Error(
          serverMessage
            ? `OPENCLAW_SERVER_ERROR: ${serverMessage}`
            : 'OPENCLAW_HTTP_ERROR',
        );
      }

      if (!isOpenClawResponse(data)) {
        console.error('[OpenClaw] respuesta inesperada:', data);
        throw new Error('OPENCLAW_RESPONSE_ERROR');
      }

      const content = data.choices?.[0]?.message?.content;

      if (typeof content !== 'string') {
        console.error('[OpenClaw] contenido inesperado:', data);
        throw new Error('OPENCLAW_RESPONSE_ERROR');
      }

      console.log('[OpenClaw] respuesta recibida correctamente');

      return content;
    } catch (error) {
      console.error('[OpenClaw] error durante la solicitud:', error);

      if (
        error instanceof TypeError &&
        error.message === 'Failed to fetch'
      ) {
        throw new Error(getErrorMessage(new Error('OPENCLAW_NETWORK_ERROR')));
      }

      if (
        error instanceof Error &&
        error.message.startsWith('OPENCLAW_SERVER_ERROR:')
      ) {
        const realMessage = error.message.replace(
          'OPENCLAW_SERVER_ERROR: ',
          '',
        );

        throw new Error(`OpenClaw: ${realMessage}`);
      }

      throw new Error(getErrorMessage(error));
    }
  },
};