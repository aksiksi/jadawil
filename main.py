from flask import request, render_template, url_for, redirect, Flask
import scheduler
import time
from datetime import datetime, timedelta

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
            if course['crn'] not in crns:
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

    # Add 4 hours to account for local time
    d = d + timedelta(hours=4)

    return render_template('index.html', d=d)

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

        gender = request.form.get('gender')
        term = request.form.get('term')

        errors = scheduler.validate_inputs(courses, constants, term)
        course_errors = ', '.join(errors[0])
        crn_errors = ', '.join(errors[1])

        if not (course_errors or crn_errors):
            schedules, conflicts = scheduler.Scheduler(courses, constants, gender, term).start()
        else:
            return render_template('results.html', course_errors=course_errors, crn_errors=crn_errors)

        end = time.time() - start

        return render_template('results.html', schedules=schedules, conflicts=conflicts, end=end)

if __name__ == '__main__':
    app.run(debug=True)
