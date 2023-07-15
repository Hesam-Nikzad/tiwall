import requests
from bs4 import BeautifulSoup
import pandas as pd
import jdatetime
import re
import os

def Pages(pageNumber):
    url = 'https://www.tiwall.com/showcase?filters=s:theater&p=%s' %pageNumber
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    pages = soup.find_all('a', class_='item-page')
    pagesList = []
    
    for page in pages:
        pagesList.append('https://www.tiwall.com/' + page['href'])
    
    return pagesList

def month2int(m):
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

def crawl(url):
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
    location = location.replace('\u200c', '')
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
        month = month2int(date[1])
    except:
        date.pop(0)
        day = int(date[0])
        month = month2int(date[1])
    
    today = jdatetime.date.today()
    if len(date) == 3:
        year = int(date[2])
    elif month < today.month and today.month >= 10:
        year = today.year + 1
    else:
        year = today.year
    date = jdatetime.date(year, month, day)
    theater['date'] = date

    # Director
    infoFirst = soup.find(class_='page-info-section first')
    try:
        director = infoFirst.find('label', string=lambda text: 'کارگردان' in text).parent.text.strip()
        director = director.split(':')[1].strip()
        director = director.replace('\u200c', '')    
        theater['director'] = director
    except:
        theater['director'] = 'نامعلوم'

    # Writer
    try:
        writer = infoFirst.find('label', string=lambda text: 'نویسنده' in text).parent.text.strip()
        writer = writer.split(':')[1].strip()
        writer = writer.replace('\u200c', '')
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
        cast = cast.replace('\u200c', '')
        theater['cast'] = cast
    except:
        theater['cast'] = 'نامعلوم'

    theater['url'] = url

    return theater

path = os.getcwd().replace('\\', '/')

pages = []
for i in range (1, 5):
    print('Crawling search page number %s started' %i)
    pages.extend(Pages(i))
pages = list(set(pages))
print(len(pages))

theatersList = []
for page in pages:
    #page = 'https://www.tiwall.com//p/khatoun2'
    try:
        theater = crawl(page)
        print(theater)
        theatersList.append(theater)
    
    except Exception as e:
        with open(path + '/error.txt', 'a') as file:
            file.write('%s, %s \n' %(page, e))
    #break

df = pd.DataFrame(theatersList)
df['title'] = df.apply(lambda row: f'=HYPERLINK("{row["url"]}","{row["title"]}")', axis=1)
df.drop(columns='url', axis=1, inplace=True)
df.to_excel(path + '/theaters1.xlsx', index=False)