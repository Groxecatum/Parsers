# -*- coding: UTF-8 -*- 
'''
Created on 12 мая 2016 г.

@author: YSklyarov
'''

#===================================================================================================================
input_filename = '10kor.csv';
output_filename = '10kor_done.csv';
groups_start_index = 3;
#===================================================================================================================

input_file = open(input_filename, 'r', 0);
output_file = open(output_filename, 'w+', 0);
try:
    index = 0;
    last_sku = 0;
    fillable_line = '';
    for line in input_file.readlines():
        if index == 0:
            index += 1;
            output_file.write(line);
        else:
            line_arr = line.split('^');
            if last_sku <> line_arr[0]:
                output_file.write('^'.join(fillable_line));
                fillable_line = line_arr; # теперь заполняем ЭТУ строку. номер группы сбрасываем
                group_num = 1;
                last_sku = line_arr[0];
            else:
                if fillable_line:
                    fillable_line[groups_start_index + group_num] = line_arr[groups_start_index];
                    group_num += 1; 
            index += 1;
finally:
    output_file.close();
    input_file.close();
        