import subprocess
from grabber import html_to_pickle, source_grabber

def main():
    # Get new course data
    html_to_pickle(source_grabber())

    # Add pickle to git
    subprocess.call(['git', 'add', 'classes.pickle'])

    # Commit changes
    subprocess.call(['git', 'commit', '-m', 'Update class pickle'])

    # Push to heroku
    subprocess.call(['git', 'push', 'heroku', 'master'])

if __name__ == '__main__':
    main()