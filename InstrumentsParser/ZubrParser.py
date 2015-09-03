# -*- coding: utf-8 -*- 

'''
Created on 28.08.2015.

@author: YSklyarov
'''
import os;
import re;
import threading;
import time;
from urllib2 import urlopen;
import lxml.html as html;

#-----------------------------------------------------------------

site_url='http://zubr.ru';
imagesDir = 'instrument_images';
CSVFile = 'instrument_parse-results.csv';
CSVFilePart = 'instrument_parse-results-part-{0}.csv';
CACHEFile = 'itemlinks.txt';
formatStr = '{0};{1};{2};{3};{4}\n';
maxAdditionalImages = 8;
#-------------------------------------------------------------------   
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

def tabletoList(tableElem):
    tableArray = [];
    for tbody in tableElem.getchildren():
        for row in tbody.getchildren():
            tableRow = [];
            for col in row.getchildren():
                tableRow.append(col.text_content().strip());
            if (tableRow != []):
                tableArray.append(tableRow);
    return tableArray;            

def IsSKU(Str): #строка содержит 5+ цифр(подряд?)
    Res = (re.search('\d', Str) != None) or (re.search('-', Str) != None); 
    return Res;
        
def getNameStrFromVertical(tableArray): # Один артикул - обходим всю таблицу Кроме первого элемента - шапка
    ResList = [];
    for idx, row in enumerate(tableArray):
        if idx:
            for col in row:
                pass;
            # если это последняя колонка(со значениями)
            ResList.append(DeleteLineWraps(col.strip()));
    return ','.join(ResList);

def getNameStrFromHorizontal(row): # обходим только один ряд. кроме первого столбца - артикула
    #first = True;
    ColsList = [];
    for idx, col in enumerate(row):
        if idx:    # Не значение артикула
            ColsList.append(DeleteLineWraps(col.strip()));
        #first = False; 
    return ','.join(ColsList);         

def ParseSKU_DESC(desc_div, tree, sku_default):
    Result = {};
    table_found = False;
    for child in desc_div.getchildren():
        if (child.tag == 'table') and (not table_found): # у некоторых товаров - 2 таблицы
            table_found = True;
            tableArray = tabletoList(child);
            # если артикулов несколько - уточняем название товара в скобках
            if (tableArray[0][0] == u'Артикул'):
                # если артикул один - называем как есть
                # таблица построена вертикально 
                if IsSKU(tableArray[0][1]):                              # Если элемент справа - артикул - забираем его
                    Result[tableArray[0][1]] = getNameStrFromVertical(tableArray); # и крепим к нему все свойства   
                else:
                    if IsSKU(tableArray[1][0]):   
                        for idx, row in enumerate(tableArray):
                            if idx:    #Не шапка
                                cols_str = getNameStrFromHorizontal(row);
                                Result[row[0]] = cols_str;
                    else: # Не нашли артикул - используем имя товара
                        Result[sku_default] = '';
                        
    return Result;

def ParseName(root, tree):
    box = root.get_element_by_id('content-box');
    way = box.find_class('way').pop();
    way = way.text_content();
    way = way.replace(u'г/г', u'г-г');
    name = way.split('/');
    return name[-1].strip();

def ParseDescDiv_spec(root, tree):
    return root.get_element_by_id('specifications');

def ParseDescDiv_features(root, tree): 
    return root.get_element_by_id('features'); 

def ParseDesc(desc_div_spec, desc_div_features, tree):
    res = ''; 
    for child in desc_div_features.getchildren():
        res += html.tostring(child, encoding='utf-8').replace(';', ',');
    for child in desc_div_spec.getchildren():
        res += html.tostring(child, encoding='utf-8').replace(';', ',');
    #print res;
    return res;

def ParseImages(root, tree):
    res = [];
    gallery = root.find_class('item-gallery');
    for galleryClass in gallery:
        for imageLink in galleryClass.iterlinks():
            if 'type=resize&w=800&h=600' in imageLink[2]:
                res.append(site_url + imageLink[2]);
    while len(res) <= maxAdditionalImages:
        res.append('');
    resStr = ';'.join(res); 
    return resStr;

def ParseCategory(root, tree, IsMultipleSKUs): # если артикулов больше одного - тогда название входит как название группы
    box = root.get_element_by_id('content-box');
    way = box.find_class('way').pop();
    way = way.text_content();
    way = way.replace(u'Слесарно/столярный', u'Слесарно\столярный' );
    wayParts = way.split('/');
    way = '';
    for wayPart in wayParts:
        if (wayPart != wayParts[-1]) or IsMultipleSKUs:
            wayPart = wayPart.strip(); 
            way += PrettifyStr(wayPart).strip();
            if (((not IsMultipleSKUs) and (wayPart != PrettifyStr(wayParts[-2].strip()))) or
                (IsMultipleSKUs and (wayPart != PrettifyStr(wayParts[-1].strip())))):
                way += '|';
    return way;

def savepics(imgs, itemLink):
    itemLink = itemLink.strip().replace('/', '\\');
    fullPath = r'images\zubr' + itemLink;
    saved_imgs = [];
    if not os.path.exists(fullPath):
        os.makedirs(fullPath);
    for idx, img in enumerate(imgs.split(';')):
        if img != '':
            imagename = "{0}\\{1}".format(fullPath, itemLink.split('\\')[-1] + str(idx + 1) + '.png');
            saved_imgs.append(imagename.replace('\\', '/'));
            if not os.path.exists(imagename):
                resource = urlopen(img);
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

def IsItemsCached():
    return os.path.exists(CACHEFile);

def CacheItems():
    items_cache = open(CACHEFile, 'w');
    try:  
        MainMenuLinks = [];
        if not os.path.exists(imagesDir):
            os.makedirs(imagesDir);
        page = urlopen(site_url + '/');
        tree = html.parse(page);
        root = tree.getroot();
        MainMenuItems = root.find_class('menu-pop-box');
        #print MainMenuItems;
        #парсим категории
        for MainMenuItem in MainMenuItems:
            #print MainMenuItem;
            #print tostring(MainMenuItem);
            for elem in MainMenuItem.getchildren():
                if elem.tag == 'a':
                    MainMenuLinks.append(elem.get('href'))
                    #print elem.get('href');
        
        #парсим подкатегории
        for MainMenuLink in MainMenuLinks:
            page = urlopen(site_url + MainMenuLink);
            tree = html.parse(page);
            root = tree.getroot();
            SubMenuItems = root.find_class('menu-sub-pop-box');
            for SubMenuItem in SubMenuItems:
                for link in SubMenuItem.iterlinks():
                    if 'witem' in link[2]:
                        print 'Cached:' + link[2];
                        items_cache.write(link[2] +'\n');
                        
        items_cache.close();
    except:
        items_cache.close();
        raise;
    
def ParseItems(linkLines, lock, part):
    f = open(CSVFilePart.format(part), 'w+');
    try:
        f.write('{0};{1};{2};{3};{4};{5};{6};{7};{8};{9};{10};{11};{12}\n'.format('sku', 'name', 'desc', 'group', 'img', 'adImg1', 'adImg2', 'adImg3', 'adImg4', 'adImg5', 'adImg6', 'adImg7', 'adImg8'));
        for itemLink in linkLines:
            page = urlopen(site_url + itemLink, timeout = 5000);
            tree = html.parse(page);
            root = tree.getroot(); 
            name_str = ParseName(root, tree);
            print 'Name:' + name_str;
            img_str = ParseImages(root, tree).strip();
            print 'Images links:' + img_str;
            if img_str != '':
                img_str = savepics(img_str, itemLink);
                
            print 'Images paths:' + img_str;    
            desc_div_features = ParseDescDiv_features(root, tree);    
            desc_div_spec = ParseDescDiv_spec(root, tree);
            
            # основная операция
            SKUs_NameDesc_dict = ParseSKU_DESC(desc_div_spec, tree, name_str);
            
            IsMultipleSKUs = len(SKUs_NameDesc_dict) > 1;
            
            group_str = PrettifyStr(ParseCategory(root, tree, IsMultipleSKUs));
            print 'Category:' + group_str;   
            desc_str = ParseDesc(desc_div_spec, desc_div_features, tree);
            desc_str = DeleteLineWraps(desc_str);
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
                with lock:
                    #file = open(CSVFile, 'a+');
                    #try:
                    f.write(formatStr.format(encodedKey, 
                                                name_str, 
                                                desc_str,
                                                group_str, 
                                                img_str));  
                    #finally:
                        #file.close();
            #time.sleep(5);
    finally:
        f.close();
        
def createThread(threads):
    t = threading.Thread(target=ParseItems, args=(threadItems[:], lock, len(threads))); 
    threads.append(t);
               
   
if not IsItemsCached():
    CacheItems();  
      
lock = threading.Lock();
threadItems = [];
threads = [];              
items_cache = open(CACHEFile, 'r');
try:
    for itemLink in items_cache.readlines():
        threadItems.append(itemLink);
        if len(threadItems) >= 500:
            threadItems = createThread(threads);
            threadItems = []; 
    if len(threadItems):
        createThread(threads);
        threadItems = [];    
    print len(threads);
    for thread in threads:
        thread.start();
        #thread.join();
        '''for itemLink in items_cache.readlines():
            page = urlopen(site_url + itemLink, timeout = 5000);
            tree = html.parse(page);
            root = tree.getroot(); 
            name_str = ParseName(root, tree);
            print 'Name:' + name_str;
            img_str = ParseImages(root, tree).strip();
            print 'Images links:' + img_str;
            if img_str != '':
                img_str = savepics(img_str, itemLink);
                
            print 'Images paths:' + img_str;    
            desc_div_features = ParseDescDiv_features(root, tree);    
            desc_div_spec = ParseDescDiv_spec(root, tree);
            
            # основная операция
            SKUs_NameDesc_dict = ParseSKU_DESC(desc_div_spec, tree, name_str);
            
            IsMultipleSKUs = len(SKUs_NameDesc_dict) > 1;
            
            group_str = PrettifyStr(ParseCategory(root, tree, IsMultipleSKUs));
            print 'Category:' + group_str;   
            desc_str = ParseDesc(desc_div_spec, desc_div_features, tree);
            desc_str = DeleteLineWraps(desc_str);
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
                f.write(formatStr.format(encodedKey, 
                                        name_str, 
                                        desc_str,
                                        group_str, 
                                        img_str));
            #print itemLink.strip();'''
    #items_cache.close();  
finally:
    items_cache.close();   
    #raise       
    #f.close();
#except:
    #f.close();
    #raise