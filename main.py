from flask import request, render_template, url_for, redirect, Flask
import scheduler
import time

app = Flask(__name__)
app.debug = True

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

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        start = time.time()
        courses = set([each for each in request.form.values() if len(each) > 1])
        gender = request.form.get('gender')
        errors = ', '.join(scheduler.validate_inputs(courses))
        
        if not errors:
            schedules = scheduler.Scheduler(courses, gender).start()
        else:
            return render_template('results.html', errors=errors)
        
        end = time.time() - start
        return render_template('results.html', schedules=schedules, end=end)

def determine_grade(grade):
    if grade >= 90:
        return 4
    elif 85 <= grade < 90:
        return 3.5
    elif 80 <= grade < 85:
        return 3
    elif 75 <= grade < 80:
        return 2.5
    elif 70 <= grade < 75:
        return 2
    elif 65 <= grade < 70:
        return 1.5
    elif 60 <= grade < 65:
        return 1
    else:
        return 0

@app.route('/gpacalc', methods=['POST', 'GET'])
def calculator():
    if request.method == 'POST':
        try:
            grades = [determine_grade(int(value)) for key, value in request.form.items() if 'g' in key and value]
            credits = [int(value) for key, value in request.form.items() if 'c' in key and value]
            total_credits = sum(credits)
            grade_points = 0

            for i in range(len(grades)):
                grade_points += (grades[i] * credits[i])

            gpa = grade_points / float(total_credits)

            return render_template('gpa.html', gpa=round(gpa, 2))
        except:
            pass

    return render_template('calc.html')

if __name__ == '__main__':
    app.run(debug=True)