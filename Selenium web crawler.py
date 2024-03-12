from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import numpy as np
from itertools import chain
import re
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm 
import time
from datetime import datetime, timedelta
from geotext import GeoText
from langdetect import detect_langs
from countrygroups import EUROPEAN_UNION
import pycountry
import math
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



#0) Setup
options = webdriver.ChromeOptions()
options.page_load_strategy = 'eager'
driver = webdriver.Chrome(options=options)
driver.get('https://www.linkedin.com')

#1) Manual navigation to job posts


#2) functions
def time_adjust(x):
    if 'year' in x or 'years' in x:
        ret=datetime.now()-timedelta(days=365*float(re.findall(r'\d+', str(x))[0]))
    elif 'month' in x or 'months' in x:
        ret=datetime.now()-timedelta(days=30*float(re.findall(r'\d+', str(x))[0]))
    if 'week' in x or 'weeks' in x:
        ret=datetime.now()-timedelta(weeks=float(re.findall(r'\d+', str(x))[0]))
    elif 'days' in x or 'day' in x:
        ret=datetime.now()-timedelta(days=float(re.findall(r'\d+', str(x))[0]))
    elif 'hour' in x or 'hours' in x:
        ret=datetime.now()-timedelta(hours=float(re.findall(r'\d+', str(x))[0]))
    elif 'minutes' in x or 'minute' in x:
        ret=datetime.now()-timedelta(minutes=float(re.findall(r'\d+', str(x))[0]))        
    return ret

def cities(x):
    city=GeoText(x).cities
    if len(set(city))>1 and city or len(city)==0:
        city='Error'
    else:
        city=city[0]
    return city

def scientist(x):
    if 'scientist' in x.lower():
        ret=1
    elif 'analyst' in x.lower():
        ret=0
    else:
        ret=-1
    return ret

def is_on_site(info):
    if 'On-site' in info:
        x=1
    elif 'Hybrid' in info:
        x=0
    elif 'Remote' in info:
        x=-1
    else:
        x=-2
    return x

def country_search():
    flag=True
    count=0
    country_bug_count=0
    while flag:
        try:
            search_bar= driver.find_elements(By.CLASS_NAME,'jobs-search-box__text-input')
            search_bar=search_bar[3]
            search_bar.clear()
            search_bar.send_keys(country.lower())
            driver.find_element(By.CLASS_NAME, "jobs-search-box__submit-button").click()
            time.sleep(4)
            if country not in driver.find_element(By.CLASS_NAME, "jobs-search-results-list__text").text:
                search_bar= driver.find_elements(By.CLASS_NAME,'jobs-search-box__text-input')
                search_bar=search_bar[3]
                search_bar.clear()
                search_bar.send_keys(country)
                driver.find_element(By.CLASS_NAME, "jobs-search-box__submit-button").click()
                time.sleep(4)
            if country not in driver.find_element(By.CLASS_NAME, "jobs-search-results-list__text").text:
                country_bug_count=country_bug_count+1
                for i in range(0,30):
                    time.sleep(1)
                driver.refresh()
                if country_bug_count!=8:
                    continue
            flag=False
            time.sleep(3)
        except Exception as e:
            print(e)
            for i in range(0,30):
                time.sleep(1)
            driver.refresh()
            count=count+1
            if count==8:
                flag=False
                
                
def info_blocks_error_check():
    global current_batch
    global count
    global info_blocks
    global final_page
    if pages!=page:
        count=0
        flag=True
        while flag:
            if len(info_blocks)<25:
                driver.get(current_link+str(page*25))
                try:
                    info_blocks=WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "scaffold-layout__list-container")))
                    info_blocks= info_blocks.find_elements(By.CLASS_NAME,"jobs-search-results__list-item")
                    try:
                        info_blocks[0].click()
                    except:
                        info_blocks=driver.find_element(By.CLASS_NAME, "scaffold-layout__list-container")
                        info_blocks= info_blocks.find_elements(By.CLASS_NAME,"jobs-search-results__list-item")
                except:
                    for i in range(0,10):
                        time.sleep(1)
                
                count=count+1
                if count==3:
                    final_page=True
                    flag=False
            else:
                flag=False
    
    flag=True
    count=0
    while flag:
        current_batch=pd.Series(index=range(0,25),dtype=object)
        restart=False
        try:
            for num,block in enumerate(info_blocks):
                driver.execute_script("arguments[0].scrollIntoView(true);", block)
                current_batch.loc[num]=block.find_element(By.TAG_NAME,'a').get_attribute('href')
            if current_batch.equals(last_batch):
                restart=True
                break
            else:
                flag=False
        except:
            
                
        if restart:
            refresh_count=0
            refresh_flag=True
            while refresh_flag:
                driver.get(current_link+str(page*25))
                try:
                    info_blocks=WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "scaffold-layout__list-container")))
                    info_blocks= info_blocks.find_elements(By.CLASS_NAME,"jobs-search-results__list-item")
                    try:
                        info_blocks[0].click()
                    except:
                        info_blocks=driver.find_element(By.CLASS_NAME, "scaffold-layout__list-container")
                        info_blocks= info_blocks.find_elements(By.CLASS_NAME,"jobs-search-results__list-item")
                    refresh_flag=False
                except:
                    refresh_count=refresh_count+1
                    if refresh_count>4:
                        refresh_flag=False
                        continue
                    for i in range(0,10):
                        time.sleep(1)
                
        count=count+1
        if count==3:
            flag=False

                

#3) web scraping links
countries=EUROPEAN_UNION.names
countries.append('Norway')
countries.append('Finland')
countries.append('Switzerland')

last_batch=pd.Series(dtype=object)
job_counts=pd.Series()
jobs=pd.DataFrame(columns=['title','company','city','country','post time','applicants','description','on_site','raw_location','page','link'])
for ind_country,country in tqdm(enumerate(countries)):
    
    #3.1) Searching by country and errors around it
    country_search()
    
    #3.2) Extracting a country specific link for page turning
    current_link=driver.current_url
    current_link=current_link+'&start='
    
    #3.3) Getting a count of pages, if there's an error maximum possible is taken
    try:
        job_count=float(re.findall(r'\d+', driver.find_element(By.CLASS_NAME,'jobs-search-results-list__subtitle').text)[0])
        job_counts.loc[country]=job_count
    except:
        job_count=40*25
    pages=int(job_count/25)
    
    #3.4) Loop across pagees
    final_page=False
    for page in range(0,min(pages+1,41)): 
        
        #3.4.1) If break in case of early stopping of page turning
        if final_page:
            break
        if page>0:
            driver.get(current_link+str(page*25))
            
        #3.4.2) Check in case of error
        flag=True
        count=0
        while flag:
            try:
                driver.find_element(By.CLASS_NAME,'jobs-search-no-results__reload').click()
                time.sleep(1)
                driver.find_element(By.CLASS_NAME,'jobs-search-no-results__reload')
                for i in range(20):
                    time.sleep(1)
                count=count+1
                if count==10:
                    flag=False
            except:
                flag=False
        
        #3.4.3) Getting the job links within the page and checking for errors. last_batch series is for next error check
        time.sleep(1)
        
        try:
            info_blocks=WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "scaffold-layout__list-container")))
            info_blocks= info_blocks.find_elements(By.CLASS_NAME,"jobs-search-results__list-item")
        except:
            info_blocks=[]
        
        info_blocks_error_check()
        last_batch=current_batch.copy()
                    
        #3.4.4) Adding things to final frame
        jobs=pd.concat([jobs,pd.DataFrame(index=range(len(current_batch)),columns=jobs.columns)],axis=0,ignore_index=True)
        jobs.loc[len(jobs)-len(current_batch):,'link']=current_batch.values
        jobs.loc[len(jobs)-len(current_batch):,'country']=country
        jobs.loc[len(jobs)-len(current_batch):,'page']=page        

#4) Gathering data from the gathered links. Loop start
jobs= jobs[jobs['link'].notna()]
jobs=jobs.drop_duplicates()

for ind,link in tqdm(zip(jobs.index,jobs['link']),total=len(jobs)):
    #4.1) While loop with try to deal with all unaccounted errors
    main_while_flag=True
    while main_while_flag:
        try:
            driver.get(link)

            #4.1.1) Waiting for button to appear as a measure of loaded page, then checking whether job post is dead
            loop_flag=True
            skip=False
            while loop_flag:
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'jobs-description__footer-button')))
                    loop_flag=False
                    try:
                        if 'No longer accepting applications'==driver.find_element(By.CLASS_NAME,'artdeco-inline-feedback__message').text:
                            loop_flag=False
                            skip=True
                            jobs.loc[ind,'dead']=True 
                            continue
                    except:
                        None
                except:
                    try:
                        if 'No longer accepting applications'==driver.find_element(By.CLASS_NAME,'artdeco-inline-feedback__message').text:
                            loop_flag=False
                            skip=True
                            jobs.loc[ind,'dead']=True 
                            continue
                    except:
                        None
                    driver.get(link)
            if skip:
                main_while_flag=False
                continue

            #4.1.2) Getting table of various info (location, company, reposted or not and applicant amount. While loop in case of slow loading. meta count in case of overly consistent unkown type of error
            info=driver.find_element(By.CLASS_NAME,"job-details-jobs-unified-top-card__primary-description-container").text.split('·')
            count=0
            meta_count=0
            flag=True
            while (len(info)<4 and flag):
                try:
                    if 'year' in info[2]:
                        flag=False
                except:
                    None
                time.sleep(0.5)
                info=driver.find_element(By.CLASS_NAME,"job-details-jobs-unified-top-card__primary-description-container").text.split('·')
                count=count+1
                if count==40:
                    meta_count=meta_count+1
                    driver.get(link)
                    count=0
                    if meta_count==4:
                        flag=False

            #4.1.3) Getting job title, while loop in case of error. While stop in case of persistent error. This part of website is less prone to weird errors unlike the info part above hence page is reseted for this only once
            count=0
            flag=True
            while_stop=False
            text=driver.find_element(By.CLASS_NAME,'t-24').text
            while len(text)=='' and flag:
                time.sleep(0.5)
                text=driver.find_element(By.CLASS_NAME,'t-24').text
                count=count+1
                if count==40:
                    driver.get(link)
                    count=0
                    if while_stop:
                        flag=False
                    while_stop=True

            #4.1.4) putting in the gathered data
            jobs.loc[ind,'title']=text
            jobs.loc[ind,'scientist']=scientist(text)
            jobs.loc[ind,'company']=info[0]
            jobs.loc[ind,'raw_location']=info[1]
            jobs.loc[ind,'city']=cities(info[1])
            
            if isinstance(jobs.loc[ind,'post time'], float):
                jobs.loc[ind,'post time']=time_adjust(info[2])
            if 'Reposted' in info[2]:
                jobs.loc[ind,'Reposted']=True
            else:
                jobs.loc[ind,'Reposted']=False
        
            try:
                jobs.loc[ind,'applicants']=re.findall(r'\d+', str(info[3]))[0]
            except:
                jobs.loc[ind,'applicants']=np.nan

            #4.1.5) Pressing the button for description to open up if needed
            button=driver.find_element(By.CLASS_NAME, 'jobs-description__footer-button')
            more_flag=True
            while more_flag:
                if 'more' in button.find_element(By.CLASS_NAME, 'artdeco-button__text').text:
                    button.click()
                    if 'more' not in button.find_element(By.CLASS_NAME, 'artdeco-button__text').text:
                        more_flag=False
            
            jobs.loc[ind,'description']=driver.find_element(By.CLASS_NAME,"jobs-box__html-content").text
            jobs.loc[ind,'lang']=detect_langs(jobs.loc[ind,'description'])[0]

            #4.1.6) Getting info on whether a job is on site. While loop in case of errors
            count=0
            flag=True
            while_stop=False
            text=driver.find_element(By.CLASS_NAME,'job-details-jobs-unified-top-card__job-insight').text
            text=is_on_site(text)
            while text==-2 and flag:
                time.sleep(0.5)
                text=driver.find_element(By.CLASS_NAME,'t-24').text
                count=count+1
                if count==20:
                    driver.get(link)
                    count=0
                    if while_stop:
                        flag=False
                    while_stop=True
            
            jobs.loc[ind,'on_site']=is_on_site(text)
            main_while_flag=False

        #4.1.7) End of the very first "try"  
        except KeyboardInterrupt:
            main_while_flag=False
        except:
            None

#4.2) Pickling data 
main_dataframes={}
main_dataframes['jobs']=jobs.copy()
file_path='C:/Users/user/Desktop/projects/main_dataframes.pickle'
with open(file_path, "wb") as file:
    main_dataframes=pickle.dump(main_dataframes,file)
