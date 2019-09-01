#!/bin/bash
# Simple shell script that runs updatepickle.py as a cron task
# Paths below should be absolute
VENV_PATH=/Users/aksiksi/.virtualenvs/main2
REPO_PATH=/Users/aksiksi/Projects/Python/jadawil

# Override $HOME to detect Git creds
export HOME=/home/aksiksi

echo "source $VENV_PATH/bin/activate"
source $VENV_PATH/bin/activate

cd $REPO_PATH

echo "python $REPO_PATH/updatepickle.py"
python $REPO_PATH/updatepickle.py
if [ $? -ne 0 ]; then
    echo "Update pickle failed!"
else
    echo "Pickle update successful!"
fi

