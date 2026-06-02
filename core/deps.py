"""依赖检查"""

import importlib.util
from typing import List


def check_dependencies() -> List[str]:
    """检查必要的 Python 库是否已安装，返回缺失列表"""
    missing: List[str] = []
    # 包名到 import 名的映射
    pkg_map = {
        "opencv-python": "cv2",
        "python-pptx": "pptx",
        "fpdf2": "fpdf",
        "Pillow": "PIL",
        "customtkinter": "customtkinter",
    }
    for pkg_name, import_name in pkg_map.items():
        if not importlib.util.find_spec(import_name):
            missing.append(pkg_name)
    return missing
