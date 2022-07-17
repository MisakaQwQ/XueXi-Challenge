import time
import random

import requests
from bs4 import BeautifulSoup
import re
import lxml
import html5lib


def run():
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
    }
    MAIN_DOMAIN = 'https://www.3gmfw.cn'
    SORT_URL = MAIN_DOMAIN + '/article/tag.asp?name=%D1%A7%CF%B0%C7%BF%B9%FA%CC%E2%BF%E2'
    with open('2.txt', 'a', encoding='utf-8') as f:
        for page in range(175, 200):
            print('Page %d' % page)
            page_url = SORT_URL + '&page=%d' % page
            headers['referer'] = page_url
            response = requests.get(page_url, headers=headers)
            time.sleep(random.random())
            soup = BeautifulSoup(response.content.decode('gbk'), 'html5lib')
            main_content = soup.find_all(class_='xs-card-content-15')[1]
            hrefs = main_content.find_all('a')
            for idx, href in enumerate(hrefs):
                print('Index %d' % idx)
                if href.get('title'):
                    question_url = MAIN_DOMAIN + href.get('href')
                    response = requests.get(question_url, headers=headers)
                    time.sleep(random.random())
                    soup = BeautifulSoup(response.content.decode('gbk'), 'html5lib')
                    main_content = soup.find_all('div', style='font-size: 15px;')[0]
                    txts = main_content.text.split('\n')
                    question = ''
                    choice = []
                    answer = ''
                    for txt in txts:
                        tmp = txt.strip()
                        if tmp:
                            if not question:
                                question = tmp
                            elif re.match(r'[A-Z].*', tmp):
                                choice.append(tmp[2:])
                            elif re.match(r'(正确)?答案[:：][A-Z]', tmp):
                                answer = re.findall('正?确?答案[:：]([A-Z]*)', tmp)[0]
                    if choice and len(answer) == 1:
                        f.writelines('%s\n' % question)
                        f.writelines('%d\n' % len(choice))
                        f.writelines('%s\n' % '\n'.join(choice))
                        f.writelines('%s\n' % answer)
                        f.flush()
                        print('%s\n%s\n%s' % (question, choice, answer))

    # for article_id in range(543223, 543239 + 1):
    #     for page in range(1, 40):
    #         if page == 1:
    #             url = URL + f'{article_id}.html'
    #             response = requests.get(url)
    #             soup = BeautifulSoup(response.content.decode('gbk'), 'html5lib')
    #             loc = soup.find_all(class_='textpage')
    #             txt = loc[0].previous_sibling.text
    #             print(txt)
    #             with open('1.txt', 'a', encoding='utf-8')as f:
    #                 f.writelines(txt)
    #         else:
    #             url = URL + f'{article_id}_{page}.html'
    #             response = requests.get(url)
    #             soup = BeautifulSoup(response.content.decode('gbk'), 'html5lib')
    #             if '提醒您！非常抱歉，您要查看的网页当前已过期' in response.content.decode('gbk'):
    #                 break
    #             loc = soup.find_all(id='mainNewsContent')
    #             lst = loc[0].children
    #             for each in lst:
    #                 if bool(each.string and each.string.strip()):
    #                     txt = each.string.strip()
    #                     if '3G免费网' in txt or '学习强国' in txt or '的相关资源如下：' in txt:
    #                         continue
    #                     pass
    #                     print(txt)
    #                     with open('1.txt', 'a', encoding='utf-8')as f:
    #                         f.writelines(txt+'\n')
    #                 pass


if __name__ == '__main__':
    run()