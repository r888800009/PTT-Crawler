# PTT Crawler

一個練習網路爬蟲的小實驗，可以取出 PTT 文章中標題、內容與推文。

本專案為 [zake7749/PTT-Crawler](https://github.com/zake7749/PTT-Crawler) 的 fork，本 fork feature 如下:
- `parse_article()` 移除 try-catch block ，這使佇列系統(rq/celery)可以收集崩潰日誌、重新排程
- (WIP) 增加 pttweb 爬蟲，由於 ptt 討埨板有文章上限，未標記的文章會被移除，可透過鏡像站爬取備份
- [jwlin/ptt-web-crawler](https://github.com/jwlin/ptt-web-crawler) 會自行前處理移除換行資訊，如果需要這些資訊可能無法重新構造，
對於 ETL pipeline 較不友善。

## 已知 bug
- 目前文章只會爬取第一行文字的部分，可能造成爬取的資料不完整

## 使用方式

### 批量爬取
```python
crawler = PttCrawler()
crawler.crawl(board="欲爬取的看版名稱", start=StartIndex, end=EndIndex)
```
`start` 表示想從哪一頁開始爬取，`end` 則是爬到哪一頁時會停止，比方說想爬取八卦版的 90 ~ 100 頁，可以設定為：

```python
crawler.crawl(board="Gossiping", start=90, end=101)
```

### 單一頁面爬取

透過調用 `crawler.parse_article(url)` 可以爬取單一頁面，回傳值為包含文章資訊的`dictionary`

```python
crawler = PttCrawler()
result = crawler.parse_article("https://www.ptt.cc/bbs/Gossiping/M.1475542702.A.46A.html")
crawler.output("output_file_name", result)
```

### 指定模式爬取

設定參數`mode` (default all)，可以指定想要爬取的是**推文(up)**、**噓文(down)**、**一般回文(normal)** 或 **不指定(all)**

~~~python
mode = 'up' # 只爬取文章內的推文

# 批量爬取
crawler.crawl(board="Gossiping", start=90, end=101, mode=mode)

# 單一頁面爬取
result = crawler.parse_article("https://www.ptt.cc/bbs/Gossiping/M.1475542702.A.46A.html", mode)
crawler.output("output_file_name", result)
~~~

## 環境配置

主要基於 python2.7 (支援2.7以上版本)，開發，另外需配置好`bs4`、`requests`與`lxml`：

```terminal
pip install bs4
pip install requests
pip install lxml
```

## 資料格式

每爬完一整頁就會進行一次輸出，檔案格式為`json`:

```
{
    "Content": "文章內容",
    "Responses": [
        {
            "Content": "推文內容", 
            "Vote": "推文立場(箭頭、推、噓)", 
            "User": "推文 ID"
        }
    ],
    "Title": "文章標題",
    "Author": "文章作者",
    "UpVote": 推文總數,
    "NoVote": 箭頭總數,
    "DownVote": 噓文總數
}
```
