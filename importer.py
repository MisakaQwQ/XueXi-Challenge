from qgmodel import *
import difflib
from playhouse.shortcuts import model_to_dict

all_ques = []

def chk_indb(question):
    return True
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
    try:
        db.create_tables([Questions])
    except Exception as e:
        print(e)
        pass
    cursor = Questions.select()
    for each in cursor:
        all_ques.append(each.question)
    question = ''
    choice = ['', '', '', '']
    ans = '1'
    cnt = 1

    with open('2.txt', 'r', encoding='utf-8') as f:
        while True:
            tmp = f.readline()
            if tmp.strip() == 'EOF':
                break
            question = tmp.strip()
            choice = ['', '', '', '']
            choicecnt = int(f.readline().strip())
            for _ in range(choicecnt):
                choice[_] = f.readline().strip()
            ans = f.readline().strip()
            ans = ord(ans) - ord('A') + 1
            Q = Questions(question=question, answer=ans, choice1=choice[0], choice2=choice[1], choice3=choice[2],
                          choice4=choice[3])
            print(model_to_dict(Q))
            Q.save()


if __name__ == '__main__':
    # exit(0)
    run()