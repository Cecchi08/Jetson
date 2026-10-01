import { useEffect, useState } from 'react';
import type { Conversation, Message } from '../types';
import type { AssistantService } from '../services/backendService';

const createId = () =>
  `${Date.now()}-${Math.random().toString(36).slice(2)}`;

function createDraftConversation(): Conversation {
  return {
    id: createId(),
    title: 'Nueva conversación',
    preview: 'Comienza una nueva idea',
    updatedAt: 'Ahora',
    messages: [],
  };
}

export function useChat(
  service: AssistantService,
  isAuthenticated: boolean
) {
  const [conversations, setConversations] =
    useState<Conversation[]>([]);

  const [activeId, setActiveId] =
    useState<string>('');

  const [isGenerating, setIsGenerating] =
    useState(false);

  const activeConversation =
    conversations.find(
      (conversation) => conversation.id === activeId
    );

  useEffect(() => {
    if (!isAuthenticated) {
      setConversations([]);
      setActiveId('');
      return;
    }

    let cancelled = false;

    async function load() {
      try {
        const stored = await service.getConversations();

        if (cancelled) return;

        if (stored.length === 0) {
          const draft = createDraftConversation();

          setConversations([draft]);
          setActiveId(draft.id);
          return;
        }

        setConversations(stored);
        setActiveId(stored[0].id);

        const messages =
          await service.getMessages(stored[0].id);

        if (cancelled) return;

        setConversations((current) =>
          current.map((conversation) =>
            conversation.id === stored[0].id
              ? { ...conversation, messages }
              : conversation
          )
        );
      } catch (error) {
        console.error(
          'Error cargando conversaciones:',
          error
        );

        if (!cancelled) {
          const draft = createDraftConversation();
          setConversations([draft]);
          setActiveId(draft.id);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, service]);

  const selectConversation = async (id: string) => {
    if (isGenerating || id === activeId) return;

    setActiveId(id);

    const conversation =
      conversations.find((item) => item.id === id);

    if (!conversation) return;

    // Un chat nuevo todavía no existe en PostgreSQL.
    if (
      conversation.messages.length === 0 &&
      conversation.title === 'Nueva conversación'
    ) {
      return;
    }

    try {
      const messages = await service.getMessages(id);

      setConversations((current) =>
        current.map((item) =>
          item.id === id
            ? { ...item, messages }
            : item
        )
      );
    } catch (error) {
      console.error(
        'Error cargando mensajes:',
        error
      );
    }
  };

  const createConversation = () => {
    if (isGenerating) return;

    const conversation =
      createDraftConversation();

    setConversations((current) => [
      conversation,
      ...current,
    ]);

    setActiveId(conversation.id);
  };

  const sendMessage = async (
    content: string,
    file?: File
  ) => {
    if (
      isGenerating ||
      !activeConversation ||
      !content.trim()
    ) {
      return;
    }

    const sessionId = activeConversation.id;

    const userMessage: Message = {
      id: createId(),
      role: 'user',
      content: content.trim(),
      createdAt: new Date().toISOString(),
    };

    const nextMessages = [
      ...activeConversation.messages,
      userMessage,
    ];

    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === sessionId
          ? {
              ...conversation,
              title:
                conversation.messages.length > 0
                  ? conversation.title
                  : content.trim().slice(0, 40),
              preview: content.trim(),
              updatedAt: 'Ahora',
              messages: nextMessages,
            }
          : conversation
      )
    );

    setIsGenerating(true);

    try {
      const response = await service.sendMessage(
        nextMessages,
        file,
        sessionId
      );

      const assistantMessage: Message = {
        id: createId(),
        role: 'assistant',
        content: response,
        createdAt: new Date().toISOString(),
      };

      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === sessionId
            ? {
                ...conversation,
                preview: response,
                updatedAt: 'Ahora',
                messages: [
                  ...nextMessages,
                  assistantMessage,
                ],
              }
            : conversation
        )
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'No se pudo obtener una respuesta.';

      const errorMessage: Message = {
        id: createId(),
        role: 'assistant',
        content: message,
        createdAt: new Date().toISOString(),
      };

      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === sessionId
            ? {
                ...conversation,
                messages: [
                  ...nextMessages,
                  errorMessage,
                ],
              }
            : conversation
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return {
    conversations,
    activeConversation,
    isGenerating,
    selectConversation,
    createConversation,
    sendMessage,
  };
}
