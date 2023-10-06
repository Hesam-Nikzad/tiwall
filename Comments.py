from bs4 import BeautifulSoup
import mysql.connector
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import pandas as pd
import re
import jdatetime


class tiwall_comments:
    def __init__(self):
        self.path = os.getcwd().replace('\\', '/')
        self.cnx = mysql.connector.connect(user='hessum', password='harchi', host='localhost', database='theaters')
        print('connected to the mysql')
        self.driver = webdriver.Chrome()
        self.months = {'فروردین': 1, 'اردیبهشت': 2, 'خرداد': 3, 'تیر': 4, 'مرداد': 5, 'شهریور': 6,
                'مهر': 7, 'آبان': 8, 'آذر': 9, 'دی': 10, 'بهمن': 11, 'اسفند': 12}
        self.path2save = 'D:/EE/My Project/Tiwall/Webpages/'

    def Theaters_List(self):
        query = "SELECT * FROM theater;"
        dfHistory = pd.read_sql(query, self.engine)
        self.theatersList = dfHistory.URL.tolist()

    def openUrl(self, url):
        fileName = url[len('https://www.tiwall.com/p/'):-1]
        if os.path.exists(self.path2save + fileName + '.html'):
            with open(f'{self.path2save}{fileName}.html', 'r', encoding='utf-8') as file:
                self.soup = BeautifulSoup(file.read(), 'html.parser')
        else:
            self.selen(url)

    def selen(self, url):
        self.driver.get(url)
        # Scroll down to load more comments
        while True:
            try:
                load_more_button = self.driver.find_element(By.ID, "load-more")
                load_more_button.click()
                time.sleep(2)  # Wait for new comments to load
            except Exception as e:
                break
        
        html_content = self.driver.page_source
        self.soup = BeautifulSoup(html_content, 'html.parser')
        # Save the soup object to a file
        html_content = str(self.soup)
        fileName = url[len('https://www.tiwall.com/p/'):-1]
        with open(f'{self.path2save}{fileName}.html', 'w', encoding='utf-8') as file:
            file.write(html_content)
    
    def crawl(self, url):

        comments = self.soup.find_all('div', class_=lambda x: x and 'wall-post browsable' in x)
        for comment in comments:
        
            cmnt = comment.find('div', class_="clear wallItemBody")
            id = cmnt.get('id')
            id = re.search(r'(\d+)', id).group(1)
            text = cmnt.text.strip()
            
            # Extract Persian date components
            date_element = comment.find('span', class_="tooltip", title=True)['title']
            date_element = date_element.split()
            day = int(date_element[1])
            month = self.months.get(date_element[2])
            year = int(date_element[3])
            time_str = date_element[5]
            date_element = jdatetime.datetime(year, month, day, hour=int(time_str.split(':')[0]), minute=int(time_str.split(':')[1]))
            
            username = comment.find('a', class_="user").text
            
            print(date_element.togregorian())
            print(id)
            print(username)
            print(text)
            



url = 'https://www.tiwall.com/p/zirzaminiha/'

Comments = tiwall_comments()
#Comments.Theaters_List()
Comments.openUrl(url)
Comments.crawl(url)