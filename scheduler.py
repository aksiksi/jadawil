import time
import cPickle
import itertools
import random
from datetime import datetime
from pprint import pprint
from collections import defaultdict, OrderedDict

def validate_inputs(courses, constants):
    '''Make sure inputs are valid courses.'''
    with open('classes.pickle') as f:
        all_courses = cPickle.load(f)

    course_errors = []
    crn_errors = []
    
    # Catch any course errors and return them
    for course in courses:
        try:
            abbrev, code = course.upper().strip(' ').split(' ')
            all_courses[abbrev][code]
        except:
            course_errors.append(course)

    # Catch CRN errors
    for crn in constants:
        found = False
        for course in courses:
            if course not in course_errors:
                abbrev, code = course.upper().strip(' ').split(' ')
                course_info = all_courses[abbrev][code]
                if any([crn == each for each in course_info]):
                    found = True
        if not found:
            crn_errors.append(crn)

    return course_errors, crn_errors

class TimeRange():
    '''Simple class for checking if a time (or times) lie(s) within a time range.'''
    datetimes = {}
    
    def __init__(self, start, end):
        '''Add datetime object to datetimes dict if not already there.'''
        index = 0
        for time in [start, end]:
            if not index:
                if time not in self.datetimes:
                    self.start = datetime.strptime(start, '%I:%M %p')
                    self.datetimes[time] = self.start
                else:
                    self.start = self.datetimes[time]
            elif index:
                if time not in self.datetimes:
                    self.end = datetime.strptime(end, '%I:%M %p')
                    self.datetimes[time] = self.end
                else:
                    self.end = self.datetimes[time]
            index += 1

    def construct(self, *args):
        '''Construct a list of datetime objects for given arguments.'''
        times = []
        
        for time in args:
            if time not in self.datetimes:
                time_obj = datetime.strptime(time, '%I:%M %p')
                self.datetimes[time] = time_obj
                times.append(time_obj)
            else:
                times.append(self.datetimes[time])

        return times

    def contains(self, *args):
        '''Return True if any of the inputs lies in the range.'''
        # Construct list of datetime objects
        datetimes = self.construct(*args)
        
        # Check for conflicts
        for time in datetimes:
            if (self.start <= time <= self.end):
                return True
        
        return False

    def __gt__(self, other):
        return self.start > other.end

    def __str__(self):
        '''Return time range as string.'''
        return '{0}-{1}'.format(datetime.strftime(self.start, '%I:%M %p'), datetime.strftime(self.end, '%I:%M %p'))

class Scheduler():
    timeranges = {}

    def __init__(self, courses, constants, gender):
        self.courses = courses
        self.constants = constants
        self.gender = gender

    def get_course_lab_info(self, courses):
        '''Return course and lab information in dict form.'''
        # Get course data from file
        with open('classes.pickle') as f:
            all_courses = cPickle.load(f)

        filtered_courses = {}

        # Loop through required courses
        for course in courses:
            abbrev, code = course.upper().strip(' ').split(' ')
            course_sections = all_courses[abbrev][code]
            course_labs = {}

            filtered_course_sections = {}

            # Filter course_sections by gender and availability (!TBA for loc, time, and instructor)
            for crn, section in course_sections.items():
                if section['gender'] == self.gender and all(['TBA' not in each for each in [section['time'], section['location']]]):
                    filtered_course_sections[crn] = section

            # Loop through filtered sections
            for crn, section in filtered_course_sections.items():
                # If lab section, add to lab dict and remove from section dict
                if 'L' in section['section']:
                    course_labs[crn] = filtered_course_sections.pop(crn)

            # Add labs (if any) to filtered_courses; key is course name with 'Lab' appended
            if filtered_course_sections: # Make sure that there are sections
                if course_labs:
                    filtered_courses[course], filtered_courses[course + ' Lab'] = filtered_course_sections, course_labs
                else:
                    filtered_courses[course] = filtered_course_sections

        return filtered_courses

    def is_conflict(self, section1, section2):
        '''Check for a conflict between two sections.'''
        # Get start and end times for each section
        start1, end1, start2, end2 = section1['time'].split('-') + section2['time'].split('-')

        # Create a TimeRange object for section1 if it's not in timeranges
        text_time = section1['time']
        if text_time in self.timeranges:
            timerange = self.timeranges.get(text_time)
        else:
            timerange = TimeRange(start1, end1)
            self.timeranges[text_time] = timerange

        # Check if there is a conflict in days and/or time
        if any(day in section2['days'] for day in section1['days']):
            if timerange.contains(start2, end2):
                return True
        else:
            return False

    def check_conflicts(self, current_section, other_sections):
        '''Return True if there are any conflicts.'''
        return any([self.is_conflict(current_section, each) for each in other_sections])

    def check_schedule_conflicts(self, schedule):
        '''Check if a schedule contains conflicts.'''
        sections = schedule.values()
        for section in sections:
            other_sections = [each for each in sections if each != section]
            if self.check_conflicts(section, other_sections):
                return True
        return False

    def generate_products(self, course_info):
        '''Return all possible schedule combinations as a generator.'''
        possible_products = list(itertools.product(*course_info))
        random.shuffle(possible_products)
        for product in possible_products:
            yield product

    def convert_to_week_based(self, schedules):
        '''Convert normal schedules to week-based schedules.'''
        days_of_week = [('U', 'Sunday'), ('M', 'Monday'), ('T', 'Tuesday'),
                        ('W', 'Wednesday'), ('R', 'Thursday')]
        week_schedules = []

        for schedule in schedules:
            # Initialize week_schedule - need it to be in order
            week_schedule = OrderedDict()
            for letter, word in days_of_week:
                week_schedule[word] = []

            # Populate days of the week with courses
            for course in schedule.values():
                days = list(course['days'])
                for letter, word in days_of_week:
                    if letter in days:
                        week_schedule[word].append(course)
            
            # Sort each schedule
            sorted_week_schedule = OrderedDict()
            for day, day_schedule in week_schedule.items():
                sorted_week_schedule[day] = self.sort_courses_in_day(day_schedule)

            week_schedules.append(sorted_week_schedule)

        return week_schedules

    def sort_courses_in_day(self, schedule):
        '''Given a list of courses in a day, return the courses in chronological order.'''
        sorted_schedule = [0 for _ in range(len(schedule))]

        for course in schedule:
            # Track position of course; this basically tracks how many courses this course is after
            position = 0
            
            # Get timeranges from dict (they're definitely there already - maybe not?)
            if course['time'] in self.timeranges:
                current_timerange = self.timeranges[course['time']]
            else:
                # Pass in start and end time to object
                timerange = TimeRange(*course['time'].split('-'))
                self.timeranges[course['time']] = timerange

            other_timeranges = [self.timeranges[each['time']] for each in schedule if each != course]

            # Compare current course to the rest of them
            for timerange in other_timeranges:
                if current_timerange > timerange:
                    position += 1

            sorted_schedule.insert(position, course)

        return [course for course in sorted_schedule if course]

    def start(self):
        '''Start the scheduler.'''
        # Get course info, filtered by gender
        unfiltered_courses = self.get_course_lab_info(self.courses)
        courses = {}

        # Append any constant sections to courses
        for code, info in unfiltered_courses.items():
            needed = [crn for crn in info if crn in self.constants]
            if needed:
                course_info = {}
                for crn in needed:
                    course_info[crn] = info[crn]
            else:
                course_info = info
            courses[code] = course_info
        
        # Make sure possible combinations not too high
        product = 1
        for course in courses.values():
            product *= len(course)

        if product > 2e6:
            return -1

        # Get titles and corresponding sections
        course_titles, course_info = courses.keys(), courses.values()

        # Start finding valid schedules
        schedules = []
        start = time.time()
        generate_products = self.generate_products(course_info)

        for each in generate_products:
            schedule = {}
            # Build a schedule based on products
            for title, crn in itertools.izip(course_titles, each):
                schedule[title] = courses[title][crn]
            # Check for conflicts in schedule
            if not self.check_schedule_conflicts(schedule):
                schedules.append(schedule)
            if (time.time() - start) >= 10 or len(schedules) >= 50:
                break

        return self.convert_to_week_based(schedules)

if __name__ == '__main__':
    s = Scheduler(['PHYS 1110', 'MATH 1110', 'MECH 390', 'HIS 133', 'ITBP 319'], 'B').start()
    print s