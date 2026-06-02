"""依赖检查测试"""
from core.deps import check_dependencies


def test_check_dependencies_returns_list():
    result = check_dependencies()
    assert isinstance(result, list)
