#!/bin/bash
# Simple shell script that runs updatepickle.py as a cron task
# Make sure to update the paths
VENV_PATH=~/.virtualenvs/main2
REPO_PATH=~/Projects/Python/jadawil
LOG_PATH=/tmp/jadawil.log

echo "source $VENV_PATH/bin/activate"
source $VENV_PATH/bin/activate

echo "python $REPO_PATH/updatepickle.py 2>&1 1>$LOG_PATH"
python $REPO_PATH/updatepickle.py 2>&1 1>$LOG_PATH
if [ $? -ne 0 ]; then
    echo "Update pickle failed! Please check $LOG_PATH!"
else
    echo "Pickle update successful!"
fi

deactivate
