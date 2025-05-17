# OCR助手

一个基于 PaddleOCR 的自动化窗口识别工具，可以自动识别和点击指定窗口中的文本。

## 功能特点

- 自动识别窗口中的文本
- 支持自动点击识别到的文本
- 支持多个任务状态自动切换
- 实时日志记录
- 友好的图形用户界面

## 系统要求

- Windows 10 或更高版本
- Python 3.7 或更高版本
- 支持 CUDA 的显卡（可选，用于 GPU 加速）

## 安装说明

1. 克隆仓库：
```bash
git clone https://github.com/你的用户名/ocr-assistant.git
cd ocr-assistant
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行程序：
```bash
python gui.py
```

2. 在界面中选择要识别的窗口
3. 点击"开始识别"按钮开始自动识别
4. 点击"停止识别"按钮停止识别

## 打包说明

使用以下命令打包成可执行文件：
```bash
python build.py
```

打包后的文件将在 `dist` 目录中生成。

## 注意事项

- 首次运行可能需要下载 PaddleOCR 模型文件
- 如果使用 GPU 加速，请确保已正确安装 CUDA 和 CUDNN
- 建议在使用前先测试程序是否正常运行

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！ 