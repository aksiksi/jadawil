from __future__ import print_function
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

    print("Updating repo and committing...")

    # Add pickle to git
    subprocess.call(['git', 'add', 'classes/*.pickle'])
    subprocess.call(['git', 'add', 'last.txt'])

    # Commit changes
    subprocess.call(['git', 'commit', '-m', 'Update class pickles'])

    # Push to GH
    subprocess.call(['git', 'push', 'origin', 'master'])

if __name__ == '__main__':
    main()
