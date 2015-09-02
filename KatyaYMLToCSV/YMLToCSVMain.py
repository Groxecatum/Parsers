# -*- coding: windows-1251 -*- 

'''
Created on 02 сент. 2015 г.

@author: YSklyarov
'''

import re;
import urllib2;
import lxml.etree as etree;
import os;

YMLFile = 'irr.yml'

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

def savepic(imageurl):
    imageurl = DeleteLineWraps(imageurl);
    name = imageurl.split('/')[-1].strip();
    path = "images\{0}".format(name);
    if not os.path.exists(path):
        try:
            resource = urllib2.urlopen(imageurl);
            out = open(path, 'wb');
            out.write(resource.read());
            out.close(); 
            print imageurl + ' saved';
        except urllib2.HTTPError:
            print imageurl + ' not found';
            
        
    else:
        print imageurl + ' passed';

f = open('KResults.csv', 'w+');
f.write('{0};{1};{2};{3};{4};{5}\n'.format('id', 'name', 'description', 'url', 'price', 'picturename'));
try:
    parser = etree.XMLParser(encoding = 'windows-1251') 
    tree = etree.parse(YMLFile, parser);
    offers = tree.xpath('//shop/offers').pop();
    for offer in offers.getchildren():
        offer_id = offer.get('id');
        offer_available = offer.get('available') == 'true';
        for offer_detail in offer:
            if offer_detail.tag == 'url':
                url_str = DeleteLineWraps(etree.tostring(offer_detail, method='text'));
            if offer_detail.tag == 'price':
                price_str = DeleteLineWraps(etree.tostring(offer_detail, method='text'));
            if offer_detail.tag == 'name':
                name_str = DeleteLineWraps(etree.tostring(offer_detail, method='text', encoding = 'windows-1251'));
            if offer_detail.tag == 'description':
                desc_str = DeleteLineWraps(etree.tostring(offer_detail, method='text', encoding = 'windows-1251'));
            if offer_detail.tag == 'picture':
                picture_url = DeleteLineWraps(etree.tostring(offer_detail, method='text'));
                savepic(picture_url);
                img_str = picture_url.split('/')[-1];
        f.write('{0};{1};{2};{3};{4};{5}\n'.format(offer_id, name_str, desc_str, url_str, price_str, img_str));        
finally:
    f.close();