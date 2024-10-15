# -*- coding: UTF-8 -*-

import asyncio
import json
import requests
import time

from bs4 import BeautifulSoup
from bs4.element import NavigableString

from pyppeteer import launch

def main():
    # 我們不 main 直接做 test
    test_parse_article()

    #crawler = PttCrawler()
    #crawler.crawl(board="Gossiping", start=10001, end=11000)

    #res = crawler.parse_article("https://www.ptt.cc/bbs/Gossiping/M.1119928928.A.78A.html")
    #crawler.output("test", res)


class PttCrawler:

    root = "https://www.ptt.cc/bbs/"
    main = "https://www.ptt.cc"
    gossip_data = {
        "from":"bbs/Gossiping/index.html",
        "yes": "yes"
    }

    def __init__(self):
        self.session = requests.session()
        requests.packages.urllib3.disable_warnings()
        self.session.post("https://www.ptt.cc/ask/over18",
                           verify=False,
                           data=self.gossip_data)

    def articles(self, page):
        '''文章內容的生成器
        Args:
            page: 頁面網址
        Returns:
            文章內容的生成器
        '''

        res  = self.session.get(page, verify=False)
        soup = BeautifulSoup(res.text, "lxml")

        for article in soup.select(".r-ent"):
            try:
                yield self.main + article.select(".title")[0].select("a")[0].get("href")
            except:
                pass # (本文已被刪除)

    def pages(self, board=None, index_range=None):
        '''頁面網址的生成器
        Args:
            board: 看板名稱
            index_range: 文章頁數範圍
        Returns:
            網址的生成器
        '''
        
        target_page = self.root + board + "/index"

        if range is None:
            yield target_page + ".html"
        else:
            for index in index_range:
                yield target_page + str(index) + ".html"

    def parse_article(self, url, mode):
        '''解析爬取的文章，整理進dict
        Args:
            url: 欲爬取的PTT頁面網址
            mode: 欲爬取回文的模式。全部(all)、推文(up)、噓文(down)、純回文(normal)
        Returns:
            article: 爬取文章後資料的dict
            
        '''
        raw  = self.session.get(url, verify=False)
        return self.parse_article_no_request(raw.text, mode)
        
    def parse_article_no_request(self, text, mode):
        '''同 parse_article，但是這個函數不主動從網頁爬取資料，直接傳入爬取的文字
        '''
        # 處理mode標誌
        if mode == 'all':
            mode = 'all'
        elif mode == 'up':
            mode = u'推'
        elif mode == 'down':
            mode = u'噓'
        elif mode == 'normal':
            mode = '→'
        else:
            raise ValueError("mode變數錯誤", mode)

        soup = BeautifulSoup(text, "lxml")

        article = {}

        # 取得文章作者與文章標題
        self.get_title_and_author(soup, article)

        # 取得內文
        self.get_content(soup, article)

        # 處理回文資訊
        upvote = 0
        downvote = 0
        novote = 0
        response_list = []

        push_list = self.get_push_list(soup)
        for response_struct in push_list:

            #跳脫「檔案過大！部分文章無法顯示」的 push class
            if self.push_list_skip_condition(response_struct):
                continue

            response_dic = {}
            
            # 根據不同的mode去採集response
            if mode == 'all':
                self.parse_response(response_struct, response_dic)
                response_list.append(response_dic)
                
                if response_dic["Vote"] == u"推":
                    upvote += 1
                elif response_dic["Vote"] == u"噓":
                    downvote += 1
                else:
                    novote += 1
            else:
                response_dic = self.parse_response(response_struct, response_dic)

                if response_dic["Vote"] == mode:
                    response_list.append(response_dic)
                    
                    if mode == u"推":
                        upvote += 1
                    elif mode == u"噓":
                        downvote += 1
                    else:
                        novote += 1

        article["Responses"] = response_list
        article["UpVote"] = upvote
        article["DownVote"] = downvote
        article["NoVote"] = novote

        return article

    def push_list_skip_condition(self, response_struct):
        return "warning-box" in response_struct['class']

    def get_push_list(self, soup):
        return soup.select(".push")

    def get_content(self, soup, article):
        content = ""
        # BUG: 這個 Parsing 方式只會得到其中一行，因為有時候會有多行，就不會得到正確的內文
        # NOTE: 如果要進行修改，也務必檢查 PttWebCrawler.get_content 的內容
        for tag in soup.select("#main-content")[0]:
            if type(tag) is NavigableString and tag !='\n':
                content += tag
                break
        article["Content"] = content

    def get_title_and_author(self, soup, article):
        article["Author"] = soup.select(".article-meta-value")[0].contents[0].split(" ")[0]
        article["Title"]  = soup.select(".article-meta-value")[2].contents[0]

    def parse_response(self, response_struct, response_dic):
        """response_dic 回傳內容
        """
        response_dic["Content"] = response_struct.select(".push-content")[0].contents[0][2:]
        response_dic["Vote"]  = response_struct.select(".push-tag")[0].contents[0][0]
        response_dic["User"]  = response_struct.select(".push-userid")[0].contents[0]

    def output(self, filename, data):
        '''爬取完的資料寫到json文件
        Args:
            filename: json檔的文件路徑
            data: 爬取完的資料
        '''

        with open(filename+".json", 'wb+') as op:
            op.write(json.dumps(data, indent=4, ensure_ascii=False).encode('utf-8'))
            print('爬取完成~', filename + '.json', '輸出成功！')

        
    def crawl(self, board="Gossiping", mode='all', start=1, end=2, sleep_time=0.5):
        '''爬取資料主要接口
        Args:
            board: 欲爬取的看版名稱
            mode: 欲爬取回文的模式。全部(all)、推文(up)、噓文(down)、純回文(normal)
            start: 從哪一頁開始爬取
            end: 爬取到哪一頁停止
            sleep_time: sleep間隔時間
        '''

        crawl_range = range(start, end)

        for page in self.pages(board, crawl_range):
            res = []
            
            for article in self.articles(page):
                res.append(self.parse_article(article, mode))
                time.sleep(sleep_time)
            
            print(u"已經完成 %s 頁面第 %d 頁的爬取" %(board, start))
            self.output(board + str(start), res)
            
            start += 1

class PttWebCrawler(PttCrawler):

    def parse_article(self, url, mode):
        text = self.open_url_sync(url)
        return self.parse_article_no_request(text, mode)
    
    def open_url_sync(self, url):
        return asyncio.run(self.open_url(url))

    async def open_url(self, url):
        browser = await launch()
        page = await browser.newPage()
        await page.goto(url)
        
        # 如果有 button 就點擊
        button = await page.xpath('//div[contains(text(), "載入全部")]/parent::button')
        if button:
            print('有 button 就點擊')
            # TODO: 這目前點擊後不會有效果，需要進一步確認
            await button[0].click()

        # 回傳 html
        html_doc = await page.content()
        await browser.close()
        return html_doc

    def get_content(self, soup, article):
        # BUG: 這個為了維持介面一致，我們採用 PttCrawler.get_content 的方式，也因此每次只會爬取一行
        content = ""
        for tag in soup.find("div", itemprop="articleBody"):
            # check class is "" and tag is span
            if len(tag.get("class")) == 0 and tag.name == "span" and tag !='\n':
                content += tag.text
                break
        article["Content"] = content

    def get_title_and_author(self, soup, article):
        # h1 title mt-2
        article["Title"] = soup.find_all("h1", class_="title")[0].text.strip()
        article["Author"] = soup.find("span", itemprop="name").text

    def get_push_list(self, soup):
        print(soup.find_all("div", itemprop="comment"))
        return soup.find_all("div", itemprop="comment")

    def parse_response(self, response_struct, response_dic):
        """response_dic 回傳內容
        """
        response_dic["Content"] = response_struct.find("div", itemprop="text").text
        response_dic["Vote"]  = response_struct.find("div", class_="e7-left").text
        response_dic["User"]  = response_struct.find("span", itemprop="name").text

    def push_list_skip_condition(self, response_struct):
        # don't care
        return False

def test_parse_article():
    article_list = [
        'Gossiping/M.1694692614.A.53F',
        'Linux/M.1117722226.A.5BB',
        'Gossiping/M.1528987377.A.B29',
        'Gossiping/M.1694692327.A.BC3',
    ]
    
    test_mode = [
        'all', 
        #'up',
        #'down',
        #'normal',
    ]

    for article in article_list:
        for mode in test_mode:
            crawler = PttCrawler()
            url = f"https://www.ptt.cc/bbs/{article}.html"
            print(url)
            ptt_result = crawler.parse_article(url, mode=mode)

            crawler = PttWebCrawler()
            url = f"https://www.pttweb.cc/bbs/{article}"
            print(url)
            pttweb_result = crawler.parse_article(url, mode=mode)
            for key in ptt_result:
                debug_print(ptt_result, pttweb_result, key)
                assert ptt_result[key] == pttweb_result[key], f"article: {article}, mode: {mode}, key: {key}"

def debug_print(ptt_result, pttweb_result, key):
    if key == "Content":
        print("=== content ptt ===")
        print(ptt_result[key])
        print("=== content pttweb ===")
        print(pttweb_result[key])
    else:
        print(key, ptt_result[key], pttweb_result[key])

if __name__ == '__main__':
    main()
