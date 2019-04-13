# Jadawil

A web application running with Flask that allows UAEU students to schedule their courses without time conflicts. A running version can be found at the repo's website.

# Usage

1. Initialize a Heroku app inside the folder.
2. Create a file in root directory `secret.py` and add your UAEU username and password to it as similarly named variables (`username` and `password`)
3. Push the repo to Heroku - `git push heroku master`.

# Updating Data

1. Install all dependencies with `pip install -r requirements.txt`.  You will need to be running Python 2.6+ (no Python 3 support due to Mechanize).
2. Make sure that `secret.py` contains valid UAEU credentials (see above).
3. Run `grabber.py` and pass in the `--term` parameter.  For Fall, the format is `YYYY10`, where YYYY is the current year.  For example, Fall 2019 -> `201920`. For Spring, `YYYY10`, where YYYY is the current year.
4. If everything went well, you should find a new pickle file under `classes/` corresponding to the given term. This is the raw course data dump.
5. Finally, open `index.html` and add a new entry to the `<select>` block for the added term. This is how the user can select to use the course data for that term.
6. Commit your changes, then push to Heroku (see above).
