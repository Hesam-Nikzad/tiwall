import requests
from bs4 import BeautifulSoup
import pandas as pd
import jdatetime
import re
import os


class tiwall:
    def __init__(self):
        self.path = os.getcwd().replace('\\', '/')

    def Pages(self, pageNumber):
        url = 'https://www.tiwall.com/showcase?filters=s:theater&p=%s' %pageNumber
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        pages = soup.find_all('a', class_='item-page')
        pagesList = []
        
        for page in pages:
            pagesList.append('https://www.tiwall.com/' + page['href'])
        
        self.pagesList = pagesList

        return self.pagesList

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

    def crawl(self, url):
        theater = {}
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

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
            theater['price'] = 'نامعلوم'

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
        date = jdatetime.date(year, month, day)
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

    def find_links(self, pageNumber):
        pages = []
        for i in range (1, pageNumber+1):
            pages.extend(self.Pages(i))
            print('Crawling search page number %s finished and %s links added' %(i, len(pages)))
        
        self.pages = list(set(pages))

    def crawl_pages(self):
        self.theatersList = []
        for page in self.pages:
            try:
                theater = self.crawl(page)
                print(theater)
                self.theatersList.append(theater)
            
            except Exception as e:
                with open(self.path + '/error.txt', 'a') as file:
                    file.write('%s, %s \n' %(page, e))

        return self.theatersList

    def save(self):
        df = pd.DataFrame(self.theatersList)
        df['title'] = df.apply(lambda row: f'=HYPERLINK("{row["url"]}","{row["title"]}")', axis=1)
        df.drop(columns='url', axis=1, inplace=True)
        df.to_excel(self.path + '/theaters.xlsx', index=False)


if __name__ == '__main__':
    Tiwall = tiwall()
    Tiwall.find_links(1)
    Tiwall.crawl_pages()
    Tiwall.save()