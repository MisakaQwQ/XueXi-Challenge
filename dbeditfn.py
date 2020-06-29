from PyQt5.QtWidgets import QApplication, QMainWindow, QHeaderView, QTableWidgetItem, QTableView
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime, QObject
from PyQt5.QtGui import *
import sys
from playhouse.shortcuts import model_to_dict
import difflib

from dbedit import Ui_MainWindow
from qgmodel import *


class Main_ui(QMainWindow, Ui_MainWindow):
    content = []
    pend = None
    row_count = 0
    stack_ = []
    remapper = ['id', 'question', 'answer', 'choice1', 'choice2', 'choice3', 'choice4']

    def Table_widget_init(self):
        self.tableWidget.setEditTriggers(QTableView.NoEditTriggers)
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels(['id', '题干', '答案', '答案A', '答案B', '答案C', '答案D'])
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setColumnWidth(0, 20)
        self.tableWidget.setColumnWidth(1, 290)
        self.tableWidget.setColumnWidth(2, 20)
        self.tableWidget.setColumnWidth(3, 110)
        self.tableWidget.setColumnWidth(4, 110)
        self.tableWidget.setColumnWidth(5, 110)
        self.tableWidget.setColumnWidth(6, 110)

    def Reload_database(self):
        self.content = []
        cursor = Questions.select()
        for each in cursor:
            self.content.append(model_to_dict(each))
        self.row_count = len(self.content)
        self.tableWidget.setRowCount(self.row_count)
        for row in range(len(self.content)):
            for col in range(len(self.remapper)):
                oneItem = QTableWidgetItem(str(self.content[row][self.remapper[col]]))
                self.tableWidget.setItem(row, col, oneItem)

    def View_Update(self):
        def builder(font_size, color, font_family, content):
            html = '''<span style="font-size:%dpx;color:%s;font-family:'%s';"> %s <br /><br /></span>''' \
                  % (font_size, color, font_family, content)
            return html
        score = [0, 0]
        cnt = 0
        for each in self.content:
            tmp = difflib.SequenceMatcher(None, self.pend.question, each['question']).quick_ratio()
            if tmp > score[0]:
                score[0] = tmp
                score[1] = cnt
            cnt += 1
        html = builder(13, '#000000', '楷体', '置信度: %.2f' % score[0])
        html += builder(22, '#000000', '楷体', self.content[score[1]]['question'])
        for i in range(1, 5):
            if self.content[score[1]]['choice' + str(i)] == '':
                break
            if self.content[score[1]]['answer'] == str(i):
                html += builder(
                    18, '#ff00ff', '楷体', (chr(ord('A') + i - 1) + '.  ' + self.content[score[1]]['choice' + str(i)]))
            else:
                html += builder(
                    16, '#000000', '楷体', (chr(ord('A') + i - 1) + '.  ' + self.content[score[1]]['choice' + str(i)]))
        end_html = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">' \
                   '<html><head><meta name="qrichtext" content="1" /><style type="text/css">' \
                   'p, li { white-space: pre-wrap; }</style></head><body> %s </body></html>' % html
        self.View.setText(end_html)

    def Chk_database(self):
        question = self.Input_Question.toPlainText()
        answer1 = self.Input_AnsA.toPlainText()
        answer2 = self.Input_AnsB.toPlainText()
        answer3 = self.Input_AnsC.toPlainText()
        answer4 = self.Input_AnsD.toPlainText()
        choice = None
        if self.Ans_Chk_A.isChecked():
            choice = '1'
        elif self.Ans_Chk_B.isChecked():
            choice = '2'
        elif self.Ans_Chk_C.isChecked():
            choice = '3'
        elif self.Ans_Chk_D.isChecked():
            choice = '4'
        else:
            print('Input Answer')
            return
        self.pend = Questions(question=question, answer=choice, choice1=answer1, choice2=answer2, choice3=answer3, choice4=answer4)
        self.View_Update()
        print(model_to_dict(self.pend))
        self.FN3_Push.setEnabled(True)

    def Push_database(self):
        self.FN3_Push.setEnabled(False)
        self.pend.save()
        self.stack_.append(self.pend.id)
        if len(self.stack_):
            self.FN4_Undo.setEnabled(True)
        else:
            self.FN4_Undo.setEnabled(False)
        self.row_count += 1
        self.tableWidget.setRowCount(self.row_count)
        for col in range(len(self.remapper)):
            oneItem = QTableWidgetItem(str(model_to_dict(self.pend)[self.remapper[col]]))
            self.tableWidget.setItem(self.row_count - 1, col, oneItem)

    def Undo_operation(self):
        Questions.delete().where(Questions.id == self.stack_[-1]).execute()
        self.stack_.pop(-1)
        if len(self.stack_):
            self.FN4_Undo.setEnabled(True)
        else:
            self.FN4_Undo.setEnabled(False)
        self.row_count -= 1
        self.tableWidget.setRowCount(self.row_count)

    def __init__(self, parent=None):
        super(Main_ui, self).__init__(parent)
        self.setupUi(self)
        self.FN1_RLD_db.clicked.connect(self.Reload_database)
        self.FN2_Chk.clicked.connect(self.Chk_database)
        self.FN3_Push.clicked.connect(self.Push_database)
        self.FN4_Undo.clicked.connect(self.Undo_operation)
        self.Table_widget_init()
        self.Reload_database()


def run():
    db.connect()
    try:
        db.create_tables([Questions])
    except Exception as e:
        print(e)
        pass
    app = QApplication(sys.argv)
    main_window = Main_ui()
    main_window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run()