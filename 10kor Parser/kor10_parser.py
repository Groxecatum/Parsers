# -*- coding: UTF-8 -*- 

#from __future__ import unicode_literals;
import os;
import re;
import threading;
import time;
import sys;
import urllib2;
import lxml.html as html;

#===================================================================================================================
site_url = 'http://10kor.ru';
pages_ended_str = u'В этой категории нет ни одного товара.';
pages_ended_str2 = u'Не найдено ни одного товара.'
CSVFilePart = '10kor_parse-results-part-{0}.csv';
reviews_file_part = '10kor_reviews_part-{0}.txt';
ParsedPart = '10kor_parsed-{0}.txt';
CACHEFile = 'itemlinks_10kor.txt';
reviews_SQL = '10kor_reviews_SQL';
formatStr = u"{0}~{1}~{2}~{3}~{4}\n";
maxAdditionalImages = 8;
#===================================================================================================================

def ParseAndPlaceReviews(root, part, Name):
    reviews_file = open(reviews_file_part.format(part), 'a+', 0);
    try:
        reviews = root.find_class('respond');
        for review in reviews:
            username_elem = review.xpath('//strong')[0];
            review_name_date = username_elem.text_content().split(',');
            review_rating = '100';
            stars_bar_div = review.find_class('stars-bar-active');
            if stars_bar_div:
                stars_bar_div = review.find_class('stars-bar-active').pop();  
                review_rating = unicode(stars_bar_div.attrib['style'][7:-1]);
            review_text_elem = review.xpath('//em')[0];
            review_text = html.tostring(review_text_elem, encoding='UTF-8').decode('utf-8', 'ignore');
            
            FieldsStr = review_name_date[0] + ', ' +  review_text + ', ' + review_rating + ', ' + str(1) + ', ' + review_name_date[1]  + ', ' +  review_name_date[1];
            reviews_file.write((Name + u'\n').encode('utf-8', 'ignore'));
            reviews_file.write(u'INSERT INTO oc_reviews(review_id, product_id, customer_id, author, text, rating, status, date_added, date_modified) VALUES({0});\n'.format(FieldsStr).encode('utf-8', 'ignore'));    
    finally:
        reviews_file.close();
    
    return True;

def ParseCategory(root): # если артикулов больше одного - тогда название входит как название группы
    way = root.find_class('breadcrumb').pop();
    category = way.text_content();
    #for part in way.getchildren():
        #category = part.text_content(); 
        #if (part.tag == 'a'):
            #category = part.attrib['title'];
    #category = category;
    category = category.replace(' / ', '|');
    category = category.replace('/ ', '|');
    category = category.replace(' /', '|');
    return category.replace('/', '|');

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

def Encode(ustr):
    return ustr.decode('utf-8', 'ignore').encode('windows-1251', 'ignore');

def ParseDescElement(root):
    wrapper = root.find_class('detail-wrapper').pop();
    try:
        elem = wrapper.xpath("//div[@itemprop='description']")[0];
    except KeyError:
        elem = None;
    return elem;

def ParseSpecsElements(root):
    try:
        elem = root.find_class('atr');
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
    for img in imgs.split('~'):
        if img != '':
            imagename = "{0}\\{1}".format(fullPath, img.split('/')[-1]);
            saved_imgs.append(imagename.replace('\\', '/'));
            if not os.path.exists(imagename):
                print 'Opening image: ' + img;
                try:
                    resource = urllib2.urlopen(img, timeout = 10000);
                except: 
                    time.sleep(30);
                    resource = urllib2.urlopen(img, timeout = 10000);
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
            
    return u'~'.join(saved_imgs);

def ParseImages(root):
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
            
    resStr = '~'.join(res); 
    return resStr;

def ParseName(root):
    right_col = root.find_class('col-right').pop();
    return right_col.xpath("//h1[@itemprop='name']/text()")[0]; #/h1[@itemprop='name']/text()"

def ParseDesc(desc_div):
    res = '';
    if desc_div is not None:  
        for child in desc_div.getchildren():
            res += html.tostring(child, encoding='UTF-8');
            
    return res;

def ParseSKU(specs_divs, sku_default):
    Result = 0;
    for specs_div in specs_divs:
        text = specs_div.text_content();
        name = u'Артикул: ';
        if name in text:
            Result = text.replace(name, '');
            break;                    
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
            res_file.write('{0}~{1}~{2}~{3}~{4}\n'.format('sku', 'name', 'desc', 'group', 'img'));
        for itemLink in linkLines:
            itemLink = itemLink.strip();
            if (last_link != '') and (last_link != itemLink):
                continue;
            last_link = ''; # Что бы крутилось дальше
            print 'Opening: ' + site_url + itemLink;

                #page = urlopen(site_url + itemLink, timeout = 10000);
            request = urllib2.Request(site_url + itemLink);
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 9.1; rv:10.0) Gecko/20151031 Firefox/40.0'); 
            opener = urllib2.build_opener();                                   
            page = opener.open(request).read();
            root = html.fromstring(page);
            
            name_str = ParseName(root);
            print 'Name: ' + name_str;
            img_str = ParseImages(root).strip();
            print 'Images links: ' + img_str;
            if img_str != '':
                img_str = savepics(img_str, itemLink);
                
            print 'Images paths:' + img_str;    
            desc_div = ParseDescElement(root);
            div_specs = ParseSpecsElements(root);    
            
            # основная операция
            SKU = ParseSKU(div_specs, name_str);
            
            group_str = ParseCategory(root);
            print 'Category:' + group_str;   
            desc_str = PrettifyStr(ParseDesc(desc_div)).decode('utf-8', 'ignore');
            ParseAndPlaceReviews(root, part, name_str);
            #print desc_str;
            Overall_Str = formatStr.format(SKU, 
                                    name_str, 
                                    desc_str,
                                    group_str, 
                                    img_str);
            Overall_Str = Overall_Str.encode('utf-8', 'ignore');
            res_file.write(Overall_Str);
                                     
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
        page = urllib2.urlopen(site_url + '/catalog');
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
                    page = urllib2.urlopen(site_url + MainMenuLink + '?PAGEN_1={0}'.format(page_num), timeout = 10000);
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