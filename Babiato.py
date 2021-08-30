import grequests
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime, date
from random import randint
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import csv
import os
import re
import json
import time
import logging
import smtplib
import js2py
import shutil


category_num = 1 #category number that you want to scrape from 1 to 6

logging.basicConfig(
  filename = 'logfile_WordPress.log',
  filemode = 'w+',
  format = '%(asctime)s:%(message)s'
)


class Babiato_scrapper:
    mega_user = 'vasiapupkin212112afv@gmail.com'
    mega_pass = '12345678danet'

    proxy_user = ''
    proxy_password = ''
    proxy_ip = '' #better pure ip of proxy but domain can be
    proxy_port = ''
    proxies  = {} # if you want to delete proxy then make proxies = {}

    # kproxy private server
    private_server_arr = []

    driver_path = 'geckodriver'

    sender = 'shopflippa@gmail.com' #email of sender mail
    receiver = 'shopflippa+babiato@gmail.com' #email of receiver mail
    pas = 'y5YhswsuLJYxzLZ' #password of sender email

    #headers for babiato
    headers = {"user-agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
    "cookie": """_ga=GA1.2.78058051.1608595229; __gads=ID=6787c93ac08f5456-22d435596bb90045:T=1608591327:RT=1608591327:S=ALNI_MZTyc0VTO-HCRZTAFdqU0HKeM2CZg; xf_user=101501%2Ch5GGckAPRYlZVah_474sIdbQ_biCcLFoG-kfazr5; xf_csrf=cjDu-pOXKmiwzZ64; xf_session=qeuCNzd-f3y6MokVd4EuXRhwt1D3Lohl; _gid=GA1.2.203705266.1622464855; xf_forumstats_autorefresh=1; _gat_gtag_UA_122238493_1=1"""}

    download_image_directory = './files/images'
    download_file_directory = './files/files'
    csv_directory = './files/csv_files/'
    any_babiato_item_link = 'https://babiato.co/resources/woocommerce-account-funds.63/' # need for first row in csv file


    #return selected category title and sub categories links
    def get_main_and_sub_categories(self, num_of_category):
        category = {}

        r = requests.get('https://babiato.co/resources/', headers = self.headers, proxies = self.proxies)
        assert r.status_code == 200
        soup = bs(r.text, 'lxml')

        category['category_name'] = soup.select("#js-SideNavOcm > div > div:nth-child(2) > div > div:nth-child(1) > div > div > ol > li:nth-child({}) > div > a.categoryList-link".format(num_of_category))[0].text.replace(' ', '_').replace('\n', '').replace('$', '').replace('\'', '')
        category['sub_categories_links'] = []

        for a in soup.select('#js-SideNavOcm > div > div:nth-child(2) > div > div:nth-child(1) > div > div > ol > li:nth-child({}) > ol > li > div > a.categoryList-link'.format(num_of_category)):
            category['sub_categories_links'].append('https://babiato.co{}'.format(a.get('href')))
        return category


    #scrape the need category
    def scrape_category(self, num_of_category):
        assert num_of_category >= 1 and num_of_category <= 6 #here is 6 categories
        category = self.get_main_and_sub_categories(num_of_category)
        self.category_name = category['category_name']
        sub_categories_links = category['sub_categories_links']

        #get the duplicate data from file
        self.duplicate_data = self.get_duplicate_data(self.category_name)
        #clear all previous duplicate data
        f = open('./files/duplicate/{}.txt'.format(self.category_name), 'w+')
        f.write(json.dumps([]))
        f.close()


        self.create_envado_first_line() # create first line for envado comments and reviews

        #get object properties for first line in csv
        r = requests.get(self.any_babiato_item_link, proxies=self.proxies, headers = self.headers)
        obj = self.scrape_item(r)
        first_line = [property for property in obj]

        #clear previous data in csv file and add first line
        f = open("{}/{}.csv".format(self.csv_directory,self.category_name), 'w+', encoding = 'utf-8-sig', newline='')
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writerow(first_line)
        f.close()

        del obj, first_line, writer

        #scrape the sub categories
        for link in sub_categories_links:
            self.scrape_sub_category(link)


    def scrape_sub_category(self, link):
        self.items_info = []
        items_links = self.get_pages_links_sub_category(link)
        self.save_pages_info_to_csv(self.category_name,self.items_info)
        self.save_duplicate_data(self.category_name,self.items_info)
        del self.items_info


        #scrape the items diverse them n parts
        n = 30
        get_from = 0
        page_index = 0 #how many pages already scrapped
        items_part = round(len(items_links) / n) # n part of pages

        for part_count in range(n):
            pages_to_scrape = items_links[get_from: get_from + items_part]
            get_from += items_part

            items_info = []
            scraped_pages = grequests.map([grequests.get(u, headers = self.headers, proxies = self.proxies) for u in pages_to_scrape])
            for r in scraped_pages:
                page_index += 1
                logging.warning('Scrapped {}/{} pages '.format(page_index, len(items_links)))

                if not r: continue
                if 'https://babiato.co/resources' not in r.url or r.status_code != 200:
                    send_message('Issue with this url: {}, status code: {}'.format(r.url, r.status_code))
                    continue

                try:
                    # the error could be the proxy error
                    #items_info.append(self.scrape_item(r))
                    item = self.scrape_item(r)
                    self.save_pages_info_to_csv(self.category_name,[item])
                    self.save_duplicate_data(self.category_name,[item])
                except Exception as e:
                    logging.warning(f'Exception with item {e}, item: {r.url}')

            #save info into files
            """self.save_pages_info_to_csv(self.category_name,items_info)
            self.save_duplicate_data(self.category_name,items_info)
            del items_info, scraped_pages, pages_to_scrape"""
            logging.warning('scrape the next part of pages')



    # return pages urls from sub category (check if this app version has already)
    def get_pages_links_sub_category(self,link):
        #return items urls
        items_urls = []
        #get the pages
        r = requests.get(link, headers = self.headers, proxies = self.proxies)
        soup = bs(r.text,'lxml')

        pages_url = []
        #take the max count of page
        if len(soup.select('#top > div.p-body > div > div.uix_contentWrapper > div.p-body-main.p-body-main--withSideNav > div.p-body-content > div > div > div:nth-child(1) > div > nav > div.pageNav.pageNav--skipEnd > ul > li:nth-child(5) > a')) != 0:
            count = soup.select('#top > div.p-body > div > div.uix_contentWrapper > div.p-body-main.p-body-main--withSideNav > div.p-body-content > div > div > div:nth-child(1) > div > nav > div.pageNav.pageNav--skipEnd > ul > li:nth-child(5) > a')[0].text
            for i in range(1,int(count) + 1): pages_url.append("{}?page={}".format(link,i))
        else: #if hasn't it means that pages < 5
            if len(soup.select('.block-outer-main')) == 0: pages_url.append(link) #it means this sub category has 1 page items in another words url - 1 page of sub category & the only
            else: # pages < 5
                elems = soup.select('ul.pageNav-main')[0]
                elems = elems.select('ul > li > a')
                for elem in elems: pages_url.append('https://babiato.co{}'.format(elem.get('href')))


        responses = grequests.map([grequests.get(u, headers = self.headers, proxies= self.proxies) for u in pages_url])
        for r in responses:
            if not r: continue
            if r.status_code != 200: continue
            soup = bs(r.text, 'lxml')
            #get the blocks of items
            for block in soup.select('.structItem.structItem--resource'):
                item_title = block.select('.structItem-title > a')[0].text
                item_url = block.select('.structItem-title > a')[0].get('href')
                if len(block.select('.structItem-title > span.u-muted')) != 0: item_version = block.select('.structItem-title > span.u-muted')[0].text
                else: item_version = None

                # check if it has already in server
                if self.has_item_in_server(item_title, item_url, item_version): continue
                items_urls.append('https://babiato.co{}'.format(item_url))
        return items_urls




    # scrape the item page
    def scrape_item(self, r):
        item_info = {}
        soup = bs(r.text, 'lxml')

        if not soup.select('.p-title > h1'): return {}
        item_info['id'] = re.findall('\.(\d+)/', r.url)[0]
        if len(soup.select('.p-title > h1 > span')) != 0:
            pure_version = re.findall(r'([\d\.]+)\b', soup.select('.p-title > h1 > span')[0].text) #delete no need symbols
            if not pure_version: item_info['version'] = None
            else: item_info['version'] = pure_version[0]
        else: item_info['version'] = None

        #delete from title the version if it has
        title_block = soup.select('.p-title > h1')[0]
        if len(title_block.select('span')) != 0: title_block.select('span')[0].decompose()
        item_info['title'] = title_block.text.replace('\n', '').replace(',', '')


        #download image
        if len(soup.select('#top > div.p-body > div > div.uix_contentWrapper > div > div > div > div.block > div.block-container > div > div > article > div.bbWrapper > div > img')) == 0: item_info['local_image'] = None
        else:
            #src of image link
            src = soup.select('#top > div.p-body > div > div.uix_contentWrapper > div > div > div > div.block > div.block-container > div > div > article > div.bbWrapper > div > img')[0].get('src')
            image_r = requests.get(src, headers = self.headers, proxies=self.proxies)
            img_filename = self.delete_prohibited_symbols(item_info['title'].replace(' ', '_') + '.jpg')
            image = open('{}/{}'.format(self.download_image_directory, img_filename), 'wb')
            image.write(image_r.content)
            image.close()
            item_info['local_image'] = '{}/{}'.format(self.download_image_directory, img_filename)


        description_block = soup.select('.bbWrapper')[0]
        # delete image from description if it has
        if len(description_block.select('.bbImageWrapper')) != 0:
            description_block.select('.bbImageWrapper')[0].decompose()

        item_info['description'] = re.sub(r'\s{3}', '', ''.join([str(block) for block in description_block.contents]) )
        item_info['description'] = re.sub(r'https?://\S+\b', '', item_info['description']) # delete links from text


        item_info['views'] = soup.select('.resourceBody-sidebar > .resourceSidebarGroup > dl:nth-child(3) > dd')[0].text
        item_info['downloads'] = soup.select('.resourceBody-sidebar > .resourceSidebarGroup > dl:nth-child(2) > dd')[0].text
        item_info['url'] = r.url
        item_info['date_scraped'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        item_info['date_published'] = int(soup.select('.resourceBody time')[0].get('data-time'))
        item_info['date_published'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(item_info['date_published']))

        item_info['last_uploaded'] = int(soup.select('.resourceBody time')[1].get('data-time'))
        item_info['last_uploaded'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(item_info['last_uploaded']))

        #get categories
        item_info['categories'] = ''
        for category in soup.select('ul.p-breadcrumbs')[0].select('li')[2:]:
            item_info['categories'] += category.text.replace('\n', '') + ';'

        download_link = 'https://babiato.co{}'.format(soup.select('.p-title-pageAction > a')[0].get('href'))
        item_info['local_file'],item_info['type'],item_info['external'], item_info['link_download_site']  = self.download_file(download_link, self.delete_prohibited_symbols(item_info['title']).replace(' ', '_'))
        item_info['update'] = self.get_item_previous_updates(r)

        if len(soup.select('.resourceSidebarGroup.resourceSidebarGroup--buttons > a:nth-child(2)')) == 0: item_info['link_demo'] = None
        else: item_info['link_demo'] = soup.select('.resourceSidebarGroup.resourceSidebarGroup--buttons > a:nth-child(2)')[0].get('href')

        item_info['demo_body'] = None
        item_info['demo_title'] = None
        item_info['demo_description'] = None
        item_info['demo_tags'], item_info['demo_rating'], item_info['demo_votes'] = None, None, None
        if not item_info['link_demo']:
            pass
        else:
            self.scrape_demo_site(item_info['link_demo'], item_info)

        return item_info



    def get_item_previous_updates(self, page):
        result_string = ''
        r = requests.get(page.url + 'updates?page=1', allow_redirects=True, headers = self.headers, proxies=self.proxies)

        #if item has updates it'll direct script to update page if not it'll redirect script to item page (page.url)
        if r.url != page.url:
            #if for example item update page 10 hasn't got then script will be redirected to page 9, then page 10 hasn't got
            previous = ''
            for update in range(1,10):
                r = requests.get(page.url + 'updates?page=' + str(update), allow_redirects=True, headers = self.headers, proxies=self.proxies)
                if previous == r.url:
                    break

                soup = bs(r.text, 'lxml')
                #data for each update
                time_blocks = soup.select('ul.message-attribution-opposite.message-attribution-opposite--list > li > a > time')
                version_blocks = soup.select('h2.message-attribution-main.block-textHeader')
                text_blocks = soup.select('.bbWrapper')

                for y in range(len(time_blocks)):
                    #take version
                    version = ''.join([num + '.' for num in re.findall('(\d)', version_blocks[y].text)])[:-1] # delete last comma
                    if not version: continue

                    result_string += f"<p class='update_version'>{version}<p> \n"
                    result_string += f"<p class='update_date'>{time_blocks[y].text}</p> \n"
                    result_string += f"<p class='update_changelog'><ul><li> {text_blocks[y].text} </li></ul></p> \n"
                previous = page.url + 'updates?page=' + str(update)

        else: result_string = None

        if str(result_string) == '':
            result_string = None

        return result_string


    def scrape_demo_site(self, demo_link, item_info):
        demo_body = ''
        demo_title = ''
        demo_description = ''

        try:
            r = requests.get(demo_link, allow_redirects=True, headers = self.headers, proxies=self.proxies)
            if r.status_code != 200: return

            soup = bs(r.text, 'lxml')
            demo_title = soup.select('title')[0].text
            try: demo_description = str(soup.select('meta[name="description"]')[0].get('content'))
            except: demo_description = None
            for p in soup.select('p'):
                if len(p.text.replace(' ', '')) < 4: continue
                demo_body += p.text + ';'

            item_info['demo_description'] = demo_description
            item_info['demo_title'] = demo_title
            item_info['demo_body'] = demo_body
            item_info['demo_tags'], item_info['demo_rating'], item_info['demo_votes'] = EnvadoScraper(item_info['title'], self.proxies, self.category_name, self.csv_directory).scrape_link(demo_link)
        except Exception as e:
            logging.warning(f'Exception with demo sites: {e}')
            return



    #download file parts
    def download_file(self, download_link, title):
        type = ''
        external = ''
        local_file = ''
        link_download_site = ''

        try: r = requests.get(download_link, allow_redirects = True, proxies = self.proxies, headers = self.headers)
        except: return (None, None, True, download_link)

        link_download_site = r.url
        if 'babiato.co' in r.url:
            external = False
            local_file, type = self.download_file_from_babiato(r, title)
        else:
            external = True
            local_file, type = self.download_file_from_external_site(r, title)

        logging.warning('scrape from: {}, file: {}'.format( link_download_site, local_file))
        return (local_file, type, external, link_download_site)


    def download_file_from_babiato(self, r, title):
        #here is 2 files from babiato, download the file from there
        if 'text/html' in r.headers['Content-Type']:
            try:
                r = requests.get(r.url, proxies = self.proxies, headers = self.headers)
                if r.status_code != 200 or 'babiato.co' not in r.url: return (None, None)
                link = 'https://babiato.co' + bs(r.text, 'lxml').select('.contentRow-main a')[0].get('href')
                r = requests.get(link, proxies = self.proxies, headers = self.headers)
            except:
                return (None, None)

        filename = self.delete_prohibited_symbols(re.findall(r'filename="(.+)"', r.headers['Content-Disposition'])[0])
        # in txt file the links for external domains, parse them until scrape 1 file
        if '.txt' in filename:
            links = re.findall(r'(\w+)', r.text)
            for link in links:
                try:
                    r = requests.get(link, proxies = self.proxies, headers = self.headers, allow_redirects = True)
                    local_file, type = self.download_file_from_external_site(r,title)
                    if not local_file and not type: continue
                    return (local_file, type)
                except: continue

            #if script didn't scrape file from links return nothing
            return (None,None)


        f = open('{}/{}'.format(self.download_file_directory, filename), 'wb')
        f.write(r.content)
        f.close()
        type = re.findall('\.(\w+)$', filename)[0]
        return ('{}/{}'.format(self.download_file_directory, filename), type)



    def download_file_from_external_site(self,r,title):
        external_parser = External_scrapper(download_directory = os.path.abspath(os.path.dirname(self.download_file_directory + '/')), file_name = title, relative_path = self.download_file_directory,
                                            proxies = self.proxies, headers = self.headers, driver = self.driver, private_server_arr = self.private_server_arr)

        if '://mega' in r.url:
            result = external_parser.scrape_mega(r.url)
            return result

        if '4sync.com' in r.url:
            result = external_parser.scrape_sync(r.url)
            return result

        if 'zippyshare' in r.url:
            result = external_parser.scrape_zippyshare(r.url)
            return result

        if 'www.mirrored' in r.url:
            #get the zippy link from miro after scrape zippyshare
            zippyshare_link = external_parser.get_zippyshare_from_mirrored(r.url)
            if not zippyshare_link: return (None, None)
            result = external_parser.scrape_zippyshare(zippyshare_link)
            return result

        return (None, None)







    def save_duplicate_data(self,category_name, items):
        f = open('./files/duplicate/{}.txt'.format(category_name), 'r+')
        duplicate_data = json.loads(f.read())
        f.close()

        for obj_item in items:
            obj_item['version'] = re.sub(r'\s+', '', str(obj_item['version'])).lower()
            duplicate_data.append(obj_item)

        f = open('./files/duplicate/{}.txt'.format(category_name), 'w+')
        f.write(json.dumps(duplicate_data))
        f.close()


    def save_pages_info_to_csv(self,category_name, info_items):
        #write to csv file data
        f = open("{}/{}.csv".format(self.csv_directory,category_name), 'a+', encoding = 'utf-8-sig', newline='')
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_ALL)

        for item in info_items:
            row = []
            for property in item: row.append( '\n'.join(str(item[property]).splitlines()).replace(',', '').replace('\"', '')[:21000] )
            writer.writerow(row)
        f.close()






    #if this item version has already in server
    def has_item_in_server(self,title,url,version):
        id = re.findall('\.(\d+)/', url)[0]
        version = re.sub(r'\s+', '', str(version)).lower()

        for item in self.duplicate_data:
            if id == item['id'] and (version in item['version'] or item['version'] in version):
                # if this item has in server already add item info previous for csv file
                logging.warning('that item was before {}'.format(title))
                self.items_info.append(item)
                return True

        return False



    def get_duplicate_data(self,category_name):
        try:
            f = open('./files/duplicate/{}.txt'.format(category_name), 'r+')
            data = json.loads(f.read())
            f.close()
            return data
        except: return []

    def delete_prohibited_symbols(self,string):
        replacement = ['/', '<', '?', '>', '\\', ':', '*', '\n', '|', '&', ',']
        for symbol in replacement:
            string = string.replace(symbol, '')
        return string

    #create the need folders for collect the data
    def create_folders(self):
        if os.path.exists('./files') == False: os.makedirs('./files')
        #create folder for image, csv, duplicate & files if it hasn't got directory
        if os.path.exists('./files/images') == False: os.makedirs('./files/images')
        if os.path.exists('./files/csv_files') == False: os.makedirs('./files/csv_files')
        if os.path.exists('./files/files') == False: os.makedirs('./files/files')
        if os.path.exists('./files/duplicate') == False: os.makedirs('./files/duplicate')


    #send message to email file
    def send_message(message):
        logging.warning(str(message))
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender, self.pas)
            server.sendmail(self.sender,self.receiver,message)
        except:
            #this error when we sended more than 100 emails
            pass



    #create browser for external scrapper
    def register_into_mega(self, driver):
        driver.get('https://mega.nz/login')
        WebDriverWait(driver, 15).until( EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.accept-cookies'))).click()
        driver.find_element_by_css_selector('#login-name2').send_keys(self.mega_user)
        driver.find_element_by_css_selector('#login-password2').send_keys(self.mega_pass)
        driver.find_element_by_css_selector('button.login-button').click()
        time.sleep(3)


    def create_browser(self):
        path = os.path.join(os.path.abspath(os.path.dirname(__file__)), self.driver_path)

        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.helperApps.neverAsk.openFile","application/x-gzip")
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference("browser.download.dir", os.path.abspath(self.download_file_directory)) # os.path.abspath(os.path.dirname(self.download_file_directory + '/'))
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip,application/octet-stream,text/plaintext,application/vnd.android.package-archive")

        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Firefox(profile, executable_path=path, options=options)
        driver.implicitly_wait(10)
        self.register_into_mega(driver)
        return driver

    def create_envado_first_line(self):
        file = open(f'{self.csv_directory}/{self.category_name}_comments.csv', 'w+', newline='')
        writer = csv.writer(file, quoting=csv.QUOTE_ALL, delimiter = ',')
        first_row = ['item_title', 'author', 'comment', 'comment_date']
        writer.writerow(first_row)
        file.close()

        file = open(f'{self.csv_directory}/{self.category_name}_reviews.csv', 'w+', newline='')
        writer = csv.writer(file, quoting=csv.QUOTE_ALL, delimiter = ',')
        first_row = ['item_title', 'stars', 'author', 'review_date', 'review_text']
        writer.writerow(first_row)
        file.close()









# external scraper scrape the sites: mega.zn (not by api), zippyshare, 4sync.io and getting zippyshare link from mirrored
class External_scrapper:
    def __init__(self, driver = "", download_directory = os.path.abspath(os.path.dirname(__file__)), headers = {}, file_name = 'file', proxies = {}, private_server_arr = [], relative_path = './'):
        private_server_url = private_server_arr[ randint(0, len(private_server_arr) - 1) ]

        self.download_directory = download_directory
        self.file_name = file_name
        self.proxies = proxies
        self.headers = headers
        self.private_server_url = private_server_url
        self.driver = driver
        self.relative_path = relative_path

    def scrape_mega(self, url):
        driver = self.driver
        try:
            driver.get(url)

            filename = driver.find_element_by_css_selector('.download.info-txt.big-txt').get_attribute('title')
            extension = driver.find_element_by_css_selector('#startholder > div.bottom-page.scroll-block.startpage.download.light-blue-top.animated-page.start-animation > div > div.download.top-bar.initial.auto.expanded > div.bottom-page.download-content > div > div:nth-child(3) > div.download.main-pad > div.download.transfer-wrapper > div.download.info-block > div.download.file-info > div.download.info-txt.big-txt > span.extension').text.replace('.', '')
            if os.path.isfile(os.path.join(self.download_directory, filename)):
                os.remove(os.path.join(self.download_directory, filename)) #otherwise browser will download file in another file name

            WebDriverWait(driver, 15).until( EC.element_to_be_clickable((By.CSS_SELECTOR, '.download.buttons-block > button.mega-button.download:nth-child(2)'))).click()
            #after start the download the title has % symbol while file is downloading, after download this symbol deleted
            time.sleep(5)
            while True:
                if '%' not in driver.title: break
                time.sleep(1)
            time.sleep(7)

            #change file name to need name
            os.rename(os.path.join(self.download_directory, filename), os.path.join(self.download_directory, f"{self.file_name}.{extension}"))

            if not os.path.isfile(os.path.join(self.download_directory, f"{self.file_name}.{extension}")):
                logging.warning(f'Created folder: {self.file_name}.{extension}')

            path = os.path.join(self.relative_path, "{}.{}".format(self.file_name, extension)).replace('\\', '/')
            return (path, extension)
        except:
            return (None, None)



    def get_zippyshare_from_mirrored(self,url):
        try:
            r = requests.get(url, headers = self.headers, proxies= self.proxies)
            soup = bs(r.text,'lxml')
            try:
                #get value of form data
                data = {
                "uhash": soup.select('input[name="uhash"]')[0].get("value"),
                "dl": soup.select('input[name="dl"]')[0].get('value')}
                r = requests.post(url, data = data, headers = self.headers, proxies= self.proxies)
            except:
                href = soup.select('body > div.container.dl-width > div:nth-child(3) > div > a')[0].get('href')
                r = requests.get(href,headers = self.headers, proxies= self.proxies)

            #get the same link with form data
            soup = bs(r.text,'lxml')
            #find the link of servers links in js scripts
            for script in soup.select('script'):
                if '/mirstats.php' in str(script):
                    words = str(script).split(' ')
                    for word in words:
                        if '/mirstats.php' in word:
                            r = requests.get('https://www.mirrored.to' +  word.replace('\"', '').replace(',', ''), headers = self.headers, proxies= self.proxies)
                            try: link = 'https://www.mirrored.to' + bs(r.text,'lxml').select('body > div.col-sm > table > tbody > tr:nth-child(1) > td:nth-child(2) > a')[0].get('href')
                            except: return None

                            r = requests.get(link, headers = self.headers, proxies= self.proxies)
                            zippyshare_link = bs(r.text, 'lxml').select('body > div.container.dl-width > div:nth-child(3) > div > a')[0].get('href')
                            return zippyshare_link
            return None
        except:
            return None


    def scrape_zippyshare(self, url):
        driver = self.driver
        try:
            driver.get(self.private_server_url)

            driver.find_element_by_css_selector('#surfbar > input:nth-child(1)').send_keys(url)
            WebDriverWait(driver, 15).until( EC.element_to_be_clickable((By.CSS_SELECTOR, '#surfbar > input:nth-child(2)'))).click()
            file_link = WebDriverWait(driver, 15).until( EC.element_to_be_clickable((By.CSS_SELECTOR, '#dlbutton'))).get_attribute('href')

            #get cookie for download file link directly
            cookie_string = ''
            for cookie in list(driver.get_cookies()):
                cookie_string += "{}={}; ".format(cookie['name'], cookie['value'])

            #download file from file link
            file_extension = re.findall(r'\.(\w+)$', file_link)[0]
            r = requests.get(file_link, headers = {"user-agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36", 'cookie': cookie_string})
            f = open(os.path.join(self.download_directory, self.file_name) + '.{}'.format(file_extension), 'wb')
            f.write(r.content)
            f.close()

            return (os.path.join(self.relative_path, self.file_name) + '.{}'.format(file_extension), file_extension)
        except:
            return (None,None)

    def scrape_sync(self, url):
        driver = self.driver
        try:
            #if it html page then get file link from there
            if '.html' in url:
                driver.get(self.private_server_url)

                driver.find_element_by_css_selector('#surfbar > input:nth-child(1)').send_keys(url)
                WebDriverWait(driver, 15).until( EC.element_to_be_clickable((By.CSS_SELECTOR, '#surfbar > input:nth-child(2)'))).click()
                file_link = driver.find_element_by_css_selector('.jsDLink').get_attribute('value')

                #get cookie for download file link directly
                cookie_string = ''
                for cookie in list(driver.get_cookies()):
                    cookie_string += "{}={}; ".format(cookie['name'], cookie['value'])

                file_extension = re.findall(r'\.(\w+)\?', file_link)[0]
                r = requests.get(file_link, headers = {"user-agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36", 'cookie': cookie_string})
                f = open(os.path.join(self.download_directory, self.file_name) + '.{}'.format(file_extension), 'wb')
                f.write(r.content)
                f.close()
                return (os.path.join(self.relative_path, self.file_name) + '.{}'.format(file_extension), file_extension)

            full_file_name = re.findall(r'/(.[^/]+)\?', url)[0]
            file_extension = re.findall(r'\.(\w+)$', full_file_name)[0]
            r = requests.get(url, headers = self.headers, proxies = self.proxies)

            f = open(os.path.join(self.download_directory, self.file_name) + '.{}'.format(file_extension), 'wb')
            f.write(r.content)
            f.close()

            return (os.path.join(self.relative_path, self.file_name) + '.{}'.format(file_extension), file_extension)
        except:
            return (None, None)





class EnvadoScraper:
    headers = {"user-agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"}
    date_format = '%Y-%m-%d'

    def __init__(self,item_title,proxies,filename,directory):
        self.proxies = proxies
        self.csv_filename = filename
        self.item_title = item_title
        self.directory = directory


    # scrape link with comments and reviews
    def scrape_link(self,link):
        r = requests.get(link, headers = self.headers, proxies = self.proxies)
        if not r or r.status_code != 200: return
        soup = bs(r.text, 'lxml')

        if not soup.select('span.meta-attributes__attr-tags > a'):
            tags = ''
        else:
            tags = ';'.join([block.text for block in soup.select('span.meta-attributes__attr-tags > a')])

        if not soup.select('.rating-detailed-small__stars'):
            stars = 0
            votes = 0
        else:
            stars_arr = re.findall(r'(\d+).(\d+)', soup.select('.rating-detailed-small__stars')[0].text)[0]
            # if stars don't have the double numbers then save star else save star with double
            if stars_arr[1] != '':
                stars = float('.'.join(stars_arr))
            else:
                stars = int(stars_arr[0])

            votes = int(''.join([number for number in re.findall(r'(\d)', soup.select('.rating-detailed-small__stars a')[0].text)]))

        self.scrape_review_comment_page(link + '/comments', 'comment')

        # make link for reviews
        split = link.split('/')
        split.insert(len(split) - 1, 'reviews')
        review_link = '/'.join(split)
        self.scrape_review_comment_page(review_link, 'review')

        return (tags, stars, votes)



    # scrape the review and comment pages
    def scrape_review_comment_page(self,start_link,page_type):
        r = requests.get(start_link, headers = self.headers, proxies = self.proxies)
        soup = bs(r.text, 'lxml')

        # get whole count of comments pages
        pages = []
        if not soup.select('ul.pagination__list'):
            pages.append(start_link) # 1 page
        else:
            block = soup.select('ul.pagination__list')[0]
            if not block.select('li:nth-child(10)'):
                for i in range(1, len(block.select('a.pagination__page')) + 1):
                    pages.append(start_link + f'?page={i}')
            else:
                page_count = block.select('li:nth-child(9)')[0].text
                for i in range(1, (int(page_count) + 1)):
                    pages.append(start_link + f'?page={i}')

        if page_type == 'comment':
            file = open(f'{self.directory}/{self.csv_filename}_comments.csv', 'a', encoding='utf-8-sig', newline='')
            scrape_method = self.scrape_comment_page
        else:
            file = open(f'{self.directory}/{self.csv_filename}_reviews.csv', 'a', encoding='utf-8-sig', newline='')
            scrape_method = self.scrape_review_page
        writer = csv.writer(file, delimiter=',', quoting=csv.QUOTE_ALL)

        rs = [grequests.get(url_page, headers = self.headers, proxies = self.proxies) for url_page in pages]
        for page in grequests.map(rs):
            if not page or page.status_code != 200: continue
            page.encoding = 'utf-8'

            for item_info in scrape_method(page):
                # item_info - info about 1 comment or 1 review
                # iterate the info to replace delimiter
                for i in range(len(item_info)):
                    item_info[i] = str(item_info[i]).replace(',', '').replace('\"', '')

                item_info.insert(0, self.item_title) # insert item title that scrapped in babiato
                writer.writerow([column.encode('utf-8', errors='replace').decode('utf-8') for column in item_info])

        file.close()


    def scrape_comment_page(self, page):
        comments = []
        soup = bs(page.text, 'lxml')

        for comment_block in soup.select('div[data-view="commentList"] > div > .comment__item'):
            comment = comment_block.select('.js-comment__body')[0].text
            author = comment_block.select('.t-link.-decoration-reversed')[0].text

            comment_date = datetime.today().strftime(self.date_format)
            date_text = comment_block.select('.comment__date')[0].text

            if 'days' in date_text:
                days = re.findall(r'\d+', date_text)[0]
                comment_date = self.get_correct_date(int(days), 'day')
            elif 'month' in date_text:
                months = re.findall(r'\d+', date_text)[0]
                comment_date = self.get_correct_date(int(months), 'month')
            elif 'year' in date_text:
                years = re.findall(r'\d+', date_text)[0]
                comment_date = self.get_correct_date(int(years), 'year')

            comments.append([author, comment, comment_date])

        return comments

    def scrape_review_page(self, page):
        reviews = []
        soup = bs(page.text, 'lxml')

        for review_block in soup.select('#content > div > div.content-s > div:nth-child(2) > article'):
            stars = (5 - len(review_block.select('i.e-icon.-color-grey-medium')))
            if not review_block.select('.t-link.-decoration-reversed'):
                block = review_block.select('p.t-body.-size-m.h-m0')[0]
                author = re.findall(r'by (\w+)\b', block.text)[0]
            else:
                author = review_block.select('.t-link.-decoration-reversed')[0].text

            if not review_block.select('p.t-body.h-my1'):
                review_text = ''
            else:
                review_text = review_block.select('p.t-body.h-my1')[0].text


            review_date = datetime.today().strftime(self.date_format)
            date_text = review_block.select('.review-header__date')[0].text

            if 'days' in date_text:
                days = re.findall(r'\d+', date_text)[0]
                review_date = self.get_correct_date(int(days), 'day')
            elif 'month' in date_text:
                months = re.findall(r'\d+', date_text)[0]
                review_date = self.get_correct_date(int(months), 'month')
            elif 'year' in date_text:
                years = re.findall(r'\d+', date_text)[0]
                review_date = self.get_correct_date(int(years), 'year')

            reviews.append([stars, author, review_date, review_text])

        return reviews

    # time correction with javascript
    def get_correct_date(self,number, time_reckorning):
        current_date = datetime.now()
        current_day = current_date.day - 1
        current_month = current_date.month - 1 # 12 months
        current_year = current_date.year

        if time_reckorning == 'day': current_day -= number
        if time_reckorning == 'month': current_month -= number
        if time_reckorning == 'year': current_year -= number

        js_function = js2py.eval_js("""
            function a(days, months, years) {
              d = new Date(years,months,days);
              return [d.getDate(), d.getMonth(), d.getFullYear()];
            }
        """) # javascript has autocorrection date

        day, month, year = js_function(current_day,current_month,current_year)
        return date(year,month + 1,day).strftime(self.date_format)






if __name__ == '__main__':
    scraper = Babiato_scrapper()
    scraper.create_folders()
    scraper.driver = scraper.create_browser() # one browser for whole scraper work
    try:
        scraper.scrape_category(category_num) #number of category that you want to scrape
    except Exception as e:
        logging.warning(f'Root exception {e}')

    logging.warning("script stopped the execution in this time")
    scraper.driver.quit() # stop webdriver
