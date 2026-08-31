export type MessageRole = 'user' | 'assistant';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

export interface Conversation {
  id: string;
  title: string;
  preview: string;
  updatedAt: string;
  messages: Message[];
}

export interface User {
  id: number;
  username: string;
  name?: string;
  email?: string;
  initials?: string;
}

export interface Assistant {
  name: string;
  status: string;
  description: string;
}
