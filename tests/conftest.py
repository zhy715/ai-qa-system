"""测试配置与共享 fixtures"""
import os
import sys
import tempfile

import pytest

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """临时目录，测试后自动清理"""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_txt_file(temp_dir):
    """创建一个示例 TXT 文件"""
    path = os.path.join(temp_dir, "test.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("这是第一段测试文本。\n\n这是第二段测试文本。\n\n这是第三段测试文本。")
    return path
