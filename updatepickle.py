import subprocess
import time
import grabber
from datetime import datetime

def main():
    # Get new course data
    grabber.main()

    # Write last update time to file
    with open('last.txt', 'w') as f:
    	f.write(str(time.time()))

    # Add pickle to git
    subprocess.call(['git', 'add', '*.pickle'])
    subprocess.call(['git', 'add', 'last.txt'])

    # Commit changes
    subprocess.call(['git', 'commit', '-m', 'Update class pickles'])

    # Push to heroku
    subprocess.call(['git', 'push', 'heroku', 'master'])

if __name__ == '__main__':
    main()