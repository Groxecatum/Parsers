# -*- coding: utf-8 -*- 

'''
Created on 30 авг. 2015 �.

@author: Grey
'''
import os;
import re;
import threading;
import time;
from urllib2 import urlopen;
import lxml.html as html;

#===================================================================================================================
site_url = 'http://instrument.ru';
pages_ended_str = u'В этой категории нет ни одного товара.';
pages_ended_str2 = u'Не найдено ни одного товара.'
CSVFilePart = 'instrument_parse-results-part-{0}.csv';
CACHEFile = 'itemlinks_instrument.txt';
formatStr = '{0};{1};{2};{3};{4}\n';
maxAdditionalImages = 8;
#===================================================================================================================
def ParseCategory(root, tree, IsMultipleSKUs): # если артикулов больше одного - тогда название входит как название группы
    way = root.find_class('breadcrumbs').pop();
    way = way.text_content();
    wayParts = way.split(u'→');
    wayParts.remove(wayParts[0]);
    wayParts.remove(wayParts[-1]);
    way = '';
    for wayPart in wayParts:
        wayPart = PrettifyStr(wayPart.strip());
        not_last_part_of_singlesku = wayPart != PrettifyStr(wayParts[-1].strip()); 
        #if wayPart != PrettifyStr(wayParts[-1]):   
        way += wayPart;
        if not_last_part_of_singlesku:
            way += '|';
    return way;     

def IsSKU(Str): #строка содержит 5+ цифр(подряд?)
    Res = (re.search('\d', Str) != None) or (re.search('-', Str) != None); 
    return Res;

def DeleteSpacesFromMiddle(Str):
    Str = re.sub("\s{2}", '', Str);
    return Str;    

def MultipleStrip(Str):
    Str = re.sub("^\s+|\s+$", '', Str);
    return Str;

def DeleteLineWraps(Str):
    Str = re.sub("\n|\r", '', Str);
    return Str;

def PrettifyStr(Str):
    Str = DeleteLineWraps(Str);
    Str = MultipleStrip(Str);
    Str = DeleteSpacesFromMiddle(Str);
    return Str;

def ParseDescElement(root, tree):
    try:
        elem = root.get_element_by_id('product-description');
    except KeyError:
        elem = None;
    return elem;

def ParseSpecsElement(root, tree):
    try:
        elem = root.get_element_by_id('product-features');
    except KeyError:
        elem = None;
    return elem;

def savepics(imgs, itemLink):
    itemLink = itemLink.replace(site_url, '').strip();
    itemLink = itemLink[:-1];
    itemLink = itemLink.replace('/', '\\');
    fullPath = r'images\instrument' + itemLink;
    saved_imgs = [];
    if not os.path.exists(fullPath):
        os.makedirs(fullPath);
    for img in imgs.split(';'):
        if img != '':
            imagename = "{0}\\{1}".format(fullPath, img.split('/')[-1]);
            saved_imgs.append(imagename.replace('\\', '/'));
            if not os.path.exists(imagename):
                print 'Opening image: ' + img;
                try:
                    resource = urlopen(img, timeout = 10000);
                except: 
                    time.sleep(30);
                    resource = urlopen(img, timeout = 10000);
                out = open(imagename, 'wb');
                try:
                    out.write(resource.read());
                finally:
                    out.close(); 
                print imagename + ' saved';
            else:
                print imagename + ' passed';
        else:
            saved_imgs.append(''); 
            
    return ';'.join(saved_imgs);

def ParseImages(root, tree):
    res = [];
    main_image_div = root.get_element_by_id('product-core-image'); # Забираем основное фото
    for imageLink in main_image_div.iterlinks():
        if '.970' in imageLink[2]:
            res.append(site_url + imageLink[2]);
            
    resStr = ';'.join(res); 
    return resStr;

def ParseName(root, tree):
    title = root.get_element_by_id('page-content');
    span = title.xpath('./article/h1/span');
    return span[0].text_content().replace(';', ',');

def ParseDesc(desc_div, desc_div_specs, tree):
    res = '';
    if desc_div is not None:  
        for child in desc_div.getchildren():
            res += html.tostring(child, encoding='utf-8').replace(';', ',');
         
    if desc_div is not None:  
        for child in desc_div_specs.getchildren():
            res += html.tostring(child, encoding='utf-8').replace(';', ',');
    #print res;
    return res;

def ParseSKU_DESC(desc_div, tree, sku_default):
    Result = {};
    root = tree.getroot();
    # Парсим артикул - он у них отдельно
    cart_form = root.get_element_by_id('cart-form');
    sku_span = cart_form.xpath('./div/span').pop();
    if sku_span is not None:
        Result[sku_span.text_content().strip()] = '';  
    if len(Result) == 0:
        Result[sku_default] = '';                     
    return Result;

def ParseItems(linkLines, lock, part):
    res_file = open(CSVFilePart.format(part), 'w+', 0);
    try:
        res_file.write('{0};{1};{2};{3};{4}\n'.format('sku', 'name', 'desc', 'group', 'img'));
        for itemLink in linkLines:
            itemLink = itemLink.strip();
            try:
                page = urlopen(site_url + itemLink, timeout = 10000);
            except:
                time.sleep(30);
                page = urlopen(site_url + itemLink, timeout = 10000);
            tree = html.parse(page);
            root = tree.getroot(); 
            print 'Item link: ' + site_url + itemLink;
            name_str = ParseName(root, tree);
            print 'Name: ' + name_str;
            img_str = ParseImages(root, tree).strip();
            print 'Images links:' + img_str;
            if img_str != '':
                img_str = savepics(img_str, itemLink);
                
            print 'Images paths:' + img_str;    
            desc_div = ParseDescElement(root, tree);
            desc_div_specs = ParseSpecsElement(root, tree);    
            
            # основная операция
            SKUs_NameDesc_dict = ParseSKU_DESC(desc_div_specs, tree, name_str);
            
            IsMultipleSKUs = False; # Здесь только одиночные артикулы. Но что бы не рушить логику ниже - проще просто переназначить.
            
            group_str = PrettifyStr(ParseCategory(root, tree, IsMultipleSKUs));
            print 'Category:' + group_str;   
            desc_str = PrettifyStr(ParseDesc(desc_div, desc_div_specs, tree));
            #print desc_str;
            orig_name_str = name_str;
            group_str = group_str.encode('windows-1251', errors='ignore');
            desc_str = desc_str.decode('utf-8').encode('windows-1251', errors='ignore'); 
            img_str = img_str.encode('windows-1251', errors='ignore');
            for key in SKUs_NameDesc_dict:
                name_str = orig_name_str;
                encodedKey = key.encode('windows-1251', errors='ignore');
                if IsMultipleSKUs:
                    name_str = orig_name_str + '(' + SKUs_NameDesc_dict[key] + ')';
                name_str = name_str.encode('windows-1251', errors='ignore');
                #with lock:
                res_file.write(formatStr.format(encodedKey, 
                                        name_str, 
                                        desc_str,
                                        group_str, 
                                        img_str)); 
    finally:
        res_file.close();

def createThread(threads, lock, threadItems):
    t = threading.Thread(target=ParseItems, args=(threadItems[:], lock, len(threads))); 
    threads.append(t);
       
def IsItemsCached():
    return os.path.exists(CACHEFile);

def CacheItems():
    items_cache = open(CACHEFile, 'w');
    try:  
        MainMenuLinks = [];
        #if not os.path.exists(imagesDir):
            #os.makedirs(imagesDir);
        page = urlopen(site_url + '/');
        tree = html.parse(page);
        root = tree.getroot();
        catalog_elem = root.find_class('catalog').pop();
        if catalog_elem is not None:
            MainMenuItems = catalog_elem.find_class('menu-h').pop();
            #print MainMenuItems;
            #парсим категории
            if (MainMenuItems is not None) and (MainMenuItems.tag == 'ul'): 
                for MainMenuItem in MainMenuItems:
                    #print MainMenuItem;
                    #print tostring(MainMenuItem);
                    for link in MainMenuItem.iterlinks():
                        if 'category' in link[2]:
                            MainMenuLinks.append(link[2]);
                            print 'MainMenu link:' + link[2];
        
        #Обходим все страницы   
        for MainMenuLink in MainMenuLinks:
            page_num = 1;
            while True:
                try:
                    print 'Opening: ' + site_url + MainMenuLink + '?page={0}'.format(page_num);
                    page = urlopen(site_url + MainMenuLink + '?page={0}'.format(page_num), timeout = 10000);
                    tree = html.parse(page);
                    root = tree.getroot();
                    lst = root.get_element_by_id('product-list');
                    if (pages_ended_str in lst.text_content()) or (pages_ended_str2 in lst.text_content()):
                        break;
                    else: 
                        for link in lst.iterlinks():
                            if re.search('^/\d{1,6}|\d{1,6}_ru/$', link[2]):
                                print 'Cached:' + link[2];
                                items_cache.write(link[2] +'\n');    
                except:
                    print site_url + MainMenuLink + '?page={0}'.format(page_num) + ' is broken!!!';
                    continue;
                
                page_num += 1;        
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
    #ParseItems(items_cache.readlines(), lock, 0);
    for itemLink in items_cache.readlines():
        threadItems.append(itemLink);
        if len(threadItems) >= 250:
            threadItems = createThread(threads, lock, threadItems);
            threadItems = []; 
    if len(threadItems):
        createThread(threads, lock, threadItems);
        threadItems = [];    
    print len(threads);
    for thread in threads:
        thread.start();
finally:
    items_cache.close();