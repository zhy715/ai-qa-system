"""对话管理服务 —— JSON 文件持久化"""
import json
import os
import uuid
from datetime import datetime, timezone

from app.models.schemas import ConversationMessage, ConversationInfo, ConversationDetail


class ConversationService:
    """对话 CRUD，数据存在 conversations/ 目录下"""

    def __init__(self, data_dir: str = "conversations"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _path(self, cid: str) -> str:
        return os.path.join(self.data_dir, f"{cid}.json")

    def _load(self, cid: str) -> dict | None:
        path = self._path(cid)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, cid: str, data: dict) -> None:
        with open(self._path(cid), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ─── 创建 ─────────────────────────────────────────

    def create(self, title: str = "新对话") -> ConversationDetail:
        cid = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": cid,
            "title": title,
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        self._save(cid, data)
        return ConversationDetail(**data)

    # ─── 读取 ─────────────────────────────────────────

    def get(self, cid: str) -> ConversationDetail | None:
        data = self._load(cid)
        return ConversationDetail(**data) if data else None

    def list_all(self) -> list[ConversationInfo]:
        result = []
        for fname in os.listdir(self.data_dir):
            if not fname.endswith(".json"):
                continue
            cid = fname[:-5]
            data = self._load(cid)
            if data:
                result.append(ConversationInfo(
                    id=data["id"],
                    title=data["title"],
                    message_count=len(data.get("messages", [])),
                    created_at=data["created_at"],
                    updated_at=data["updated_at"],
                ))
        result.sort(key=lambda c: c.updated_at, reverse=True)
        return result

    # ─── 追加消息 ─────────────────────────────────────

    def add_message(self, cid: str, role: str, content: str,
                    sources: list[str] | None = None) -> bool:
        data = self._load(cid)
        if not data:
            return False

        data["messages"].append({
            "role": role,
            "content": content,
            "sources": sources or [],
        })
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # 用第一条用户消息自动更新标题
        if data["title"] == "新对话":
            for m in data["messages"]:
                if m["role"] == "user":
                    data["title"] = m["content"][:30]
                    break

        self._save(cid, data)
        return True

    def get_messages(self, cid: str, limit: int = 10) -> list[ConversationMessage]:
        """获取最近 N 条消息（用于构建 LLM 上下文）"""
        data = self._load(cid)
        if not data:
            return []
        recent = data["messages"][-limit:]
        return [ConversationMessage(**m) for m in recent]

    # ─── 删除 ─────────────────────────────────────────

    def delete(self, cid: str) -> bool:
        path = self._path(cid)
        if not os.path.exists(path):
            return False
        os.remove(path)
        return True
