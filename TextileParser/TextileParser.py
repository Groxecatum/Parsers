# -*- coding: windows-1251 -*- 

import mechanize, re

#==================== Consts =======================
SiteURL = 'http://helgatextil.ru/show_good.php?idtov={0}';
NameStr = '<td width=100%><b><font color=black size=4>(.+)</font></b></td>'; #Title?
DescriptionStr = '<tr><td colspan=2><br>(.+)</td></tr><TR>'; 
ImageStr = '<table border = 0 bgcolor=939C9B topmargin=0 leftmargin=0 rightmargin=0 cellspacing=1 cellpadding=0><tr><td bgcolor=white><img src="(.+)" border=0 alt=".+" width=500></td></tr></table>';
StartItem = 1001;

#==================== Code =======================

def striphtml(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

br = mechanize.Browser()
# Browser options
br.set_handle_equiv(True)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)

item_no = StartItem;
f = open('parse-results{0}.csv'.format(StartItem), 'w');
try:
    while item_no < 10000:
        print 'Searching {0} item'.format(item_no);
        result_str = '';
        names_str = '';
        descs_str = '';
        images_str ='';
        page = br.open(SiteURL.format(item_no));
        br._factory.encoding = 'windows-1251'
        br._factory._forms_factory.encoding = 'windows-1251'
        br._factory._links_factory._encoding = 'windows-1251'
        page_text = page.read();
        
        #print page_text
        Names = re.findall(NameStr, page_text);
        for Name in Names:
            print 'Name: ' + Name;
            names_str += Name;
            
        #print page_text
        Descriptions = re.findall(DescriptionStr, page_text);
        for Desc in Descriptions: 
            if Desc.find('Полное описание'):
                Desc = Desc.replace('Вернуться', '');
                Desc = Desc.replace('<br>', ' ');
                Desc = striphtml(Desc);
                DescParts = re.findall('[0-9А-Яа-я\-,\.() %:]+', Desc);
                for DescPart in DescParts:
                    print 'DescriptionPart: ' + DescPart;
                    descs_str += DescPart;
            
        Images = re.findall(ImageStr, page_text);
        for Img in Images:
            print 'Image: ' + Img;
            images_str += Img;
        
        f.write('{0};{1};{2};{3}\n'.format(item_no, names_str, descs_str, images_str));    
        item_no += 1;
except:
    f.close();
    raise

