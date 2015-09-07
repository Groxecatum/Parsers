# -*- coding: utf-8 -*- 

'''
Created on 30 авг. 2015 г.

@author: Grey
'''
import os;
import re;
import threading;
from urllib2 import urlopen;
import lxml.html as html;

#===================================================================================================================
site_url = 'http://www.stayer-tools.com';
CSVFilePart = 'stayer_parse-results-part-{0}.csv';
CACHEFile = 'itemlinks_stayer.txt';
formatStr = '{0};{1};{2};{3};{4}\n';
maxAdditionalImages = 8;
#===================================================================================================================
def ParseCategory(root, tree, IsMultipleSKUs): # если артикулов больше одного - тогда название входит как название группы
    way = root.find_class('navigator').pop();
    way = way.text_content();
    wayParts = way.split('/');
    wayParts.remove(wayParts[-1]);
    way = '';
    for wayPart in wayParts:
        wayPart = PrettifyStr(wayPart.strip());
        not_last_part_of_multisku = IsMultipleSKUs and (wayPart != PrettifyStr(wayParts[-1].strip()));
        not_last_part_of_singlesku = (not IsMultipleSKUs) and (wayPart != PrettifyStr(wayParts[-2].strip())); 
        if ((wayPart != PrettifyStr(wayParts[-1])) or IsMultipleSKUs) and (wayPart != 'STAYER'):   
            way += PrettifyStr(wayPart).strip();
            if not_last_part_of_singlesku or not_last_part_of_multisku:
                way += '|';
    return way;

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
    return root.find_class('item_desc').pop();

def savepics(imgs, itemLink):
    itemLink = itemLink.replace(site_url, '').strip();
    itemLink = itemLink[:-1];
    itemLink = itemLink.replace('/', '\\');
    fullPath = r'images\stayer' + itemLink;
    saved_imgs = [];
    if not os.path.exists(fullPath):
        os.makedirs(fullPath);
    for img in imgs.split(';'):
        if img != '':
            imagename = "{0}\\{1}".format(fullPath, img.split('/')[-1]);
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

def ParseImages(root, tree):
    res = [];
    main_image_div = root.find_class('photo_container').pop(); # Забираем основное фото
    for imageLink in main_image_div.iterlinks():
        if 'http://www.stayer-tools.com/files/' in imageLink[2]:
            res.append(imageLink[2]);
    
    additional_images = root.find_class('big_mini_img_t');
    if len(additional_images):        
        sub_image_div = root.find_class('big_mini_img_t').pop(); # Забираем доп. фото
        for imageLink in sub_image_div.iterlinks():
            if 'http://www.stayer-tools.com/files/' in imageLink[2]:
                res.append(imageLink[2]);
        while len(res) <= maxAdditionalImages:
            res.append('');
    resStr = ';'.join(res); 
    return resStr;

def ParseName(root, tree):
    title = root.find_class('right_tit').pop();
    return title.text_content().strip();

def ParseDesc(desc_div, tree):
    res = ''; 
    for child in desc_div.getchildren():
        res += html.tostring(child, encoding='utf-8').replace(';', ',');
    #print res;
    return res;

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
    table_div = desc_div.find_class('table_har').pop();  
    for child in table_div.getchildren():  
        if child.tag == 'table': 
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

def ParseItems(linkLines, lock, part):
    res_file = open(CSVFilePart.format(part), 'w+', 0);
    try:
        res_file.write('{0};{1};{2};{3};{4};{5};{6};{7};{8};{9};{10};{11};{12}\n'.format('sku', 'name', 'desc', 'group', 'img', 'adImg1', 'adImg2', 'adImg3', 'adImg4', 'adImg5', 'adImg6', 'adImg7', 'adImg8'));
        for itemLink in linkLines:
            itemLink = itemLink.strip();
            page = urlopen(itemLink, timeout = 5000);
            tree = html.parse(page);
            root = tree.getroot(); 
            print 'Item link:' + itemLink;
            name_str = ParseName(root, tree);
            print 'Name:' + name_str;
            img_str = ParseImages(root, tree).strip();
            print 'Images links:' + img_str;
            if img_str != '':
                img_str = savepics(img_str, itemLink);
                
            print 'Images paths:' + img_str;    
            desc_div = ParseDescElement(root, tree);    
            
            # основная операция
            SKUs_NameDesc_dict = ParseSKU_DESC(desc_div, tree, name_str);
            
            IsMultipleSKUs = len(SKUs_NameDesc_dict) > 1;
            
            group_str = PrettifyStr(ParseCategory(root, tree, IsMultipleSKUs));
            print 'Category:' + group_str;   
            desc_str = PrettifyStr(ParseDesc(desc_div, tree));
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
        MainMenuItems = root.find_class('catmenu');
        #print MainMenuItems;
        #парсим категории
        for MainMenuItem in MainMenuItems:
            #print MainMenuItem;
            #print tostring(MainMenuItem);
            for elem in MainMenuItem.getchildren():
                if elem.tag == 'ul':
                    for link in elem.iterlinks():
                        if site_url + '/' + 'catalog' in link[2]:
                            MainMenuLinks.append(link[2]);
                            print 'MainMenu link:' + link[2];
            
        for MainMenuLink in MainMenuLinks:
            page = urlopen(MainMenuLink, timeout = 5000);
            tree = html.parse(page);
            root = tree.getroot();
            SubItems = root.find_class('z_group');
            last_cached_link = '';
            for SubMenuItem in SubItems:
                for link in SubMenuItem.iterlinks():
                    if ('item' in link[2]) and (link[2] != last_cached_link):
                        print 'Cached:' + link[2];
                        last_cached_link = link[2];
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
