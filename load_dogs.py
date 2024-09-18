# Utility to load dogs from a JSON file into the gpdogs database
# Usage: python tp.py <input file>
# Example: python mk_index.py input.json

import json
import sys
import re
import sqlite3
import os
import zlib

IN_DIR = 'infiles'
ARCHIVE_DIR = 'archive'
BAD_DIR = 'badfiles'
PROC_NO = 0
PROC_YES = 1
PROC_DUP = 2

# Compile regular expression to extract jpg file name
jpg_re = re.compile(r'\b[A-Za-z0-9-]+\.(?:jpg|gif)$')

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

def file_processed(c, proc_file, size, adler, fdate):
    c.execute('SELECT date_proc from file_proc where fname=?', (proc_file,))
    row = c.fetchone()
    if row is not None:
        return PROC_YES
    c.execute('select fsize, adler32 from file_proc where date_proc=(select max(date_proc) from file_proc where date_proc <= ?)', (fdate,))
    row = c.fetchone()
    if row is not None:
        if row[0] == size and row[1] == adler:
            return PROC_DUP
    return PROC_NO

def save_processed(c, proc_file, fdate, size, adler):
    c.execute('INSERT INTO file_proc (fname, date_proc, fsize, adler32) VALUES (?,?, ?, ?)', (proc_file, fdate, size, adler))

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

def store_dog(c, aid, obj, fdate):
    try:
        age = age_to_years(obj['age'])
        m = re.search(jpg_re, obj['photoUrl'])
        if m:
            photo = m.group(0)
        else:
            photo = 'Photo-Not-Available-dog.gif'
        # print('Insert/update dog: {}:{}'.format(aid, obj['name']))
        c.execute('INSERT INTO dogs (id, name, href, photo, sex, breed, age, status, date_added, date_proc) VALUES (?,?,?,?,?,?,?,\'active\',?,?) ON CONFLICT(id) DO UPDATE SET name=?, age=?, photo=?, date_proc=?, status=\'active\'',
                  (aid, obj['name'], obj['href'], photo, obj['sex'], obj['breed'], age, fdate, fdate, obj['name'], age, photo, fdate))
    except KeyError:
        print('Missing field in object: {}'.format(obj))
    except sqlite3.IntegrityError:
        print('Duplicate entry: {}'.format(aid))

def move_file(fpath, dest_dir):
    dest_path = f'{dest_dir}/{os.path.basename(fpath)}'
    os.rename(fpath, dest_path)

# Function that takes a filename and returns file size and adler32 checksum
def file_info( filename):
    try:
        size = os.path.getsize(filename)
        with open(filename, 'rb') as f:
            adler = zlib.adler32(f.read())
        return size, adler
    except FileNotFoundError:
        return None, None

################################################################################
# Main program
################################################################################

# Connect to the database gpdogs.db
conn = sqlite3.connect('gpdogs.db')
c = conn.cursor()

# Process each file in the list. 

exit_err = None
current_dogs = set()
# Get the list of files in the IN_DIR directory having name patter animals-*.json
files = [f for f in os.listdir(IN_DIR) if re.match(r'animals-\d{4}-\d{2}-\d{2}-\d{2}.json', f)]
files.sort()

for input_file in files:
    current_dogs.clear()
    fpath = f'{IN_DIR}/{input_file}'
    fdate = get_dttm(fpath)
    if fdate is None:
        exit_err = 'No date found in filename: {fpath}'
        move_file(fpath, BAD_DIR)
        break

    (size, adler) = file_info(fpath)
    if size is None:
        print(f'File not found: {fpath}')
        continue

    rv = file_processed(c, input_file, size, adler, fdate)
    if rv == PROC_YES:
        print(f'Input file already processed; Skipping: {fpath}')
        move_file(fpath, ARCHIVE_DIR)
        continue
    elif rv == PROC_DUP:
        print(f'Input file same as previous; Deleting: {fpath}')
        os.remove(fpath)
        continue

    print(f'Processing file: {fpath}')
    with open(fpath) as f:
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
            move_file(fpath, BAD_DIR)
            conn.close()
            sys.exit(1)

    save_processed(c, input_file, fdate, size, adler)
    sql = 'UPDATE dogs SET date_adopted=?, status=\'adopted\' WHERE status=\'active\' AND date_proc < (select max(date_proc) from file_proc)'
    c.execute(sql, (fdate,))
    move_file(fpath, ARCHIVE_DIR)

conn.commit()
conn.close()
if exit_err is not None:
    print(exit_err)
    sys.exit(1)

sys.exit(0)
