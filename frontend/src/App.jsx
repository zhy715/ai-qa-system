import { useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import DocumentViewer from './components/DocumentViewer';

function App() {
  // 当前活跃对话 ID
  const [conversationId, setConversationId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  // 文档查看器状态
  const [viewingDocument, setViewingDocument] = useState(null);

  const handleSelectConversation = useCallback((id) => {
    setConversationId(id);
    setRefreshKey((k) => k + 1);
  }, []);

  const handleNewConversation = useCallback(() => {
    setConversationId(null);
    setRefreshKey((k) => k + 1);
  }, []);

  const handleViewDocument = useCallback((filename) => {
    // 点同一个文档 → 关闭；点不同文档 → 切换
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
      />
      <ChatArea
        key={refreshKey}
        conversationId={conversationId}
        onConversationCreated={handleSelectConversation}
      />
      <DocumentViewer
        filename={viewingDocument}
        onClose={handleCloseViewer}
      />
    </>
  );
}

export default App;
