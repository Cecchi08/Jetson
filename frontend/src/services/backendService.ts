import type { Message } from '../types';

export interface AssistantService {
  sendMessage(messages: Message[]): Promise<string>;
}

export const backendService: AssistantService = {
  async sendMessage(messages) {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: messages.map(({ role, content }) => ({ role, content })) }),
      });
      if (!response.ok) {
        if (response.status === 503) throw new Error('El asistente no está disponible. Verificá que OpenClaw esté ejecutándose.');
        if (response.status === 400) throw new Error('Solicitud inválida. Verificá los datos enviados.');
        throw new Error('No se pudo obtener una respuesta del asistente.');
      }
      const data = await response.json() as { message?: { content?: unknown } };
      if (typeof data?.message?.content !== 'string') throw new Error('Respuesta inesperada del servidor.');
      return data.message.content;
    } catch (error) {
      if (error instanceof Error) throw error;
      throw new Error('No se pudo conectar con el asistente. Verificá que el backend esté ejecutándose.');
    }
  },
};
