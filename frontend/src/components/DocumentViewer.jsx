import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Loader2, FileText } from 'lucide-react';
import { API_BASE } from '../api/config';

const MIN_WIDTH = 280;
const MAX_WIDTH = 800;
const DEFAULT_WIDTH = 480;

export default function DocumentViewer({ filename, onClose }) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef(null);

  // 加载文档内容
  useEffect(() => {
    if (!filename) return;
    setLoading(true);
    setError('');
    fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}/content`)
      .then((r) => {
        if (!r.ok) throw new Error('加载失败');
        return r.json();
      })
      .then((d) => setContent(d.content || ''))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filename]);

  // ── 拖拽调整宽度 ─────────────────────────────────
  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e) => {
      // 面板在右侧，宽度 = 窗口右侧 - 鼠标X
      const newWidth = window.innerWidth - e.clientX;
      setWidth(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, newWidth)));
    };

    const handleMouseUp = () => setIsResizing(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    // 防止拖拽时选中文字
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isResizing]);

  if (!filename) return null;

  return (
    <div ref={panelRef} style={{ ...styles.panel, width }}>
      {/* 拖拽手柄 */}
      <div
        style={{
          ...styles.handle,
          background: isResizing ? 'oklch(0.58 0.16 45)' : 'transparent',
        }}
        onMouseDown={handleMouseDown}
      />

      {/* 标题栏 */}
      <div style={styles.titleBar}>
        <div style={styles.titleLeft}>
          <FileText size={16} style={{ color: '#a8a29e', flexShrink: 0 }} />
          <span style={styles.title}>{filename}</span>
        </div>
        <button style={styles.closeBtn} onClick={onClose} title="关闭">
          <X size={18} />
        </button>
      </div>

      {/* 内容区 */}
      <div style={styles.content}>
        {loading ? (
          <div style={styles.center}>
            <Loader2 size={24} style={{ color: '#a8a29e', animation: 'spin 1s linear infinite' }} />
            <span style={styles.loadingText}>加载中…</span>
          </div>
        ) : error ? (
          <div style={styles.center}>
            <span style={styles.errorText}>{error}</span>
          </div>
        ) : (
          <pre style={styles.text}>{content}</pre>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

const styles = {
  panel: {
    height: '100vh',
    background: '#fefefe',
    borderLeft: '1px solid #e8e6e1',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    flexShrink: 0,
    fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
  },
  handle: {
    position: 'absolute',
    left: -3,
    top: 0,
    bottom: 0,
    width: 6,
    cursor: 'col-resize',
    zIndex: 10,
    transition: 'background 150ms',
    borderRadius: '0 3px 3px 0',
  },
  titleBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 18px',
    borderBottom: '1px solid #f0ede8',
    gap: 10,
  },
  titleLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    overflow: 'hidden',
    flex: 1,
  },
  title: {
    fontSize: 14,
    fontWeight: 600,
    color: '#1a1a1a',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  closeBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 32,
    height: 32,
    borderRadius: 8,
    border: 'none',
    background: 'transparent',
    color: '#a8a29e',
    cursor: 'pointer',
    flexShrink: 0,
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px 24px',
  },
  text: {
    fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
    fontSize: 14,
    lineHeight: 1.8,
    color: '#44403c',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    margin: 0,
  },
  center: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: 12,
    color: '#a8a29e',
  },
  loadingText: {
    fontSize: 13,
    color: '#a8a29e',
  },
  errorText: {
    fontSize: 13,
    color: '#dc2626',
  },
};
