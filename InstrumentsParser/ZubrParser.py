# -*- coding: utf-8 -*- 

'''
Created on 28.08.2015.

@author: YSklyarov
'''
import os;
from urllib2 import urlopen;
import lxml.html as html;

#-----------------------------------------------------------------

site_url='http://zubr.ru/';
imagesDir = 'instrument_images';
CSVFile = 'instrument_parse-results.csv';
CACHEFile = 'itemlinks.txt';

#-------------------------------------------------------------------

def ParseSKU(root, tree):
    pass;
def ParseName(root, tree):
    pass;
def ParseDesc(root, tree):
    pass;
def ParseImages(root, tree):
    pass;
def ParseCategory(root, tree):
    pass;

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
    f.write('{0};{1};{2};{3};{4}\n'.format('sku', 'name', 'desc', 'img', 'group'));
    if not IsItemsCached():
        CacheItems();                  
    items_cache = open(CACHEFile, 'r');
    try:
        for itemLink in items_cache.readlines():
            page = urlopen(site_url + itemLink);
            tree = html.parse(page);
            root = tree.getroot();
            sku_str = ParseSKU(root, tree);
            name_str = ParseName(root, tree);
            desc_str = ParseDesc(root, tree);
            group_str = ParseCategory(root, tree);
            img_str = ParseImages(root, tree);
            savepic(img_str, group_str);
            f.write('{0};{1};{2};{3};{4}\n'.format(sku_str, name_str, desc_str, img_str, group_str));
            print itemLink.strip();
        items_cache.close();  
    except:
        items_cache.close();   
        raise       
    f.close();
except:
    f.close();
    raise