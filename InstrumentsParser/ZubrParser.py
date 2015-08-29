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

site_url='http://zubr.ru/';
imagesDir = 'instrument_images';
CSVFile = 'instrument_parse-results.csv';
CACHEFile = 'itemlinks.txt';

#-------------------------------------------------------------------   

def PrettifyCategoryStr(Str):
    Str = re.sub("\s+|\n|\r", '', Str);
    return Str;

def ParseSKU_DESC(desc_div, tree):
    # если артикул один - называем как есть
    # если артикулов несколько - уточняем название товара в скобках
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
    return tree.tostring(desc_div_spec.drop_tag()) + tree.tostring(desc_div_features.drop_tag());

def ParseImages(root, tree):
    res = [];
    images = root.find_class('gallery__image');
    for image in images:
        for elem in image.getchildren():
            if elem.tag == 'a':
                res.append(elem.get('href'));
                
    return res;

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

def savepic(img, folderPath):
    PathParts = folderPath.split('/');
    Path = imagesDir;
    for pathPart in PathParts:
        Path += pathPart; 
        if not os.path.exists(Path):
            os.makedirs(Path);
    resource = urlopen(site_url + img);
    urlparts = img.split('/');
    imagename = "{0}\{1}".format(folderPath, urlparts[-1]);
    if not os.path.exists(imagename):
        out = open(imagename, 'wb');
        out.write(resource.read());
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
    f.write('{0};{1};{2};{3};{4}\n'.format('sku', 'name', 'desc', 'group', 'img', 'adImg1', 'adImg2', 'adImg3'));
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
            if not (img_str != ''):
                savepic(img_str, group_str);
                
            desc_div_features = ParseDescDiv_features(root, tree);    
            desc_div_spec = ParseDescDiv_spec(root, tree);
            
            # основная операция
            SKUs_NameDesc_dict = ParseSKU_DESC(desc_div_spec, tree);
            
            desc_str = ParseDesc(desc_div_features, desc_div_spec, tree);
            
            for sku_str, name_additional  in SKUs_NameDesc_dict:
                f.write('{0};{1};{2};{3};{4}\n'.format(sku_str, 
                                                       '{0}({1})'.format(name_str, name_additional), 
                                                       desc_str,
                                                       group_str, 
                                                       img_str));
            print itemLink.strip();
        items_cache.close();  
    except:
        items_cache.close();   
        raise       
    f.close();
except:
    f.close();
    raise