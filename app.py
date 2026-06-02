"""视频转PPT/PDF v1.0 - 入口文件"""

import sys
sys.dont_write_bytecode = True

from core.validator import cleanup_stale_temp
from core.deps import check_dependencies
from ui import VideoConverterFluent


if __name__ == "__main__":
    missing = check_dependencies()
    if missing:
        from tkinter import messagebox
        messagebox.showerror(
            "缺少依赖",
            f"缺少必要的 Python 库:\n{', '.join(missing)}\n\n"
            f"请运行:\npip install -r requirements.txt"
        )
        sys.exit(1)

    cleanup_stale_temp()
    app = VideoConverterFluent()
    app.run()
