import { useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import DocumentViewer from './components/DocumentViewer';

function App() {
  const [conversationId, setConversationId] = useState(null);
  const [viewingDocument, setViewingDocument] = useState(null);
  // 递增此值通知 Sidebar 刷新对话列表（不触发 ChatArea 重挂载）
  const [sidebarRefresh, setSidebarRefresh] = useState(0);

  const handleSelectConversation = useCallback((id) => {
    setConversationId(id);
  }, []);

  const handleNewConversation = useCallback(() => {
    setConversationId(null);
  }, []);

  // ChatArea 创建新对话后，通知 Sidebar 刷新列表，但不重挂载 ChatArea
  const handleConversationCreated = useCallback((id) => {
    setConversationId(id);
    setSidebarRefresh((k) => k + 1);
  }, []);

  const handleViewDocument = useCallback((filename) => {
    setViewingDocument((prev) => (prev === filename ? null : filename));
  }, []);

  const handleCloseViewer = useCallback(() => {
    setViewingDocument(null);
  }, []);

  return (
    <>
      <Sidebar
        conversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        viewingDocument={viewingDocument}
        onViewDocument={handleViewDocument}
        refreshSignal={sidebarRefresh}
      />
      <ChatArea
        conversationId={conversationId}
        onConversationCreated={handleConversationCreated}
      />
      <DocumentViewer
        filename={viewingDocument}
        onClose={handleCloseViewer}
      />
    </>
  );
}

export default App;
