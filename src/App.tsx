import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatHeader } from './components/ChatHeader';
import { MessageList } from './components/MessageList';
import { ChatInput } from './components/ChatInput';
import { localAssistantService } from './services/assistantService';
import { useChat } from './hooks/useChat';
import type { Assistant, User } from './types';

const assistant: Assistant = { name: 'Orion', status: 'En línea', description: 'Tu espacio para pensar mejor' };
const user: User = { id: 'demo-user', name: 'Alex Morgan', email: 'alex@orion.local', initials: 'AM' };

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { conversations, activeConversation, isGenerating, streamingMessage, selectConversation, createConversation, sendMessage } = useChat(localAssistantService);
  if (!activeConversation) return null;
  return <div className="app-shell"><Sidebar conversations={conversations} activeId={activeConversation.id} user={user} isOpen={sidebarOpen} onSelect={(id) => { selectConversation(id); setSidebarOpen(false); }} onNewChat={() => { createConversation(); setSidebarOpen(false); }} onClose={() => setSidebarOpen(false)} /><main className="chat-panel"><ChatHeader assistant={assistant} onMenu={() => setSidebarOpen(true)} /><section className="chat-body"><div className="welcome"><span className="welcome__eyebrow"><span className="signal" /> ESPACIO DE TRABAJO PERSONAL</span><h2>¿Qué tienes<br /><em>en mente?</em></h2><p>{assistant.description}. Conversa, organiza y transforma tus ideas en algo concreto.</p></div><MessageList messages={activeConversation.messages} streamingMessage={streamingMessage} isGenerating={isGenerating} /></section><ChatInput disabled={isGenerating} onSend={sendMessage} /></main>{sidebarOpen && <button className="scrim" onClick={() => setSidebarOpen(false)} aria-label="Cerrar menú" />}</div>;
}

export default App;
