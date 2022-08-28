# Jadawil

A web application running with Flask that allows UAEU students to schedule their courses without time conflicts. A running version can be found at the repo's website.

# Usage

Build and run a Docker image:

```
docker build . -t jadawil
docker run jadawil
```

Run the grabber to update course data:

```
pip install -r requirements.txt
python3 grabber.py
```

# Updating Data

1. Install all dependencies with `pip install -r requirements.txt`.  You will need to be running Python 2.6+ (no Python 3 support due to Mechanize).
2. Make sure that `secret.py` contains valid UAEU credentials (see above).
3. Run `grabber.py` to fetch data for the **latest** term. If you need a specific term, use the `--term` flag. Refer to next section for details.
4. If everything went well, you should find a new pickle file under `classes/` corresponding to the given term. This is the raw course data dump.
5. Commit your changes, then push to Heroku (see above).

## Term Format

For Fall, the format is `YYYY10`, where `YYYY` is the *next* year.  For example, Fall 2019 -> `202010`.

For Spring, `YYYY20`, where `YYYY` is the current year. Summer is the same, but with `YYYY30`.
