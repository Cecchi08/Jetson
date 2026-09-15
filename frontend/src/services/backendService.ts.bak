import type { Message } from '../types';
import { authService } from './authService';

export interface AssistantService {
  sendMessage(messages: Message[]): Promise<string>;
}

export const backendService: AssistantService = {
  async sendMessage(messages) {
    try {
      const history = messages.slice(0, -1).map(({ role, content }) => ({ role, content }));
      const message = messages[messages.length - 1]?.content ?? '';
      const token = authService.getToken();

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message, history }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'No se pudo obtener una respuesta del asistente.' }));
        throw new Error(errorData?.error || 'No se pudo obtener una respuesta del asistente.');
      }

      const data = await response.json() as { response?: unknown };
      if (typeof data?.response !== 'string') throw new Error('Respuesta inesperada del servidor.');
      return data.response;
    } catch (error) {
      if (error instanceof Error) throw error;
      throw new Error('No se pudo conectar con el asistente. Verificá que el backend esté ejecutándose.');
    }
  },
};
