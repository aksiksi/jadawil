import subprocess
import time
from datetime import datetime
from grabber import html_to_pickle, source_grabber

def main():
    # Get new course data
    html_to_pickle(source_grabber())

    # Write last update time to file
    with open('last.txt', 'w') as f:
    	f.write(str(time.time()))

    # Add pickle to git
    subprocess.call(['git', 'add', 'classes.pickle'])
    subprocess.call(['git', 'add', 'last.txt'])

    # Commit changes
    subprocess.call(['git', 'commit', '-m', 'Update class pickle'])

    # Push to heroku
    subprocess.call(['git', 'push', 'heroku', 'master'])

if __name__ == '__main__':
    main()