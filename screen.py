import win32gui
import win32ui
import win32con
import win32api
from PIL import Image
import ctypes

def capture_application_window(window_title):
    # 获取窗口句柄
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd == 0:
        raise ValueError(f"未找到窗口 '{window_title}'")

    # 恢复窗口（如果最小化）
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.UpdateWindow(hwnd)
    
    # 获取DPI缩放因子
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()  # 设置DPI感知
    except:
        pass  # 如果失败，继续使用默认设置
    
    # 获取窗口位置和大小
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bot - top
    
    # 使用PrintWindow方法截图
    hwndDC = win32gui.GetWindowDC(hwnd)
    if hwndDC == 0:
        raise ValueError("无法获取窗口DC")
    
    try:
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        # 创建位图
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        
        # 使用PrintWindow截图，这对分层窗口更有效
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)  # PW_RENDERFULLCONTENT = 3
        
        # 如果PrintWindow失败，尝试使用BitBlt
        if not result:
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
        
        # 转换为PIL图像
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        image = Image.frombuffer(
            "RGB",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr, "raw", "BGRX", 0, 1
        )
        
        # 释放资源（严格按顺序）
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        return image
    
    except Exception as e:
        # 确保资源被释放
        try:
            win32gui.ReleaseDC(hwnd, hwndDC)
            mfcDC.DeleteDC()
            saveDC.DeleteDC()
        except:
            pass
        raise ValueError(f"截图过程中发生错误: {str(e)}")

