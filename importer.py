from qgmodel import *
import difflib
from playhouse.shortcuts import model_to_dict

all_ques = []

def chk_indb(question):
    score = 0
    suspect = ''
    for each in all_ques:
        tmp = difflib.SequenceMatcher(None, question, each).quick_ratio()
        if tmp > score:
            score = tmp
            suspect = each
    if score < 0.5:
        print('置信度{0}\n题目：{1}\n疑似：{2}'.format(score, question, suspect))
        if score<0.38:
            return True
        if input('保存:1，放弃:2') == '1':
            return True
        else:
            return False


def run():
    db.connect()
    cursor = Questions.select()
    for each in cursor:
        all_ques.append(each.question)
    question = ''
    choice = ['', '', '', '']
    ans = '1'
    cnt = 1

    with open('1.txt', 'r') as f:
        line = f.readline()
        while line:
            line = f.readline().strip()
            while line == '' or line.startswith('出题'):
                line = f.readline().strip()
            if line[0] == '答':
                ans = line[line.find('：') + 1:line.find('：') + 2]
                ans = ord(ans) - ord('A') + 1
                Q = Questions(question=question, answer=ans, choice1=choice[0], choice2=choice[1], choice3=choice[2], choice4=choice[3])
                print(model_to_dict(Q))
                if chk_indb(question):
                    all_ques.append(question)
                    Q.save()
                question = ''
                choice = ['', '', '', '']
                ans = '1'
                cnt = 1
            elif line[0].isdigit():
                question = line[line.find('、') + 1:]
                end = question.find('(推荐')
                if end != -1:
                    question = question[:end]
                end = question.find('(出题')
                if end != -1:
                    question = question[:end]
                end = question.find('出题:')
                if end != -1:
                    question = question[:end]
                end = question.find('出题：')
                if end != -1:
                    question = question[:end]
                end = question.find('（出题')
                if end != -1:
                    question = question[:end]
            elif line[0].isalpha():
                choice[cnt - 1] = line[line.find('、') + 1:]
                cnt += 1

if __name__ == '__main__':
    run()