#!/bin/bash
# Simple shell script that runs updatepickle.py as a cron task

# Configure Git for Travis
git config --global user.name "Travis CI"
git config --global user.email "travis@assil.me"
git remote set-url origin https://${GH_TOKEN}@github.com/aksiksi/jadawil.git > /dev/null 2>&1

# Update
python updatepickle.py
