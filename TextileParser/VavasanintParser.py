# -*- coding: utf-8 -*- 

import mechanize, re, urllib, os

'''
Created on 20 июля 2015 г.

@author: YSklyarov
'''

SiteURL = 'http://www.vivasanint.com';
CatalogURL = SiteURL + '/catalog/';
ItemUrl = '<a href="(.+)" class="own-tovarmini ot-with_border nomargin">';

# Ссылки на категории товаров - проще внести руками, дабы сократить время работы скрипта
CategoryURLs = {
                '/catalog/the-well-groomed-body/': 3,
                '/catalog/silky-locks/': 2,
                '/catalog/line-lagerbier-smile-without-wrinkles/': 2,
                '/catalog/the-line-of-youth-viva-beauty/': 2,
                '/catalog/the-world-of-fragrances/': 3,
                '/catalog/line-healthy-nutrition/': 1,
                '/catalog/the-line-in-a-healthy-body-healthy-spirit/': 4,
                '/catalog/cozy-house/': 1,
                '/catalog/decorative-cosmetics-locherber/': 1,
                '/catalog/the-line-is-clean-in-your-house/': 1,
                '/catalog/line-ambiance/': 1 
                };
                
CategoryBreadcrumb = '<ol class="breadcrumb">(.+)';
# Последний элемент - название товара

ImageHTML = '<img src="(.+)" alt=".+" class="img-responsive center-block"/>';
DescHTML1 = '<div id="description" class="tab_content">(.+)<div id="mode" class="tab_content">';
DescHTML2 = '<div id="mode" class="tab_content">(.+)<div id="ingridients" class="tab_content">';  
DescHTML3 = '<div id="ingridients" class="tab_content">(.+)<h2>Отзывы о товаре';  
                    
def striphtml(data, addBRs):
    #print data
    data = data.replace('<h4 class="panel-title">', '%br%%b%');
    data = data.replace('</h4>','</b>');
    p = re.compile(r'<.{4,}?>');
    data = p.sub('', data);
    data = data.replace('%br%%b%', '<br><b>');
    #if addBRs:
        #data = data.replace('</a>','<br>')
    #else:
    data = data.replace('</a>', '')
    # Убираем пробелы(больше одного за раз)
    p = re.compile("\s+")
    data = p.sub(' ', data)
    # Убираем перенос строки
    p = re.compile("\n|\r")
    data = p.sub('<br>', data)
    data = data.replace(';', ',')
    data = data.replace('Подробнее', '')    
    return data.replace('Купить товар', '');

def savepic(url):
    resource = urllib.urlopen(url);
    urlparts = url.split('/');
    imagename = "viva_images\{0}".format(urlparts[-1]);
    if not os.path.isfile(imagename):
        out = open(imagename, 'wb');
        out.write(resource.read());
        out.close(); 
        print imagename + ' saved';
    else:
        print imagename + ' passed';

def ParseCategoryForItemURLs(ItemURLs, text):
    #print text;
    CategoryItemURLs = re.findall(ItemUrl, text);
    for URL in CategoryItemURLs:
        ItemURLs.append(URL);
    
def ParseItem(text):
    name_str = '';
    desc_str = '';
    image_str ='';
    category_str = '';
    #print text
    BreadCrumbs = re.findall(CategoryBreadcrumb, text, re.IGNORECASE);
    for BreadCrumb in BreadCrumbs: 
        Parts = re.findall('<li>(.+)</li><li>(.+)</li><li>(.+)</li><li>(.+)</li>', BreadCrumb);
        for Part in Parts[0]:
            strippedPart = striphtml(Part, False); 
            if (strippedPart != 'Каталог продукции') and (strippedPart != 'Главная страница'):
                if (Part == Parts[0][-1]):
                    name_str = strippedPart;
                else:
                    # Категория 
                    if (category_str != ''):
                        category_str += '|';
                    category_str += strippedPart;
    Images = re.findall(ImageHTML, text);
    for Image in Images:
        ImagesArray = Image.split('/')
        image_str += ImagesArray[len(ImagesArray) - 1];
        savepic(SiteURL + Image); 
    #print text   
    Descs = re.findall(DescHTML1, text, re.DOTALL);
    for Desc in Descs:   
      desc_str += striphtml(Desc, True);  
    Descs = re.findall(DescHTML2, text, re.DOTALL);
    for Desc in Descs:
      desc_str += striphtml(Desc, True);  
    Descs = re.findall(DescHTML3, text, re.DOTALL);
    for Desc in Descs:   
     # print Desc
      desc_str += striphtml(Desc, True);
   # print desc_str
    # Конвертим в юникод
    name_str = name_str.decode('utf8', errors='ignore').encode('windows-1251', errors='ignore');
    desc_str = desc_str.decode('utf8', errors='ignore').encode('windows-1251', errors='ignore');
    image_str = image_str.decode('utf8', errors='ignore').encode('windows-1251', errors='ignore');
    category_str = category_str.decode('utf8', errors='ignore').encode('windows-1251', errors='ignore');
    f.write('{0};{1};{2};{3}\n'.format(name_str, desc_str, image_str, category_str)); 
    #print text; 

br = mechanize.Browser();
# Browser options
br.set_handle_equiv(True);
br.set_handle_redirect(True);
br.set_handle_referer(True);
br.set_handle_robots(False);
br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')];
ItemURLs = [];

f = open('VIVASANINT_parse-results.csv', 'w');
try:
    f.write('{0};{1};{2};{3}\n'.format('Name', 'Desc', 'Img', 'Group')); 
    for CurrentCategory, pageCount in CategoryURLs.items():
        for i in range(pageCount):
            page = br.open(SiteURL + CurrentCategory + '?PAGEN_1={0}'.format(i + 1));
            page_text = page.read();
            print 'Parsing {0} page of category: '.format(i + 1) + CurrentCategory;
            ParseCategoryForItemURLs(ItemURLs, page_text);
    
    for CurrentItem in ItemURLs:
        page = br.open(SiteURL + CurrentItem);
        page_text = page.read();
        print 'Parsing Item: ' + CurrentItem;
        ParseItem(page_text);
                
except:
    f.close();
    raise
            