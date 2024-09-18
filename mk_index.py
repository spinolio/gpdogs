# Utility to create an index.html file from a json file containing dog information
# Usage: python tp.py <input file>
# Example: python mk_index.py input.json

import sqlite3
import json
import sys
import re

dogs = dict()
sections = list()

def active_handler(row, photo):
    return '<img src="{}" width="300" alt="{}"><br><a href="{}">{}</a> - {} year(s)<div class="sexbreed">{} - {}</div>\n'.format(photo, row['name'], row['href'], row['name'], row['age'], row['sex'], row['breed'] )

def gone_handler(row, photo):
    return '<img src="{}" width="300" alt="{}"><br>{} - {} year(s)<div class="sexbreed">{} - {}</div>Adopted: {}\n'.format(photo, row['name'], row['name'], row['age'], row['sex'], row['breed'], row['date_adopted'])


sections.append(('Adoptable Dogs - Recently Added', active_handler,
                 "select iif(c.old_name is NULL, d.name, d.name || ' (' || c.old_name ||')') AS NAME, sex, breed, round(age,1) AS AGE, photo, href from dogs AS D left outer join name_change AS C ON d.id = c.id  where d.date_proc = (select max(date_proc) from file_proc) and julianday(date_added) >= (julianday()-14) order by name"))
sections.append(('Adoptable Dogs - Classics!', active_handler,
                 "select iif(c.old_name is NULL, d.name, d.name || ' (' || c.old_name ||')') AS NAME, sex, breed, round(age,1) AS AGE, photo, href from dogs AS D left outer join name_change AS C ON d.id = c.id  where d.date_proc = (select max(date_proc) from file_proc)  and julianday(date_added) < (julianday()-14)order by name"))
sections.append(('Recent Adoptions', gone_handler,
"select iif(c.old_name is NULL, d.name, d.name || ' (' || c.old_name ||')') AS NAME, sex, breed, round(age,1) AS AGE, photo, date_adopted from dogs AS D left outer join name_change AS C ON d.id = c.id  where d.date_adopted > strftime('%Y-%m-%d %H:%M', julianday()-14) AND d.date_proc < (select max(date_proc) from file_proc) order by date_adopted desc, name"))


conn = sqlite3.connect('gpdogs.db')
conn.row_factory = sqlite3.Row

# Write the index.html file
with open('index.html', 'w') as f:
    f.write('<!DOCTYPE html>\n')
    f.write('<html>\n')
    f.write('<head>\n')
    f.write('<link rel="stylesheet" href="styles.css" />\n')
    f.write('<title>Great Plains SPCA</title>\n')
    f.write('</head>\n')
    f.write('<body>\n')
    f.write('<h1>Great Plains SPCA</h1>\n')
    for section, handler, query in sections:
        f.write('<h2>{}</h2>\n'.format(section))
        f.write('<section>\n')
        res = conn.execute(query)
        row = res.fetchone()
        while row is not None:
            f.write('<div class="dogbox">\n')
            photo = 'pics/{}'.format(row['photo'])
            f.write(handler(row, photo))
            f.write('</div>\n')
            row = res.fetchone()
        f.write('</section>\n')
    f.write('</body>\n')
    f.write('</html>\n')

conn.close()
sys.exit(0)
