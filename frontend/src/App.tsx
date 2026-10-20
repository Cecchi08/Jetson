import { useState, useEffect, useRef } from 'react';
import { ArrowDown } from 'lucide-react';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { Sidebar } from './components/Sidebar';
import { ChatHeader } from './components/ChatHeader';
import { MessageList } from './components/MessageList';
import { ChatInput } from './components/ChatInput';
import { ShippingCalculatorPage } from './components/ShippingCalculatorPage';
import { backendService } from './services/backendService';
import { authService } from './services/authService';
import { useChat } from './hooks/useChat';
import type { Assistant, User } from './types';
import type { AppView } from './views';
import './navigation.css';

const assistant: Assistant = {
  name: 'Orion',
  status: 'En línea',
  description: 'Tu espacio para pensar mejor'
};

type AuthScreen = 'login' | 'register';

function App() {
  const [activeView, setActiveView] = useState<AppView>('agent');
  const [isAuthenticated, setIsAuthenticated] = useState(
    authService.isAuthenticated()
  );
  const [authScreen, setAuthScreen] = useState<AuthScreen>('login');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(
    authService.getUser()
  );
  const [showScrollButton, setShowScrollButton] = useState(false);
  const chatBodyRef = useRef<HTMLElement>(null);

  const {
    conversations,
    activeConversation,
    isGenerating,
    selectConversation,
    createConversation,
    sendMessage
  } = useChat(backendService, isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) {
      setCurrentUser(null);
    }
  }, [isAuthenticated]);

  const changeView = (view: AppView) => {
    setActiveView(view);
    setSidebarOpen(false);
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    setCurrentUser(authService.getUser());
    setAuthScreen('login');
  };

  const handleRegisterSuccess = () => {
    setIsAuthenticated(true);
    setCurrentUser(authService.getUser());
    setAuthScreen('login');
  };

  const handleLogout = () => {
    authService.logout();
    setIsAuthenticated(false);
    setCurrentUser(null);
    setAuthScreen('login');
    changeView('agent');
  };

  return (
    <div className="app-shell">
      <Sidebar
        conversations={isAuthenticated ? conversations : []}
        activeId={activeConversation?.id ?? ''}
        user={currentUser}
        isAuthenticated={isAuthenticated}
        isOpen={sidebarOpen}
        activeView={activeView}
        onViewChange={changeView}
        onSelect={(id) => {
          selectConversation(id);
          changeView('agent');
        }}
        onNewChat={() => {
          createConversation();
          changeView('agent');
        }}
        onLogin={() => {
          setAuthScreen('login');
          changeView('agent');
        }}
        onLogout={handleLogout}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="chat-panel">
        {activeView === 'calculator' ? (
          <ShippingCalculatorPage
            onGoAgent={() => changeView('agent')}
            onMenu={() => setSidebarOpen(true)}
          />
        ) : !isAuthenticated ? (
          <div className="orion-auth-view">
            {authScreen === 'login' ? (
              <Login
                onSwitchToRegister={() => setAuthScreen('register')}
                onLoginSuccess={handleLoginSuccess}
              />
            ) : (
              <Register
                onSwitchToLogin={() => setAuthScreen('login')}
                onRegisterSuccess={handleRegisterSuccess}
              />
            )}
          </div>
        ) : activeConversation && currentUser ? (
          <>
            <ChatHeader
              assistant={assistant}
              onMenu={() => setSidebarOpen(true)}
              onGoCalculator={() => changeView('calculator')}
            />

            <section
              className="chat-body"
              ref={chatBodyRef}
              onScroll={(event) => {
                const el = event.currentTarget;
                const distanceFromBottom =
                  el.scrollHeight - el.scrollTop - el.clientHeight;

                setShowScrollButton(distanceFromBottom > 120);
              }}
            >
              <div className="welcome">
                <span className="welcome__eyebrow">
                  <span className="signal" />
                  ESPACIO DE TRABAJO PERSONAL
                </span>

                <h2>
                  ¿Qué tienes<br />
                  <em>en mente?</em>
                </h2>

                <p>
                  {assistant.description}. Conversa, organiza
                  y transforma tus ideas en algo concreto.
                </p>
              </div>

              <MessageList
                messages={activeConversation.messages}
                streamingMessage={null}
                isGenerating={isGenerating}
              />
            </section>

            {showScrollButton && (
              <button
                className="scroll-to-bottom"
                type="button"
                aria-label="Ir al final del chat"
                onClick={() => {
                  chatBodyRef.current?.scrollTo({
                    top: chatBodyRef.current.scrollHeight,
                    behavior: 'smooth'
                  });
                }}
              >
                <ArrowDown size={18} />
              </button>
            )}

            <ChatInput
              disabled={isGenerating}
              onSend={sendMessage}
            />
          </>
        ) : null}
      </main>

      {sidebarOpen && (
        <button
          className="scrim"
          onClick={() => setSidebarOpen(false)}
          aria-label="Cerrar menú"
        />
      )}
    </div>
  );
}

export default App;
