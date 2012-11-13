from flask import request, render_template, url_for, redirect, Flask
import scheduler
import time

app = Flask(__name__)

@app.template_filter('len')
def length(iterable):
    return len(iterable)

@app.template_filter('sum')
def add(schedule_info):
    return sum([float(info['credits']) for info in schedule_info])

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        start = time.time()
        courses = [each for each in request.form.values() if len(each) > 1]
        gender = request.form.get('gender')
        errors = scheduler.validate_inputs(courses)
        if not errors:
            schedules = scheduler.Scheduler(courses, gender).start()
        else:
            return render_template('results.html', errors=errors)
        end = time.time() - start
        return render_template('results.html', schedules=schedules, end=end)

if __name__ == '__main__':
    app.run(debug=True)
