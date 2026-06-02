# 视频转 PPT/PDF

将视频文件智能转换为 PPT 或 PDF 文档。支持定时截图和静止检测两种模式，自动去重相似画面。

## 功能特点

- **双模式截图**：定时截图 / 画面静止自动截图
- **智能去重**：基于感知哈希算法，自动过滤相似帧
- **多格式输出**：支持 PPTX 和 PDF
- **批量处理**：一次添加多个视频，排队转换
- **可视化界面**：基于 CustomTkinter 的现代化 GUI

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行

```bash
python app.py
```

Windows 下也可直接双击 `启动.bat`。

## 使用说明

1. 点击 **浏览文件** 或 **添加多个** 选择视频
2. 选择输出格式（PPT / PDF）和输出目录
3. 设置截图方式：
   - **定时截图**：按固定时间间隔截图（如每 1 秒一张）
   - **静止检测**：画面静止超过阈值时自动截图
4. 调整去重相似度（默认 95%）
5. 点击 **开始转换**

## 支持格式

| 类型 | 格式 |
|------|------|
| 输入视频 | MP4, AVI, MKV, MOV, WMV, FLV, WEBM |
| 输出文档 | PPTX, PDF |

## 项目结构

```
├── app.py                  # 入口文件
├── config/
│   ├── __init__.py          # 集中配置
│   └── themes.py            # 主题配置
├── core/
│   ├── engine.py            # 视频帧提取引擎
│   ├── generator.py         # PPT/PDF 生成器
│   ├── converter.py         # 转换任务管理
│   ├── validator.py         # 文件校验工具
│   └── deps.py              # 依赖检查
├── ui/
│   ├── main_window.py       # 主界面
│   ├── dialogs.py           # 弹窗管理
│   └── widgets.py           # 可复用组件
├── tests/
├── scripts/
├── requirements.txt
└── README.md
```
