/** API 请求层 — 与 FastAPI 后端通信 */

const BASE_URL = 'http://localhost:8000';

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** 上传 PDF 文档 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Upload failed`);
  }
  return res.json();
}

/** 获取文档列表 */
export function getDocuments() {
  return request('/documents');
}

/** RAG 问答 */
export function queryKnowledge(question, topK = 3) {
  return request('/query', {
    method: 'POST',
    body: JSON.stringify({ question, top_k: topK }),
  });
}

/** 健康检查 */
export function healthCheck() {
  return request('/health');
}
