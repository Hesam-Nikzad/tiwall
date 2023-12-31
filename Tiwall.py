from bs4 import BeautifulSoup
import pandas as pd
import jdatetime
import datetime
import re
import os
import traceback
import asyncio
import aiohttp
import mysql.connector
from sqlalchemy import create_engine


class async_tiwall:
    def __init__(self):
        self.path = os.getcwd().replace('\\', '/')
        self.cnx = mysql.connector.connect(user='hessum', password='harchi', host='172.30.112.1', database='theaters')
        self.cursor = self.cnx.cursor()
        self.engine = create_engine('mysql+pymysql://hessum:harchi@172.30.112.1:3306/theaters')
        print('connected to the mysql')
        self.my_timeout = aiohttp.ClientTimeout(
            total=None, 
            sock_connect=3,
            sock_read=3,
            connect=3)

        self.client_args = dict(trust_env=True, timeout=self.my_timeout)

    async def find_links(self, pageNumber):

        def get_tasks(session):
            tasks = []
            for i in range(1, pageNumber+1):
                url = 'https://www.tiwall.com/showcase?filters=s:theater&p=%s' %i
                tasks.append(session.get(url))
            
            return tasks

        soups = []
        async with aiohttp.ClientSession() as session:
            tasks = get_tasks(session)
            responses = await asyncio.gather(*tasks)
            for response in responses:
                soups.append(BeautifulSoup(await response.text(), "html.parser"))

        pagesList = []
        for soup in soups:
            page = soup.find_all('a', class_='item-page')
            for link in page:
                pagesList.append('https://www.tiwall.com' + link['href'])

        query = "SELECT * FROM theater;"
        dfHistory = pd.read_sql(query, self.engine)
        #pagesList = [item for item in pagesList if item not in dfHistory.URL.to_list()]
        
        print(f"{len(pagesList)} links were found from {pageNumber} search pages")
        self.pagesList = pagesList

    def month2int(self, m):
        if m == 'فروردین':
            return 1
        elif m == 'اردیبهشت':
            return 2
        elif m == 'خرداد':
            return 3
        elif m == 'تیر':
            return 4
        elif m == 'مرداد':
            return 5
        elif m == 'شهریور':
            return 6
        elif m == 'مهر':
            return 7
        elif m == 'آبان':
            return 8
        elif m == 'آذر':
            return 9
        elif m == 'دی':
            return 10
        elif m == 'بهمن':
            return 11
        elif m == 'اسفند':
            return 12

    def crawl(self, soup, url):
        theater = {}

        # Title
        title = soup.find(class_='tooltip page-title').text.strip()
        theater['title'] = title

        # Price
        try:
            price = soup.find(class_='page-base-info-price').text.strip()
            price = price.split(',')[0].split('\xa0')[1]
            price = int(price)
            theater['price'] = price
        except:
            theater['price'] = 0

        # Location, Time, Duration 
        baseInfo = soup.find(class_='page-base-info')
        Bases = baseInfo.find_all('div')
        location = Bases[0].text.strip()
        theater['location'] = location
        
        time = Bases[2].get_text(strip=True).split('|')
        hour = time[0].split(':')
        hour = [int(item) for item in hour if item.isdigit()]
        hour = jdatetime.time(*hour)
        theater['hour'] = hour

        duration = time[1].split(' ')
        duration = [int(item) for item in duration if item.isdigit()]
        if duration[0] >= 5 and len(duration) == 1:
            hh = 0
            mm = duration[0]
        elif duration[0] < 5 and len(duration) == 1:
            hh = duration[0]
            mm = 0
        else:
            hh = duration[0]
            mm = duration[1]
        
        duration = jdatetime.time(hh, mm)
        theater['duration'] = duration

        # Date
        date = soup.find('div', class_='theater-date').text.strip()
        ind = date.find('تا')
        date = date[ind + 3:]
        date = date.split(' ')
        try:
            day = int(date[0])
            month = self.month2int(date[1])
        except:
            date.pop(0)
            day = int(date[0])
            month = self.month2int(date[1])
        
        today = jdatetime.date.today()
        if len(date) == 3:
            year = int(date[2])
        elif month < today.month and today.month >= 10:
            year = today.year + 1
        else:
            year = today.year
        date = jdatetime.date(year, month, day).togregorian()
        theater['date'] = date

        # City, Category, and Group
        infos = soup.find(class_='filters detail-tags clear-right tags')
        infos = infos.find_all('div')
        infos.pop()
        theater['city'] = 'نامعلوم'
        theater['genre'] = 'نامعلوم'
        theater['category'] = 'بزرگسال'
        
        for info in infos:
            cat = info.find('h6').text.strip()
            inf = info.find_all('a')
            information = ''
            for i in inf:
                information += i.text.strip() + ', '

            information = information[:-2]

            if cat == 'شهر':
                theater['city'] = information
            elif cat == 'سبک':
                theater['genre'] = information
            elif cat == 'دسته‌بندی':
                theater['cat'] = information

        # Director
        infoFirst = soup.find(class_='page-info-section first')
        try:
            director = infoFirst.find('label', string=lambda text: 'کارگردان' in text).parent.text.strip()
            director = director.split(':')[1].strip()   
            theater['director'] = director
        except:
            theater['director'] = 'نامعلوم'

        # Writer
        try:
            writer = infoFirst.find('label', string=lambda text: 'نویسنده' in text).parent.text.strip()
            writer = writer.split(':')[1].strip()
        except:
            writer = 'نامعلوم'
        
        theater['playwright'] = writer

        # Rate
        rating = soup.find('div', class_ = 'avg-rating tooltip')
        if rating == None:
            rate = 0
            number = 0
        else:
            rate = rating['title']
            pattern = r'امتیاز ([\d٫]+)'
            rate = float(re.search(pattern, rate).group(1).replace('٫', '.'))
            
            voters = rating.find_all('div')[0].text.strip()
            voters = [int(item) for item in voters if item.isdigit()]
            number = 0
            for i in voters: number = number*10 + i
        
        theater['rate'] = rate
        theater['voters'] = number

        # Cast
        try:
            cast = infoFirst.find('label', string=lambda text: 'بازیگران' in text).parent.text.strip()
            cast = cast.split(':')[1].strip()
            theater['cast'] = cast
        except:
            theater['cast'] = 'نامعلوم'

        theater['url'] = url

        clean_theater = {}
        for key, value in theater.items():
            if isinstance(value, str):
                clean_theater[key] = value.replace('\u200c', '')
            else:
                clean_theater[key] = value
        return clean_theater

    async def crawl_pages(self):

        def get_tasks(session):
            tasks = []
            for url in self.pagesList:
                tasks.append(session.get(url))
            
            return tasks 

        self.theatersList = []

        async with aiohttp.ClientSession(**self.client_args) as session:
            tasks = get_tasks(session)
            try:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
            except:
                print('Timeout')
            print('All webpages are downloded')
            for response, url in zip(responses, self.pagesList):
                try:
                    self.theatersList.append(self.crawl(BeautifulSoup(await response.text(), "html.parser"), url))
                except:
                    with open(self.path + '/error.txt', 'a') as file:
                        file.write('%s \n' %(traceback.format_exc()))
        
        print('All theaters webpages are crawled')
        return self.theatersList
    
    def to_DB(self):
        query = "SELECT * FROM theater;"
        dfHistory = pd.read_sql(query, self.engine)
        df = pd.DataFrame(self.theatersList)
        df = df.loc[~df.url.isin(dfHistory.URL)]
        print(f'{len(df)} theaters added to the database')
        df.to_sql(name='theater', con=self.engine, if_exists='append', index=False, chunksize=1000)

    def save(self):
        df = pd.DataFrame(self.theatersList)
        df['title'] = df.apply(lambda row: f'=HYPERLINK("{row["url"]}","{row["title"]}")', axis=1)
        df.drop(columns='url', axis=1, inplace=True)
        df.to_excel(self.path + '/theaters.xlsx', index=False)

        print(f'The theaters information saved on: {self.path}')

    def date_correction(self, url):
        
        query = 'SELECT * FROM comments WHERE theater_url="%s";' %url
        commentsDates = pd.read_sql(query, self.engine).sort_values(by='comment_date', ascending=False)
        commentsDates.sort_values(by='comment_date', ascending=False, inplace=True)
        lastCommentDate = commentsDates.iloc[0]['comment_date']
        commentYear = lastCommentDate.year

        query = 'SELECT date FROM theater WHERE URL="%s";' %url
        theaterDate = pd.read_sql(query, self.engine).loc[0, 'date']
        
        month = theaterDate.month
        day = theaterDate.day
        deltaDate = datetime.timedelta(days=0)
        
        if lastCommentDate.date() - datetime.date(commentYear, month, day) >= deltaDate:
            theaterDate = datetime.date(commentYear, month, day)
        
        elif lastCommentDate.date() - datetime.date(commentYear + 1, month, day) >= deltaDate:
            theaterDate = datetime.date(commentYear + 1, month, day)
        
        elif lastCommentDate.date() - datetime.date(commentYear - 1, month, day) >= deltaDate:
            theaterDate = datetime.date(commentYear - 1, month, day)
        
        updateQuery = "UPDATE theater SET date = '%s' WHERE URL = '%s';" %(theaterDate, url)
        self.cursor.execute(updateQuery)
        self.cnx.commit()        

    def correcting_dates(self):

        query = "SELECT * FROM theater;"
        dfHistory = pd.read_sql(query, self.engine)
        pagesList = dfHistory.URL.to_list()
        
        for theater in pagesList:
            print(theater)
            try:
                self.date_correction(theater)
            except:
                pass


if __name__ == '__main__':
    Tiwall = async_tiwall()
    #asyncio.run(Tiwall.find_links(1))
    #asyncio.run(Tiwall.crawl_pages())
    #Tiwall.to_DB()
    #Tiwall.save()
    Tiwall.correcting_dates()