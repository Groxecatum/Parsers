# -*- coding: utf-8 -*- 

'''
Created on 30 авг. 2015 �.

@author: Grey
'''
import os;
import re;
import threading;
import time;
import sys;
from urllib2 import urlopen;
import lxml.html as html;
from nt import lstat

#===================================================================================================================
site_url = 'http://10kor.ru';
pages_ended_str = u'В этой категории нет ни одного товара.';
pages_ended_str2 = u'Не найдено ни одного товара.'
CSVFilePart = '10kor_parse-results-part-{0}.csv';
ParsedPart = '10kor_parsed-{0}.txt';
CACHEFile = 'itemlinks_10kor.txt';
reviews_SQL = '10kor_reviews_SQL';
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
    Res = (re.search('\d{2,}', Str) != None) or (re.search('-', Str) != None); 
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
    wrapper = root.find_class('detail-wrapper').pop();
    try:
        elem = wrapper.xpath("//div[@itemprop='description']")[0];
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
    fullPath = r'images\kor10' + itemLink;
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
                    print '=============================================================================================' + sys.exc_info()[0]
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
    main_image_div = None;
    try:
        main_image_div = root.find_class('photo').pop(); # Забираем основное фото
    except:
        pass;
    if main_image_div is not None:
        for imageLink in main_image_div.iterlinks():
            if '/upload/iblock/' in imageLink[2]:
                res.append(site_url + imageLink[2]);
            
    resStr = ';'.join(res); 
    return resStr;

def ParseName(root, tree):
    right_col = root.find_class('col-right').pop();
    return right_col.xpath("//h1[@itemprop='name']/text()")[0]; #/h1[@itemprop='name']/text()"

def ParseDesc(desc_div, desc_div_specs, tree):
    res = '';
    if desc_div is not None:  
        for child in desc_div.getchildren():
            res += html.tostring(child, encoding='utf-8').replace(';', ',');
         
    if desc_div_specs is not None:  
        for child in desc_div_specs.getchildren():
            res += html.tostring(child, encoding='utf-8').replace(';', ',');
    #print res;
    return res;

def ParseSKU(desc_div, tree, sku_default):
    Result = {};
    root = tree.getroot();
    # Парсим артикул - он у них отдельно
    cart_form = root.get_element_by_id('cart-form');
    try:
        sku_span = cart_form.xpath('./div/span').pop();
    except:
        sku_span = cart_form.find_class('hint').pop();
    if sku_span is not None:
        Result[sku_span.text_content().strip()] = '';  
    if len(Result) == 0:
        Result[sku_default] = '';                     
    return Result;

def GetLastLink(part):
    last_link = '';
    if os.path.exists(ParsedPart.format(part)):
        done_file = open(ParsedPart.format(part), 'r+', 0);
        try:
            lines = done_file.readlines();
            if lines.count > 0: 
                last_link = lines[-1]; 
        except:
            pass; 
        done_file.close();
    return last_link.strip();

def ParseItems(linkLines, lock, part):
    ResFileExisted = os.path.exists(CSVFilePart.format(part));
    last_link = GetLastLink(part);
    res_file = open(CSVFilePart.format(part), 'a+', 0);
    done_file = open(ParsedPart.format(part), 'a+', 0);
    try:
        if not ResFileExisted: 
            res_file.write('{0};{1};{2};{3};{4}\n'.format('sku', 'name', 'desc', 'group', 'img'));
        for itemLink in linkLines:
            itemLink = itemLink.strip();
            if (last_link != '') and (last_link != itemLink):
                continue;
            last_link = ''; # Что бы крутилось дальше
            print 'Opening: ' + site_url + itemLink;
            try:
                page = urlopen(site_url + itemLink, timeout = 10000);
                tree = html.parse(page);
            except BaseException:
                time.sleep(30);
                page = urlopen(site_url + itemLink, timeout = 10000);
                tree = html.parse(page);
                print '=============================================================================================' + sys.exc_info()[0] 
            root = tree.getroot(); 
            name_str = ParseName(root, tree);
            print 'Name: ' + name_str;
            img_str = ParseImages(root, tree).strip();
            print 'Images links: ' + img_str;
            if img_str != '':
                img_str = savepics(img_str, itemLink);
                
            print 'Images paths:' + img_str;    
            desc_div = ParseDescElement(root, tree);
            desc_div_specs = ParseSpecsElement(root, tree);    
            
            # основная операция
            SKUs_NameDesc_dict = ParseSKU(desc_div_specs, tree, name_str);
            
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
            done_file.write(itemLink + '\n');
    finally:
        done_file.close();
        res_file.close();  
        

def createThread(threads, lock, threadItems):
    t = threading.Thread(target=ParseItems, args=(threadItems[:], lock, len(threads))); 
    threads.append(t);
       
def IsItemsCached():
    return os.path.exists(CACHEFile) and os.path.getsize(CACHEFile) > 0;

def CacheItems():
    items_cache = open(CACHEFile, 'w');
    try:  
        MainMenuLinks = [];
        #if not os.path.exists(imagesDir):
            #os.makedirs(imagesDir);
        page = urlopen(site_url + '/catalog');
        tree = html.parse(page);
        root = tree.getroot();
        catalog_elem = root.get_element_by_id('catalog');
        #catalog_elem = catalog_elem.find_class('inner').pop();
        if catalog_elem is not None:
            MainMenuItems = catalog_elem.find_class('menu').pop();
            #print MainMenuItems;
            #парсим категории
            if (MainMenuItems is not None) and (MainMenuItems.tag == 'ul'): 
                for MainMenuItem in MainMenuItems:
                    #print MainMenuItem;
                    #print tostring(MainMenuItem);
                    for link in MainMenuItem.iterlinks():
                        if 'catalog' in link[2]:
                            MainMenuLinks.append(link[2]);
                            print 'MainMenu link:' + link[2];
        
        #Обходим все страницы   
        for MainMenuLink in MainMenuLinks:
            page_num = 1; 
            ItemsEnded = False;
            First_stored = False;
            while not ItemsEnded:
                try:
                    print 'Opening: ' + site_url + MainMenuLink + '?PAGEN_1={0}'.format(page_num);
                    page = urlopen(site_url + MainMenuLink + '?PAGEN_1={0}'.format(page_num), timeout = 10000);
                    tree = html.parse(page);
                    root = tree.getroot();
                    lst = root.find_class('product-list').pop();
                    ItemsEnded = True;
                    for link in lst.iterlinks():
                        if re.search('^/catalog/[A-Za-z_0-9]+/[A-Za-z_0-9]+/$', link[2]):
                            if not First_stored:
                                First_item = link[2];
                                First_stored = True;
                            if (page_num != 1) and (First_item == link[2]):
                                ItemsEnded = True;
                                break;
                            else: 
                                ItemsEnded = False;
                            print 'Cached:' + link[2];
                            items_cache.write(link[2] +'\n'); 
                except:
                    print site_url + MainMenuLink + '?PAGEN_1={0}'.format(page_num) + ' is broken!!!';
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
        if len(threadItems) >= 5000:
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