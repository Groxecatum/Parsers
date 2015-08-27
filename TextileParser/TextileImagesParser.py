# -*- coding: windows-1251 -*- 

'''
Created on 23 июня 2015 г.

@author: YSklyarov
'''
import urllib

def savepic(imagename):
    resource = urllib.urlopen(url + imagename);
    out = open("images\{0}".format(imagename), 'wb');
    out.write(resource.read());
    out.close(); 
    print imagename + ' saved';
    
    
url = 'http://helgatextil.ru/admin/pictures/';
ext = '.jpg';

item_no = 1001;

while item_no < 10000:
    name = str(item_no) + 'b' + ext;
    savepic(name);
    name = str(item_no) + 's' + ext;
    savepic(name);
    item_no += 1;