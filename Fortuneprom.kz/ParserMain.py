# -*- coding: utf-8 -*- 
'''
Created on 11 ����. 2015 �.

@author: Grey
'''
from urllib2 import urlopen;
import lxml.html as html;
import xlsxwriter;
from io import BytesIO;
#import re;
import threading;
import os;

CACHEFile = 'fortuneprom.txt';
site_url = 'http://fortuneprom.kz';
excel_file = u'Каталог.xlsx';

def ParseDesc(root, tree):
    container = root.get_element_by_id('tab-description');
    return container.text_content();

def ParseName(root, tree):
    container = root.get_element_by_id('container');
    title = container.xpath('./h1');
    return title[0].text_content();

def ParseModel(root, tree):
    container = root.find_class('description').pop();
    return container.text_content();


def ParseCategory(root, tree):
    container = root.find_class('breadcrumb').pop();
    Cat = [];
    Res = '\\';
    for Link in container.iterlinks():
        if Link[0].text_content() != '':
            Cat.append(Link[0].text_content());
    Cat.remove(Cat[-1]);
    return Res.join(Cat);

def ParseImage(root, tree):
    try:
        image = root.get_element_by_id('image'); # Забираем основное фото
    except:
        pass;
    if image is not None:
        for imageLink in image.iterlinks():
            if '-228x228' in imageLink[2]:
                resStr = imageLink[2].replace('cache/', '');
                resStr = resStr.replace('-228x228', '');
                break;
            
    return resStr;

def ParseItems(linkLines, lock, part):
    workbook = xlsxwriter.Workbook(excel_file);
    worksheet = workbook.add_worksheet(u'Каталог');
    try:
        worksheet.write(0, 0, u'Название');#
        worksheet.write(0, 1, u'Модель');
        worksheet.write(0, 2, u'Описание');#
        worksheet.write(0, 3, u'Категория');#
        worksheet.write(0, 4, u'Изображение');#
        worksheet.write(0, 5, u'Ссылка');#
        worksheet.set_column(0, 5, 60); 
        worksheet.set_column(4, 4, 100);
        i = 1;
        #itemLink = linkLines[0];
        for itemLink in linkLines:
            itemLink = itemLink.strip();
            try:
                page = urlopen(itemLink);
                tree = html.parse(page);
            except:
                #time.sleep(30);
                page = urlopen(site_url + itemLink);
                tree = html.parse(page);
            print 'Item link: ' + itemLink + ' opened';
            root = tree.getroot(); 
            name_str = ParseName(root, tree);
            print 'Name: ' + name_str;
            worksheet.write(i, 0, name_str);
            
            model_str = ParseModel(root, tree);
            print 'Model: ' + model_str;
            worksheet.write(i, 1, model_str);
            
            desc_str = ParseDesc(root, tree);
            worksheet.write(i, 2, desc_str);
            
            group_str = ParseCategory(root, tree);
            print 'Category:' + group_str; 
            worksheet.write(i, 3, group_str); 
            
            url = ParseImage(root, tree);
            if not ('.gif' in url):
                image_data = BytesIO(urlopen(url).read())
        
                worksheet.insert_image(i, 4, url, {'image_data': image_data})
                
                worksheet.write(i, 5, itemLink); 
        i += 1;
    finally:
        #pass
        workbook.close()

def IsItemsCached():
    return os.path.exists(CACHEFile);

def CacheItems():
    items_cache = open(CACHEFile, 'w');
    try:  
        MainMenuLinks = [];
        #if not os.path.exists(imagesDir):
            #os.makedirs(imagesDir);
        page = urlopen(site_url + '/sitemap');
        tree = html.parse(page);
        root = tree.getroot();
        catalog_elem = root.find_class('left').pop();
        if catalog_elem is not None:
            for link in catalog_elem.iterlinks():
                MainMenuLinks.append(link[2]);
                print 'MainMenu link:' + link[2];
        
        #������� ��� ��������   
        for MainMenuLink in MainMenuLinks:
            print 'Opening: ' + MainMenuLink + '?limit=100';
            page = urlopen(MainMenuLink + '?limit=100', timeout = 5000);
            tree = html.parse(page);
            root = tree.getroot();
            lsts = root.find_class('product-list');
            if len(lsts): 
                lst = lsts.pop(); 
                last_link = '';
                #print root.text_content();
                for link in lst.iterlinks():
                    if ('.html' in link[2]) and link[2] <> last_link:
                        print 'Cached:' + link[2];
                        last_link = link[2];
                        items_cache.write(link[2] +'\n');  
        items_cache.close();
    except:
        items_cache.close();
        raise;
               
   
if not IsItemsCached():
    CacheItems();  
      
lock = threading.Lock();
threadItems = [];
threads = [];              
items_cache = open(CACHEFile, 'r');
try:
    ParseItems(items_cache.readlines(), lock, 0);
finally:
    items_cache.close();