# Utility to load dogs from a JSON file into the gpdogs database
# Usage: python tp.py <input file>
# Example: python mk_index.py input.json

import json
import sys
import re
import sqlite3
import os

# Compile regular expression to extract number that follows 'aid='
aid_re = re.compile(r'aid=(\d+)')

# Compile regular expression to extract timestamp from filename
date_re = re.compile(r'(\d{4}-\d{2}-\d{2})-(\d{2})')

# Function to return floating point years from age string in the forms 'x years', 'y months', or 'x years y months'
def age_to_years( age):
    m = re.search(r'(\d+) years?', age)
    if m:
        years = int(m.group(1))
    else:
        years = 0
    m = re.search(r'(\d+) months?', age)
    if m:
        months = int(m.group(1))
    else:
        months = 0
    return years + months / 12

def file_processed(c, proc_file):
    c.execute('SELECT date_proc from file_proc where fname=?', (proc_file,))
    row = c.fetchone()
    if row is not None:
        return True
    return False

def save_processed(c, proc_file, fdate):
    c.execute('INSERT INTO file_proc (fname, date_proc, err_msg) VALUES (?,?, NULL)', (proc_file, fdate))

def get_aid( obj):
    m = re.search(aid_re, obj['href'])
    if m:
        return m.group(1)
    else:
        return None

def get_dttm( input_file):
    m = re.search(date_re, input_file)
    if m:
        return '{} {}:00'.format(m.group(1), m.group(2))
    else:
        return None

def load_dog(c, aid):
    c.execute('SELECT name, breed, age FROM dogs WHERE id = ?', (aid,))
    row = c.fetchone()
    if row is None:
        return None
    return {'name': row[0], 'breed': row[1], 'age': row[2]}

def store_dog(c, aid, obj, fdate):
    try:
        age = age_to_years(obj['age'])
        print('Insert/update dog: {}:{}'.format(aid, obj['name']))
        c.execute('INSERT INTO dogs (id, name, href, photoUrl, sex, breed, age, date_added, date_proc) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=?, age=?, photoUrl=?, date_proc=?',
                  (aid, obj['name'], obj['href'], obj['photoUrl'], obj['sex'], obj['breed'], age, fdate, fdate, obj['name'], age, obj['photoUrl'], fdate))
    except KeyError:
        print('Missing field in object: {}'.format(obj))
    except sqlite3.IntegrityError:
        print('Duplicate entry: {}'.format(aid))

def move_file( input_file):
    pass

################################################################################
# Main program
################################################################################

if len(sys.argv) < 2:
    print("Usage: python load_dogs.py <input file(s)>")
    sys.exit(1)

# Connect to the database gpdogs.db
conn = sqlite3.connect('gpdogs.db')
c = conn.cursor()

# Process each file in the list. 

exit_err = None
current_dogs = set()
for i in range(1, len(sys.argv)):
    current_dogs.clear()
    input_file = sys.argv[i]
    proc_file=os.path.basename(input_file)
    if file_processed(c, proc_file):
        print('Already processed input file; Skipping: {}'.format(input_file))
        continue

    fdate = get_dttm(input_file)
    if fdate is None:
        exit_err = 'No date found in filename: {}'.format(input_file)
        break

    print('Processing: {} ========================'.format(input_file))
    with open(input_file) as f:
        data = json.load(f)
        for obj in data:
            aid = get_aid(obj)
            if aid is None:
                print('No aid found: {}'.format(obj['href']))
                break
            store_dog(c, aid, obj, fdate)
            current_dogs.add((aid, fdate))

        if exit_err is not None:
            print(exit_err)
            conn.close()
            sys.exit(1)

    id_where = '(' + ', '.join(["'{}'".format(d[0]) for d in current_dogs]) + ')'
    sql = 'UPDATE dogs SET date_adopted=? WHERE (date_adopted is null or date_added > date_adopted) and id not in ' + id_where
    print('SQL: ', sql)
    c.execute(sql, (fdate,))
    save_processed(c, proc_file, fdate)
    move_file(input_file)

conn.commit()
conn.close()
if exit_err is not None:
    print(exit_err)
    sys.exit(1)

sys.exit(0)
