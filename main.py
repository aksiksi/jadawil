# Flask app that serves the Jadawil website
from __future__ import print_function

import os
import time
import json
from datetime import datetime, timedelta

from flask import request, render_template, url_for, redirect, Flask

import scheduler

app = Flask(__name__)

@app.template_filter('timeslots')
def timeslots(schedule):
    t = []
    for courses in schedule.values():
        for course in courses:
            if course['time'] not in t:
                t.append(scheduler.TimeRange(course['time']))
    return [str(obj) for obj in sorted(t)]

@app.template_filter('len')
def length(iterable):
    return len(iterable)

@app.template_filter('crns')
def crns(schedule):
    crns = []
    for day in schedule.values():
        for course in day:
            if course['crn'] not in crns and 'L' not in course['crn']:
                crns.append(course['crn'])

    return ' '.join(crns)

@app.template_filter('sum')
def add(schedule):
    total_credits = 0
    added = []

    for day in schedule:
        for course in day:
            credits = course['credits']
            title = course['title']

            if title not in added:
                # In case of 0.00/3.00 like in CHEM 2702
                if '/' in credits:
                    if 'L' in course['section']: # If course is a lab
                        total_credits += float(credits.partition('/')[0])
                    else:
                        total_credits += float(credits.partition('/')[2])
                else:
                    total_credits += float(credits)

                added.append(title)

    return total_credits

@app.template_filter('date')
def date(d):
    return d.strftime('%A %dth %B %Y at %H:%M:%S')

@app.route('/')
def main():
    # Get last update date
    with open('last.txt') as f:
        d = datetime.fromtimestamp((float(f.readline())))

    # Add 4 hours to convert from UTC to local (UAE) time
    d = d + timedelta(hours=4)

    # Build list of available terms
    class_pickles = sorted(os.listdir('classes/'), reverse=True)
    terms = []
    for filename in class_pickles:
        # classes-202010.pickle -> 202010
        term = filename.split('.')[0].split('-')[1]
        assert len(term) == 6

        # Convert term to full name; e.g. 202010 -> Fall 2019
        year = int(term[:4])
        semester = int(term[-2:])

        if semester == 10:
            name = 'Fall %d' % (year-1)
        elif semester == 20:
            name = 'Spring %d' % year
        elif semester == 30:
            name = 'Summer %d' % year
        else:
            continue

        terms.append((term, name))

    return render_template('index.html', d=d, terms=terms)

@app.route('/getstarted')
def getstarted():
    return render_template('getstarted.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
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
            return redirect('/')

        gender = request.form.get('gender')
        term = request.form.get('term')

        errors = scheduler.validate_inputs(courses, constants, term)
        course_errors = ', '.join(errors[0])
        crn_errors = ', '.join(errors[1])

        if course_errors or crn_errors:
            return render_template('results.html', course_errors=course_errors, crn_errors=crn_errors)
        else:
            # Run scheduler
            s = scheduler.Scheduler(courses, constants, gender, term)
            s.start()

            # In case of too many combinations
            if s.results == -1:
                return render_template('results.html', schedules=s.results)

            end = time.time() - start

            return render_template('results.html', schedules=s.results, conflicts=s.conflicts, final_conflicts=s.final_conflicts, end=end)

@app.route('/submit_GE', methods=['POST'])
def submit_GE():
    if request.method == 'POST':
        start = time.time()

        college = request.form['college']
        major = request.form[college + '_major']

        if college == "CHSS":
            if major == "HIS" or major == "POL" or major == "SOC" or major == "GEO":
                cluster = college + "_2_cluster" # Get the checkboxes only for the college and major selected
            elif major == "MC" or major == "PHI":
                cluster = college + "_3_cluster"
            else:
                cluster = college + "_1_cluster"
        else:
            cluster = college + "_" + major + "_cluster" # Get the checkboxes only for the college and major selected

        clusters = request.form.getlist(cluster)
        gender = request.form['gender']
        term = request.form['term']

        # Form time range in the format "10:00 am-11:15 am"
        timerange = request.form['start-time'] + ":00 " + request.form['start-am-pm'] + "-" + request.form['end-time'] + ":00 " + request.form['end-am-pm']

        GE_courses = scheduler.GEScheduler(college, major, clusters, gender, timerange, term).start()

        end = time.time() - start

        return render_template('ge_results.html', sections=GE_courses, end=end)

if __name__ == '__main__':
    app.run(debug=True)
