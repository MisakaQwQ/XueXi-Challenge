from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime, QObject
from PyQt5.QtGui import *
import win32gui
import sys
import time
from ui import Ui_MainWindow
from PIL import Image, ImageQt
import cv2
import numpy as np
from qgmodel import *
from playhouse.shortcuts import model_to_dict
import difflib
import math
from ocr.cn_ocr import CnOcr

all_questions = []
ocr = CnOcr()
MODE = 2


class OCR_backend(QThread):
    update = pyqtSignal(str)
    ocr_text = ''

    def __del__(self):
        self.wait()

    def __init__(self, parent=None, image=True):  # do_create_data放在最后
        super(OCR_backend, self).__init__(parent)
        self.image = image

    def search_db(self):
        def builder(font_size, color, font_family, content):
            html = '''<span style="font-size:%dpx;color:%s;font-family:'%s';"> %s <br /><br /></span>''' \
                   % (font_size, color, font_family, content)
            return html

        score = [0, 0]
        cnt = 0
        for each in all_questions:
            tmp = difflib.SequenceMatcher(None, self.ocr_text, each['question']).quick_ratio()
            if tmp > score[0]:
                score[0] = tmp
                score[1] = cnt
            cnt += 1
        # if score[0] < 0.5:
        #     cv2.imwrite(str(time.time()) + '.png', self.image)
        html = builder(15, '#000000', '楷体', '置信度: %.2f' % score[0])
        html += builder(25, '#000000', '楷体', all_questions[score[1]]['question'])
        for i in range(1, 5):
            if all_questions[score[1]]['choice' + str(i)] == '':
                break
            if all_questions[score[1]]['answer'] == str(i):
                html += builder(
                    20, '#ff00ff', '楷体', (chr(ord('A') + i - 1) + '.  ' + all_questions[score[1]]['choice' + str(i)]))
            else:
                html += builder(
                    18, '#000000', '楷体', (chr(ord('A') + i - 1) + '.  ' + all_questions[score[1]]['choice' + str(i)]))
        end_html = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">' \
                   '<html><head><meta name="qrichtext" content="1" /><style type="text/css">' \
                   'p, li { white-space: pre-wrap; }</style></head><body> %s </body></html>' % html
        self.update.emit('H' + end_html)

    def process(self):
        # 二值化
        ret, binary = cv2.threshold(self.image, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY)
        # Sobel查找边缘
        sobel = cv2.Sobel(binary, cv2.CV_16S, 2, 0)
        sobel = cv2.convertScaleAbs(sobel)
        # 核函数
        kernel0 = np.ones((3, 3), np.uint8)
        kernel1 = np.ones((7, 16), np.uint8)
        # 腐蚀
        erosion = cv2.erode(sobel, kernel0, iterations=1)
        # 膨胀
        dilation = cv2.dilate(erosion, kernel1, iterations=2)

        region = []
        contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for each in contours:
            area = cv2.contourArea(each)
            if area < 600:
                continue
            rect = cv2.minAreaRect(each)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            region.append(box)

        self.ocr_text = ''
        cnt = 0
        for box in region[::-1]:
            top_left = box[0].copy()
            bot_right = box[0].copy()
            for each in box:
                top_left[0] = max(min(top_left[0], each[0]), 0)
                top_left[1] = max(min(top_left[1], each[1]), 0)
                bot_right[0] = min(max(bot_right[0], each[0]), self.image.shape[1] - 1)
                bot_right[1] = min(max(bot_right[1], each[1]), self.image.shape[0] - 1)
            pic = self.image[top_left[1]:bot_right[1], top_left[0]:bot_right[0]]
            text = ocr.ocr(pic)
            for each in text:
                self.ocr_text += ''.join(each)
            if cnt == 0:
                self.search_db()
            # cv2.imwrite(str(cnt)+'.png', pic)
            cv2.rectangle(self.image, (top_left[0], top_left[1]), (bot_right[0], bot_right[1]), (0, 0, 0))
            cnt += 1
            self.ocr_text += '\n'
        cv2.imwrite('split.png', self.image.copy())
        self.update.emit('T' + self.ocr_text)

    def run(self):
        try:
            self.process()
        except Exception as e:
            print(e)


class Main_backend(QThread):
    # 通过类成员对象定义信号
    update_img = pyqtSignal(QImage)
    update_txt = pyqtSignal(str)
    hwnd = None
    hwnd_stat = 0
    tpl1 = None
    image = None
    image_stat = None
    image_content = None
    image_content_now = None

    ocr_cnt = 0
    ocr_block = False

    def get_hwnd(self):
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

    def handle_rtn(self, data):
        self.ocr_block = False
        self.update_txt.emit(data)

    def __del__(self):
        self.wait()

    def __init__(self, parent=None):
        super(Main_backend, self).__init__(parent)
        self.tpl1 = cv2.imread("data/Pos%d.png"%MODE)

    def start_ocr(self):
        self.ocr_block = True
        self.image_content_now = self.image_content.copy()
        self.ocr_backend = OCR_backend(self, self.image_content_now)
        self.ocr_backend.update.connect(self.handle_rtn)
        self.ocr_backend.start()

    def image_wrap(self):
        left_up = [0, self.image.shape[0] // 4]
        right_bot = [self.image.shape[1] - 1, self.image.shape[0] - 1]
        while self.image[left_up[1]][left_up[0]].tolist() == self.image[left_up[1] - 1][left_up[0]].tolist():
            left_up[1] -= 1
        self.image = self.image[left_up[1] + 1:right_bot[1], 1:right_bot[0]]
        new_image = cv2.cvtColor(self.image, cv2.COLOR_RGB2GRAY)
        col = new_image.mean(axis=0).tolist()
        left_up = [0, 0]
        right_bot = [0, new_image.shape[0]]
        threshold = 5
        for i in range(0, len(col)):
            if col[i] != 0 or abs(col[i + 1] - col[i]) >= threshold:
                left_up[0] = i
                break
        for i in range(len(col) - 1, -1, -1):
            if col[i] != 0 or abs(col[i - 1] - col[i]) >= threshold:
                right_bot[0] = i
                break
        bias = min(left_up[0], new_image.shape[1] - right_bot[0])
        left_up[0] = bias
        right_bot[0] = new_image.shape[1] - bias
        self.image = self.image[left_up[1]:right_bot[1] + 1, left_up[0]:right_bot[0] + 1]

    def image_process(self):
        self.image = ImageQt.fromqimage(self.image)
        self.image = cv2.cvtColor(np.asarray(self.image), cv2.COLOR_RGB2BGR)
        self.image_wrap()
        if MODE == 1:
            threshold = 0.97  # 定位点置信度
            horizon_margin = 0.05
            horizon_size = 0.85
            vertical_margin = 0.16
            vertical_size = 0.75
        elif MODE == 2 or MODE == 3:
            threshold = 0.97  # 定位点置信度
            horizon_margin = 0.05
            horizon_size = 0.85
            vertical_margin = 0.12
            vertical_size = 0.5
        pos2 = [0, 0]

        if self.image.shape[0] > self.image.shape[1]:  # 判断竖屏状态
            res = cv2.matchTemplate(self.image, self.tpl1, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if res[max_loc[1]][max_loc[0]] > threshold and max_loc[0] < 40:  # 判断答题界面
                pos1 = [max_loc[0], max_loc[1]]  # 主定位点
                pos1[0] = pos1[0] + math.ceil(horizon_margin * self.image.shape[1])
                pos1[1] = pos1[1] + math.ceil(vertical_margin * self.image.shape[0])
                pos2[0] = pos1[0] + math.ceil(horizon_size * self.image.shape[1])
                pos2[1] = pos1[1] + math.ceil(vertical_size * self.image.shape[0])
                cv2.rectangle(self.image, tuple(pos1), tuple(pos2), (0, 255, 255), 2)
                self.image_content = self.image[pos1[1] + 2:pos2[1] - 1, pos1[0] + 2:pos2[0] - 1]
                self.image_content = cv2.cvtColor(self.image_content, cv2.COLOR_RGB2GRAY)
                if self.ocr_cnt == 0 and self.ocr_block == False:
                    self.start_ocr()
            else:
                self.image_content_now = None
        self.image = Image.fromarray(cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB))
        self.image = ImageQt.ImageQt(self.image)

    # 处理业务逻辑
    def run(self):
        while True:
            try:
                screen = QApplication.primaryScreen()
                if self.hwnd == None:
                    self.hwnd = self.get_hwnd()
                    if self.hwnd == None:
                        self.update_txt.emit('T句柄无效，请打开AirPlayer并连接')
                        self.hwnd_stat = 0
                        time.sleep(3)
                self.image = screen.grabWindow(self.hwnd).toImage()
                # self.image.save("screenshot.jpg")
                try:
                    ImageQt.fromqimage(self.image)
                    if self.hwnd_stat == 0:
                        self.update_txt.emit('T ')
                    self.hwnd_stat = 1
                except Exception as e:
                    self.hwnd = None
                    continue
                self.image_process()
                sender = self.image.copy()
                self.update_img.emit(sender)
                time.sleep(1 / 30)
                self.ocr_cnt = (self.ocr_cnt + 1) % 15
            except Exception as e:
                print(e)


class my_ui(QMainWindow, Ui_MainWindow):
    def handleOCR(self, data):
        try:
            # print('OCR update')
            if data[0] == 'T':
                self.Rec_out.setText(data[1:])
            if data[0] == 'H':
                self.Ans.setText(data[1:])
        except Exception as e:
            print(e)

    def __init__(self, parent=None):
        super(my_ui, self).__init__(parent)
        self.main_backend = Main_backend(self)
        # 连接信号
        self.main_backend.update_img.connect(self.handleDisplay)
        self.main_backend.update_txt.connect(self.handleOCR)
        # 开始线程
        self.main_backend.start()

    def handleDisplay(self, data):
        try:
            zoomscale = 1
            pix = QPixmap.fromImage(data)
            self.item = QGraphicsPixmapItem(pix)
            self.item.setScale(zoomscale)
            self.scene = QGraphicsScene()  # 创建场景
            self.scene.addItem(self.item)
            self.img_out.setScene(self.scene)
        except Exception as e:
            print(e)


def run():
    try:
        db.connect()
        try:
            db.create_tables([Questions])
        except Exception as e:
            print(e)
            pass
        cursor = Questions.select()
        for each in cursor:
            all_questions.append(model_to_dict(each))
        app = QApplication(sys.argv)
        main_window = QMainWindow()
        ui = my_ui()
        ui.setupUi(main_window)
    except Exception as e:
        print(e)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
