#!/bin/bash
DATA_DIR=infiles
VENV="/Users/esteban/py/dev-venv" 
if [[ $VENV != "$VIRTUAL_ENV" ]]
then
    echo "Please activate virtualenv $VENV using the following command:"
    echo "  . $VENV/bin/activate"
    exit 1
fi

npm start
mv $DATA_DIR/animals.json $DATA_DIR/animals-$(date +'%Y-%m-%d-%H').json
for url in $(pcre2grep -h -o '(?<=photoUrl": ").*\.(?:jpg|gif)' $DATA_DIR/animals-2024-0?-*.json ) ; do [[ -f pics/${url##*/} ]] || curl -o pics/${url##*/} $url ; done
python load_dogs.py $DATA_DIR/animals-*.json
python mk_index.py
