import PyInstaller.__main__
import os

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 定义需要打包的文件和资源
main_script = os.path.join(current_dir, 'gui.py')
icon_path = os.path.join(current_dir, 'icon.ico')  # 如果有图标文件的话

# PyInstaller 参数
params = [
    main_script,
    '--name=OCR助手',  # 生成的exe名称
    '--windowed',  # 使用GUI模式
    '--noconfirm',  # 不询问确认
    '--clean',  # 清理临时文件
    '--add-data=logs;logs',  # 添加logs文件夹
    '--hidden-import=PIL._tkinter',  # 添加隐藏导入
    '--hidden-import=win32gui',
    '--hidden-import=win32con',
    '--hidden-import=win32api',
    '--hidden-import=paddle',
    '--hidden-import=paddleocr',
]

# 如果有图标文件，添加图标参数
if os.path.exists(icon_path):
    params.append(f'--icon={icon_path}')

# 执行打包命令
PyInstaller.__main__.run(params) 