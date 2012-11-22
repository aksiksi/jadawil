from flask import request, render_template, url_for, redirect, Flask
import scheduler
import time

app = Flask(__name__)

@app.template_filter('len')
def length(iterable):
    return len(iterable)

@app.template_filter('sum')
def add(schedule_info):
    total_credits = 0
    for course in schedule_info:
        credits = course['credits']

        # In case of 0.00/3.00 like in CHEM 2702
        if '/' in credits:
            if 'L' in course['section']: # If course is a lab
                total_credits += float(credits.partition('/')[0])
            else:
                total_credits += float(credits.partition('/')[2])
        else:
            total_credits += float(credits)
    
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