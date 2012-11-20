import time
import cPickle
import itertools
import random
from datetime import datetime
from pprint import pprint

def validate_inputs(courses):
    '''Make sure inputs are valid courses.'''
    with open('classes.pickle') as f:
        all_courses = cPickle.load(f)

    errors = []
    
    # Catch any input errors and return them
    for course in courses:
        try:
            abbrev, code = course.upper().strip(' ').split(' ')
            all_courses[abbrev][code]
        except:
            errors.append(course)

    return errors

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

    def __contains__(self, *args):
        '''Return True if any of the inputs lies in the range.'''
        # Construct list of time dicts
        times = []
        for time in args:
            if time not in self.datetimes:
                time_obj = datetime.strptime(time, '%I:%M %p')
                self.datetimes[time] = time_obj
                times.append(time_obj)
            else:
                times.append(self.datetimes[time])

        # Check for conflicts
        for time in times:
            if (self.start <= time <= self.end):
                return True
        return False

    def __show__(self):
        '''Return time range as string.'''
        return '{0}-{1}'.format(datetime.strftime(self.start, '%I:%M %p'), datetime.strftime(self.end, '%I:%M %p'))

class Scheduler():
    timeranges = {}

    def __init__(self, courses, gender):
        self.courses = courses
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
            t = self.timeranges.get(text_time)
        else:
            t = TimeRange(start1, end1)
            self.timeranges[text_time] = t

        # Check if there is a conflict in days and/or time
        if any(day in section2['days'] for day in section1['days']):
            if t.__contains__(start2, end2):
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
        possible_products = list(itertools.product(*course_info))
        random.shuffle(possible_products)
        for product in possible_products:
            yield product

    def start(self):
        '''Start the scheduler.'''
        # Get course info, filtered by gender
        courses = self.get_course_lab_info(self.courses)
        
        # Make sure possible combinations not too high
        product = 1
        for course in courses.values():
            product *= len(course)

        if product > 1e6:
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
            for title, crn in zip(course_titles, each):
                schedule[title] = courses[title][crn]
            # Check for conflicts in schedule
            if not self.check_schedule_conflicts(schedule):
                schedules.append(schedule)
            if len(schedules) == 15 or (time.time() - start) >= 10:
                break

        return schedules