"""对话管理服务测试"""
import os
import tempfile

from app.services.conversation_service import ConversationService


class TestConversationService:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.service = ConversationService(data_dir=self.temp_dir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_conversation(self):
        conv = self.service.create()
        assert conv.id is not None
        assert len(conv.id) == 12
        assert conv.title == "新对话"
        assert conv.messages == []

    def test_get_conversation(self):
        conv = self.service.create("测试对话")
        retrieved = self.service.get(conv.id)
        assert retrieved is not None
        assert retrieved.title == "测试对话"

    def test_get_nonexistent(self):
        assert self.service.get("nonexistent") is None

    def test_add_message(self):
        conv = self.service.create()
        self.service.add_message(conv.id, "user", "你好")
        self.service.add_message(conv.id, "assistant", "你好！有什么可以帮你的？")

        detail = self.service.get(conv.id)
        assert len(detail.messages) == 2
        assert detail.messages[0].role == "user"
        assert detail.messages[1].role == "assistant"

    def test_auto_title_from_first_message(self):
        """第一条用户消息应自动更新对话标题"""
        conv = self.service.create()
        self.service.add_message(conv.id, "user", "劳动合同解除的法律条件是什么？")
        detail = self.service.get(conv.id)
        assert "劳动合同解除" in detail.title

    def test_get_messages_with_limit(self):
        conv = self.service.create()
        for i in range(5):
            self.service.add_message(conv.id, "user", f"问题{i}")
            self.service.add_message(conv.id, "assistant", f"回答{i}")

        recent = self.service.get_messages(conv.id, limit=4)
        assert len(recent) == 4  # 总共 10 条，limit 4 返回最近 4 条

    def test_list_all(self):
        self.service.create("对话A")
        self.service.create("对话B")
        convs = self.service.list_all()
        assert len(convs) == 2

    def test_delete(self):
        conv = self.service.create()
        assert self.service.delete(conv.id) is True
        assert self.service.get(conv.id) is None

    def test_delete_nonexistent(self):
        assert self.service.delete("nonexistent") is False
