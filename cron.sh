#!/bin/bash
# Simple shell script that runs updatepickle.py as a cron task
# Paths below should be absolute
VENV_PATH=/Users/aksiksi/.virtualenvs/main2
REPO_PATH=/Users/aksiksi/Projects/Python/jadawil

echo "source $VENV_PATH/bin/activate"
source $VENV_PATH/bin/activate

echo "python $REPO_PATH/updatepickle.py"
python $REPO_PATH/updatepickle.py
if [ $? -ne 0 ]; then
    echo "Update pickle failed!"
else
    echo "Pickle update successful!"
fi

deactivate