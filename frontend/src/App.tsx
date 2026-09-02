import { useState, useEffect } from 'react';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { Sidebar } from './components/Sidebar';
import { ChatHeader } from './components/ChatHeader';
import { MessageList } from './components/MessageList';
import { ChatInput } from './components/ChatInput';
import { backendService } from './services/backendService';
import { authService } from './services/authService';
import { useChat } from './hooks/useChat';
import type { Assistant, User } from './types';

const assistant: Assistant = { name: 'Orion', status: 'En línea', description: 'Tu espacio para pensar mejor' };

type AuthScreen = 'login' | 'register';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(authService.isAuthenticated());
  const [authScreen, setAuthScreen] = useState<AuthScreen>('login');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(authService.getUser());
  
  const { conversations, activeConversation, isGenerating, selectConversation, createConversation, sendMessage } = useChat(backendService);

  useEffect(() => {
    if (!isAuthenticated) {
      setCurrentUser(null);
    }
  }, [isAuthenticated]);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    setCurrentUser(authService.getUser());
  };

  const handleRegisterSuccess = () => {
    setIsAuthenticated(true);
    setCurrentUser(authService.getUser());
  };

  const handleLogout = () => {
    authService.logout();
    setIsAuthenticated(false);
    setCurrentUser(null);
    setAuthScreen('login');
  };

  if (!isAuthenticated) {
    if (authScreen === 'login') {
      return (
        <Login
          onSwitchToRegister={() => setAuthScreen('register')}
          onLoginSuccess={handleLoginSuccess}
        />
      );
    }
    return (
      <Register
        onSwitchToLogin={() => setAuthScreen('login')}
        onRegisterSuccess={handleRegisterSuccess}
      />
    );
  }

  if (!activeConversation || !currentUser) return null;

  return (
    <div className="app-shell">
      <Sidebar
        conversations={conversations}
        activeId={activeConversation.id}
        user={currentUser}
        isOpen={sidebarOpen}
        onSelect={(id) => {
          selectConversation(id);
          setSidebarOpen(false);
        }}
        onNewChat={() => {
          createConversation();
          setSidebarOpen(false);
        }}
        onLogout={handleLogout}
        onClose={() => setSidebarOpen(false)}
      />
      <main className="chat-panel">
        <ChatHeader assistant={assistant} onMenu={() => setSidebarOpen(true)} />
        <section className="chat-body">
          <div className="welcome">
            <span className="welcome__eyebrow">
              <span className="signal" /> ESPACIO DE TRABAJO PERSONAL
            </span>
            <h2>
              ¿Qué tienes<br />
              <em>en mente?</em>
            </h2>
            <p>{assistant.description}. Conversa, organiza y transforma tus ideas en algo concreto.</p>
          </div>
          <MessageList messages={activeConversation.messages} streamingMessage={null} isGenerating={isGenerating} />
        </section>
        <ChatInput disabled={isGenerating} onSend={sendMessage} />
      </main>
      {sidebarOpen && <button className="scrim" onClick={() => setSidebarOpen(false)} aria-label="Cerrar menú" />}
    </div>
  );
}

export default App;
