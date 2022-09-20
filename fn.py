from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ocr.cn_ocr import CnOcr
from qgmodel import *
from UI.ui import Ui_MainWindow
from function.common_function import *

import sys
import time
import math
from PIL import Image, ImageQt
import cv2
import numpy as np
from playhouse.shortcuts import model_to_dict
import difflib
import json

all_questions = []
ocr = CnOcr(context='gpu', model_backend='pytorch')


def init():
    global all_questions
    # db.connect()
    # try:
    #     db.create_tables([Questions])
    # except Exception as e:
    #     print(e)
    #     pass
    # cursor = Questions.select()
    # for each in cursor:
    #     all_questions.append(model_to_dict(each))
    #
    with open('./TiKu/题库_排序版.json', 'r', encoding='utf-8') as fp:
        questions = json.load(fp)

    for key, value in questions.items():
        tmp = key.split('|')
        one_question = {
            'question': tmp[0],
            'answer': 0,
            'choice1': tmp[1],
            'choice2': tmp[2],
            'choice3': '',
            'choice4': ''
        }
        if len(tmp) >= 4:
            one_question['choice3'] = tmp[3]
        if len(tmp) >= 5:
            one_question['choice4'] = tmp[4]
        if one_question['choice1'] == value:
            one_question['answer'] = 1
        elif one_question['choice2'] == value:
            one_question['answer'] = 2
        elif one_question['choice3'] == value:
            one_question['answer'] = 3
        elif one_question['choice4'] == value:
            one_question['answer'] = 4
        all_questions.append(one_question)
    pass


def find_closest_question(question):
    target = [0, 0]
    idx = 0
    for each in all_questions:
        tmp = difflib.SequenceMatcher(None, question, each['question']).quick_ratio()
        if tmp > target[0]:
            target[0] = tmp
            target[1] = idx
        idx += 1
    return target


class OCR_backend(QThread):
    update_rec = pyqtSignal(str)
    update_ans = pyqtSignal(str)
    available = True
    ocr_text = ''

    def __init__(self, parent=None):
        super(OCR_backend, self).__init__(parent)
        self.mutex = QMutex()
        self.cond = QWaitCondition()

    @timer
    def search_db(self):
        def builder(font_size, color, font_family, content):
            html = '''<span style="font-size:%dpx;color:%s;font-family:'%s';"> %s <br /><br /></span>''' \
                   % (font_size, color, font_family, content)
            return html

        score = find_closest_question(self.ocr_text)

        # if score[0] < 0.5:
        #     cv2.imwrite(str(time.time()) + '.png', self.image)
        html = builder(15, '#000000', '楷体', '置信度: %.2f' % score[0])
        html += builder(25, '#000000', '楷体', all_questions[score[1]]['question'])
        for i in range(1, 5):
            if all_questions[score[1]]['choice' + str(i)] == '':
                break
            if str(all_questions[score[1]]['answer']) == str(i):
                html += builder(
                    20, '#ff00ff', '楷体', (chr(ord('A') + i - 1) + '.  ' + all_questions[score[1]]['choice' + str(i)]))
            else:
                html += builder(
                    18, '#000000', '楷体', (chr(ord('A') + i - 1) + '.  ' + all_questions[score[1]]['choice' + str(i)]))
        end_html = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">' \
                   '<html><head><meta name="qrichtext" content="1" /><style type="text/css">' \
                   'p, li { white-space: pre-wrap; }</style></head><body> %s </body></html>' % html
        self.update_ans.emit(end_html)

    @timer
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
                self.ocr_text += ''.join(each[0])
            if cnt == 0:
                self.search_db()
            # cv2.imwrite(str(cnt)+'.png', pic)
            cv2.rectangle(self.image, (top_left[0], top_left[1]), (bot_right[0], bot_right[1]), (0, 0, 0))
            cnt += 1
            self.ocr_text += '\n'
        # cv2.imwrite('split.png', self.image.copy())
        self.update_rec.emit(self.ocr_text)

    def start_working(self, image):
        try:
            self.available = False
            self.image = image
            self.cond.wakeAll()
        except Exception as e:
            print(e)

    def run(self):
        while True:
            self.mutex.lock()
            if self.available:
                self.cond.wait(self.mutex)
            else:
                try:
                    self.process()
                except Exception as e:
                    print(e)
                self.available = True
            self.msleep(100)
            self.mutex.unlock()


class Main_backend(QThread):
    update_img = pyqtSignal(QImage)
    update_rec = pyqtSignal(str)
    update_ans = pyqtSignal(str)
    tpl1 = None
    mode = 1

    def __init__(self, parent=None):
        super(Main_backend, self).__init__(parent)
        self.tpl1 = cv2.imread("data/Pos1.png")
        self.ocr_backend = OCR_backend(self)
        self.ocr_backend.update_rec.connect(self.handleRec)
        self.ocr_backend.update_ans.connect(self.handleAns)
        self.ocr_backend.start()

    def update_mode(self, mode):
        self.mode = mode
        self.tpl1 = cv2.imread("data/Pos%d.png" % self.mode)
        pass

    def handleAns(self, data):
        self.update_ans.emit(data)

    def handleRec(self, data):
        self.update_rec.emit(data)

    def start_ocr(self, rec_image):
        if self.ocr_backend.available:
            self.ocr_backend.start_working(rec_image.copy())

    def image_wrap(self, image):
        left_up = [0, image.shape[0] // 4]
        right_bot = [image.shape[1] - 1, image.shape[0] - 1]
        while image[left_up[1]][left_up[0]].tolist() == image[left_up[1] - 1][left_up[0]].tolist():
            left_up[1] -= 1
        image = image[left_up[1] + 1:right_bot[1], 1:right_bot[0]]
        new_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
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
        wrapped_image = image[left_up[1]:right_bot[1] + 1, left_up[0]:right_bot[0] + 1]
        return wrapped_image

    @timer
    def image_process(self, image):
        wrapped_image = self.image_wrap(image)
        if self.mode == 1:
            threshold = 0.85
            horizon_margin = 0.05
            horizon_size = 0.85
            vertical_margin = 0.16
            vertical_size = 0.75
        else:
            threshold = 0.85
            horizon_margin = 0.07
            horizon_size = 0.85
            vertical_margin = 0.06
            vertical_size = 0.60
        pos2 = [0, 0]

        if wrapped_image.shape[0] > wrapped_image.shape[1]:  # 判断竖屏状态
            res = cv2.matchTemplate(wrapped_image, self.tpl1, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if res[max_loc[1]][max_loc[0]] > threshold and max_loc[0] < 40:  # 判断答题界面
                pos1 = [max_loc[0], max_loc[1]]  # 主定位点
                pos1[0] = pos1[0] + math.ceil(horizon_margin * wrapped_image.shape[1])
                pos1[1] = pos1[1] + math.ceil(vertical_margin * wrapped_image.shape[0])
                pos2[0] = pos1[0] + math.ceil(horizon_size * wrapped_image.shape[1])
                pos2[1] = pos1[1] + math.ceil(vertical_size * wrapped_image.shape[0])
                cv2.rectangle(wrapped_image, tuple(pos1), tuple(pos2), (0, 255, 255), 2)
                image_content = wrapped_image[pos1[1] + 2:pos2[1] - 1, pos1[0] + 2:pos2[0] - 1]
                image_content = cv2.cvtColor(image_content, cv2.COLOR_RGB2GRAY)
                self.start_ocr(image_content)
        return wrapped_image

    def run(self):
        hwnd = 0
        while True:
            try:
                if hwnd == 0:
                    hwnd = get_hwnd()
                if hwnd == -1:
                    self.update_rec.emit('句柄无效，请打开AirPlayer并连接')
                    time.sleep(1)
                    hwnd = get_hwnd()
                    continue
                screen = QApplication.primaryScreen()
                try:
                    raw_image = screen.grabWindow(hwnd).toImage()
                    PIL_image = ImageQt.fromqimage(raw_image)
                    CV_image = cv2.cvtColor(np.asarray(PIL_image), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    hwnd = 0
                    continue
                labeled_image = self.image_process(CV_image)
                labeled_image = Image.fromarray(cv2.cvtColor(labeled_image, cv2.COLOR_BGR2RGB))
                labeled_image = ImageQt.ImageQt(labeled_image)
                self.update_img.emit(labeled_image.copy())
                time.sleep(1 / 100)
            except Exception as e:
                print(e)


class my_ui(QMainWindow, Ui_MainWindow):
    def handleAns(self, data):
        self.answer.setText(data)

    def handleRec(self, data):
        self.result.setText(data)

    def __init__(self, parent=None):
        super(my_ui, self).__init__(parent)
        self.setupUi(self)
        self.main_backend = Main_backend(self)

        self.main_backend.update_img.connect(self.handleDisplay)
        self.main_backend.update_rec.connect(self.handleRec)
        self.main_backend.update_ans.connect(self.handleAns)
        self.mode1.clicked.connect(lambda: self.main_backend.update_mode(1))
        self.mode2.clicked.connect(lambda: self.main_backend.update_mode(2))
        self.mode3.clicked.connect(lambda: self.main_backend.update_mode(3))

        self.main_backend.start()

    def handleDisplay(self, data):
        try:
            zoomscale = 1
            pix = QPixmap.fromImage(data)
            self.item = QGraphicsPixmapItem(pix)
            self.item.setScale(zoomscale)
            self.scene = QGraphicsScene()
            self.scene.addItem(self.item)
            self.img_out.setScene(self.scene)
        except Exception as e:
            print(e)


def run():
    try:
        init()
        app = QApplication(sys.argv)
        main_window = my_ui()
    except Exception as e:
        print(e)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()
