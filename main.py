# Flask app that serves the Jadawil website
import os
import time
from datetime import datetime, timedelta

from flask import request, render_template, url_for, redirect, Flask

import scheduler

app = Flask(__name__)


@app.template_filter("len")
def length(iterable):
    return len(iterable)


@app.template_filter("crns")
def crns(schedule):
    crns = []
    for day in schedule.values():
        for course in day:
            if course["crn"] not in crns:
                crns.append(course["crn"])

    return " ".join(crns)


@app.template_filter("sum")
def add(schedule):
    total_credits = 0
    added = []

    for day in schedule:
        for course in day:
            title = course["title"]
            credits = course["credit_hours"]
            section = course["section"]

            if title not in added:
                total_credits += float(credits)
                added.append(title)

    return total_credits


@app.template_filter("date")
def date(d):
    return d.strftime("%A %dth %B %Y at %H:%M:%S")


@app.route("/")
def main():
    # Get last update date
    with open("last.txt") as f:
        d = datetime.fromtimestamp((float(f.readline())))

    # Add 4 hours to convert from UTC to local (UAE) time
    d = d + timedelta(hours=4)

    class_data  = sorted(
        [f for f in os.listdir("classes/")
         if f.endswith(".jsonl") and "stats" not in f],
        reverse=True
    )

    # Build list of available terms
    terms = []
    for filename in class_data:
        # 202010.json -> 202010
        term = filename.split(".")[0]
        assert len(term) == 6

        # Convert term to full name; e.g. 202010 -> Fall 2019
        year = int(term[:4])
        semester = int(term[-2:])

        if semester == 10:
            name = "Fall %d" % (year-1)
        elif semester == 20:
            name = "Spring %d" % year
        elif semester == 30:
            name = "Summer %d" % year
        else:
            continue

        terms.append((term, name))

    return render_template("index.html", d=d, terms=terms)

@app.route("/getstarted")
def getstarted():
    return render_template("getstarted.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/submit", methods=["POST"])
def submit():
    if request.method == "POST":
        start = time.time()

        courses, constants = set(), set()

        for each in request.form.items():
            try:
                if len(each[1]) > 1:
                    if int(each[0]) in range(1, 9):
                        courses.add(each[1].lower().strip())
                    else:
                        constants.add(each[1].strip())
            except:
                pass

        if len(courses) == 0:
            return redirect("/")

        campus = request.form.get("campus")
        term = request.form.get("term")

        errors = scheduler.validate_inputs(courses, constants, term)
        course_errors = ", ".join(errors[0])
        crn_errors = ", ".join(errors[1])

        if course_errors or crn_errors:
            return render_template("results.html", course_errors=course_errors, crn_errors=crn_errors)
        else:
            # Run scheduler
            s = scheduler.Scheduler(courses, constants, campus, term)

            try:
                s.start()
            except scheduler.CombinationError:
                num_schedules = -1
                return render_template("results.html", schedules=[], num_schedules=num_schedules)
            except scheduler.MissingInfoError:
                return render_template("results.html", schedules=[], num_schedules=-2)

            end = time.time() - start
            num_schedules = len(s.results)

            return render_template("results.html", schedules=s.results, conflicts=s.conflicts,
                                   final_conflicts=s.final_conflicts, end=end, num_schedules=num_schedules)


if __name__ == '__main__':
    app.run(debug=True)
