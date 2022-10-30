from functools import wraps
import time
import win32gui
from collections import defaultdict
import os

call_timer = [['刷新帧', 0, []], ['识别帧', 0, []], ['查询帧', 0, []]]
for i in range(3):
    call_timer[i][2] = [time.time() - i for i in range(31)]


def timer(func):
    global call_timer

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        ret = func(*args, **kwargs)
        end = time.time()
        if func.__name__ == 'image_process':
            it = 0
        elif func.__name__ == 'process':
            it = 1
        elif func.__name__ == 'search_db':
            it = 2
        call_timer[it][1] = end - start

        call_timer[it][2].insert(0, start)
        call_timer[it][2].pop()

        info = []
        for i in range(3):
            prev5 = 5 / (call_timer[i][2][0] - call_timer[i][2][5])
            prev10 = 10 / (call_timer[i][2][0] - call_timer[i][2][10])
            prev30 = 30 / (call_timer[i][2][0] - call_timer[i][2][30])
            info.append('%s %.2f [%.2f/%.2f/%.2f]' %
                        (call_timer[i][0],
                         call_timer[i][1],
                         prev5,
                         prev10,
                         prev30
                         ))
        print('%s' % ('    '.join(info)))
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
