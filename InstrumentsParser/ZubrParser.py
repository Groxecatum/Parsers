# -*- coding: utf-8 -*- 

'''
Created on 28.08.2015.

@author: YSklyarov
'''
import os;
import re;
from urllib2 import urlopen;
import lxml.html as html;

#-----------------------------------------------------------------

site_url='http://zubr.ru';
imagesDir = 'instrument_images';
CSVFile = 'instrument_parse-results.csv';
CACHEFile = 'itemlinks.txt';
formatStr = '{0};{1};{2};{3};{4}\n';
#-------------------------------------------------------------------   

def PrettifyCategoryStr(Str):
    Str = re.sub("\s+|\n|\r", '', Str);
    return Str;

def tabletoList(tableElem):
    table = [];
    for tbody in tableElem.getchildren():
        for row in tbody.getchildren():
            tableRow = [];
            for col in row.getchildren():
                tableRow.append(col.text_content().strip());
            table.append(tableRow);
    return table;            

def IsSKU(): #строка содержит 5+ цифр(подряд?) 
    pass;
  
def getNameStrFromVertical(table): # Один артикул - обходим всю таблицу
    pass;

def getNameStrFromHorizontal(row): # обходим только один ряд. кроме первого столбца - артикула
    pass;           

def ParseSKU_DESC(desc_div, tree):
    Result = {};
    for child in desc_div.getchildren():
        if child.tag == 'table':
            table = tabletoList(child);
            # если артикулов несколько - уточняем название товара в скобках
            if (table[0][0] == 'Артикул'):
                # если артикул один - называем как есть
                # таблица построена вертикально 
                if IsSKU(table[0][1]):    
                    Result[table[0][1]] = getNameStrFromVertical();  
                else:
                    for row in table:
                        first = True;
                        for col in row.getchildren():
                            if not first:    
                                cols_str += col.text_content();
                            first = False;
                        Result[row[0]] = '({0})'.format(cols_str);  
            
            
   
    desc_div.xpath();
    pass;

def ParseName(root, tree):
    box = root.get_element_by_id('content-box');
    way = box.find_class('way').pop();
    way = way.text_content();
    name = way.split('/');
    return name[-1].strip();

def ParseDescDiv_spec(root, tree):
    return root.get_element_by_id('specifications');

def ParseDescDiv_features(root, tree): 
    return root.get_element_by_id('features'); 

def ParseDesc(desc_div_spec, desc_div_features, tree):
    res = ''; 
    for child in desc_div_features.getchildren():
        res += html.tostring(child).replace(';', ',');
    for child in desc_div_spec.getchildren():
        res += html.tostring(child).replace(';', ',');
    #print res;
    return res;

def ParseImages(root, tree):
    res = [];
    gallery = root.find_class('item-gallery');
    for galleryClass in gallery:
        for imageLink in galleryClass.iterlinks():
            if 'type=resize&w=800&h=600' in imageLink[2]:
                res.append(site_url + imageLink[2]);
    resStr = ';'.join(res); 
    return resStr;

def ParseCategory(root, tree):
    box = root.get_element_by_id('content-box');
    way = box.find_class('way').pop();
    way = way.text_content();
    wayParts = way.split('/');
    way = '';
    for wayPart in wayParts:
        if wayPart != wayParts[-1]:
            wayPart.strip(); 
            way += PrettifyCategoryStr(wayPart).strip();
            if wayPart != wayParts[-2]:
                way += '|';
    return way;

def savepics(imgs, itemLink):
    itemLink = itemLink.strip().replace('/', '\\');
    fullPath = r'images\zubr' + itemLink;
    if not os.path.exists(fullPath):
        os.makedirs(fullPath);
    for img in imgs.split(';'):
        resource = urlopen(img);
        #urlparts = img.split('/');
        
        imagename = "{0}\\{1}".format(fullPath, itemLink.split('\\')[-1] + '.png');
        if not os.path.exists(imagename):
            out = open(imagename, 'wb');
            try:
                out.write(resource.read());
            finally:
                out.close(); 
            print imagename + ' saved';
        else:
            print imagename + ' passed';

def IsItemsCached():
    return os.path.exists(CACHEFile);

def CacheItems():
    items_cache = open(CACHEFile, 'w');
    try:  
        MainMenuLinks = [];
        if not os.path.exists(imagesDir):
            os.makedirs(imagesDir);
        page = urlopen(site_url);
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
                        #print link[2];
                        items_cache.write(link[2] +'\n');
                        
        items_cache.close();
    except:
        items_cache.close();
        raise;

f = open(CSVFile, 'w');
try:
    f.write('{0};{1};{2};{3};{4};{5};{6};{7};{8};\n'.format('sku', 'name', 'desc', 'group', 'img', 'adImg1', 'adImg2', 'adImg3', 'adImg4'));
    if not IsItemsCached():
        CacheItems();                  
    items_cache = open(CACHEFile, 'r');
    try:
        for itemLink in items_cache.readlines():
            page = urlopen(site_url + itemLink);
            tree = html.parse(page);
            root = tree.getroot();
            
            name_str = ParseName(root, tree);
            print 'Name:' + name_str;
            group_str = PrettifyCategoryStr(ParseCategory(root, tree));
            print 'Category:' + group_str;
            img_str = ParseImages(root, tree);
            print 'Images:' + img_str;
            if img_str != '':
                savepics(img_str, itemLink);
                
            desc_div_features = ParseDescDiv_features(root, tree);    
            desc_div_spec = ParseDescDiv_spec(root, tree);
            
            # основная операция
            SKUs_NameDesc_dict = ParseSKU_DESC(desc_div_spec, tree);
            
            desc_str = ParseDesc(desc_div_spec, desc_div_features, tree);
            #print desc_str;
            for sku_str, name_additional  in SKUs_NameDesc_dict:
                f.write(formatStr.format(sku_str, 
                                        '{0}({1})'.format(name_str, name_additional), 
                                        desc_str,
                                        group_str, 
                                        img_str));
            #print itemLink.strip();
        items_cache.close();  
    except:
        items_cache.close();   
        raise       
    f.close();
except:
    f.close();
    raise