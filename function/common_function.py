from functools import wraps
import time
import win32gui


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        ret = func(*args, **kwargs)
        end = time.time()
        print(func.__name__, end - start)
        return ret

    return wrapper


def get_hwnd():
    def get_all_hwnd(hwnd, extra):
        windows = extra
        temp = []
        temp.append(hwnd)
        temp.append(win32gui.GetClassName(hwnd))
        temp.append(win32gui.GetWindowText(hwnd))
        windows[hwnd] = temp

    windows = {}
    win32gui.EnumWindows(get_all_hwnd, windows)
    for key, value in windows.items():
        if value[1] == 'CHWindow' and value[2] == '':
            return value[0]
    return -1