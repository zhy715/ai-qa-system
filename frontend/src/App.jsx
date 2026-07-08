import { useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';

function App() {
  // 当前活跃对话 ID，null = 没有对话（欢迎页）
  const [conversationId, setConversationId] = useState(null);
  // 刷新信号：切换对话时递增，通知 ChatArea 重新加载
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSelectConversation = useCallback((id) => {
    setConversationId(id);
    setRefreshKey((k) => k + 1);
  }, []);

  const handleNewConversation = useCallback(() => {
    setConversationId(null);
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <>
      <Sidebar
        conversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      <ChatArea
        key={refreshKey}
        conversationId={conversationId}
        onConversationCreated={handleSelectConversation}
      />
    </>
  );
}

export default App;
