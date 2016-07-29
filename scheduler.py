# Python 3 support
from __future__ import print_function

import time
import cPickle as pickle
import itertools
import random
from datetime import datetime
from pprint import pprint
from collections import defaultdict, OrderedDict

def validate_inputs(courses, constants, term):
    '''Make sure inputs are valid courses.'''
    with open('classes/classes-{}.pickle'.format(term)) as f:
        all_courses = pickle.load(f)

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

class TimeRange(object):
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

    def __contains__(self, other):
        if self.start <= other.start <= self.end or other.start <= self.end <= other.end:
            return True

        return False

    def __gt__(self, other):
        return self.start > other.end

    def __str__(self):
        '''Return time range as string.'''
        return '{0}-{1}'.format(datetime.strftime(self.start, '%I:%M %p'), datetime.strftime(self.end, '%I:%M %p'))

class Scheduler(object):
    '''

        To be used publicly:

        self.results: the schedules
        self.success: True if no conflicts
        self.conflicts: possible conflicts in sections
        self.final_conflicts: any final conflicts

    '''
    timeranges = {}

    def __init__(self, courses, constants, gender, term):
        self.courses = courses
        self.constants = constants
        self.gender = gender
        self.term = term
        self.success = False

    def get_course_lab_info(self, courses):
        '''Return course and lab information in dict form.'''
        # Get course data from file
        with open('classes/classes-{}.pickle'.format(self.term)) as f:
            all_courses = pickle.load(f)

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
                current_timerange = timerange

            other_timeranges = [self.timeranges[each['time']] for each in schedule if each != course]

            # Compare current course to the rest of them
            for timerange in other_timeranges:
                if current_timerange > timerange:
                    position += 1

            sorted_schedule.insert(position, course)

        return [course for course in sorted_schedule if course]

    def is_final_conflict(self, s1, s2):
        '''Check for conflict between two sections.'''
        if u'final_date' not in s1 or u'final_date' not in s2:
            return False

        if s1['final_date'] != s2['final_date']:
            return False

        t1 = TimeRange(*s1['final_time'].split('-'))
        t2 = TimeRange(*s2['final_time'].split('-'))

        # True if there is an overlap
        return t1 in t2

    def find_exam_conflicts(self, courses):
        '''Quick check between courses to ensure no final exam date conflicts.'''
        samples = []

        # Store pairs of conflicted (LOL) courses
        conflicted = []

        for course in courses.values():
            samples.append(course.values()[0])

        for s in samples:
            for e in samples:
                if e != s and self.is_final_conflict(e, s):
                    if [e['title'], s['title']] not in conflicted:
                        conflicted.append([s['title'], e['title']])

        return conflicted

    def combs(self, l, c, p=0):
        '''Generate unique combinations of length 2.'''
        if p == len(l):
            return c
        else:
            for n in l[p+1:]:
                c.append([l[p], n])
            return self.combs(l, c, p+1)

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
            self.results = -1
            return

        # Get titles and corresponding sections
        course_titles, course_info = courses.keys(), courses.values()

        # Save sections
        section_info = []
        for v in course_info:
            for s in v.values():
                section_info.append(s)

        # Get final exam conflicts
        self.final_conflicts = self.find_exam_conflicts(courses)

        # pprint(course_info)

        # Section combinations and conflicts
        combs = self.combs(section_info, [])
        self.conflicts = []

        # Catch section overlaps for later
        for c in combs:
            s1, s2 = c

            # Possible conditions for comparison
            # 1. compare a lab with a course section
            # 2. compare sections from two diff. courses
            c1 = (s1['code'] == s2['code']) and (('L' in s1['section'] and 'L' not in s2['section']) or ('L' in s2['section'] and 'L' not in s1['section']))
            c2 = s1['code'] != s2['code']

            # Only compare if from different courses
            if c1 or c2:
                t1 = TimeRange(*s1['time'].split('-'))
                t2 = TimeRange(*s2['time'].split('-'))

                # Check for conflict in both days and time
                if any([d in s2['days'] for d in s1['days']]):
                    if t1 in t2:
                        self.conflicts.append([s1, s2])

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

        self.results = self.convert_to_week_based(schedules)

        # If results, then there are no conflicts
        if self.results:
            self.success = True

# General Education Timerange Finder

class GEScheduler():
	def __init__(self, college, clusters, gender, timerange, term):		
		self.college = college
		self.clusters = clusters
		self.gender = gender
		self.timerange = timerange
		self.term = term
		
	def get_course_list(self):
		courses = []
		if self.college == "COE":
			# Dictionary of COE general education courses
			COE_GE = {  'cluster1': [ # Learning and thinking skills
							"HSS 110",
							"PHI 180",
							"ITBP 119",
							"PSY 105"
							],
						'cluster2': [ #Humanities / fine arts
							 "ARCH 340",
							 "HSR 120",
							 "HSR 130",
							 "LIT 150",
							 "TRS 200",
							 "MSC 200",
							 "MSC 240",
							 "LNG 100",
							 "LNG 110",
							 "PHI 101",
							 "PHI 270",
							 "PHI 271"
							 ],
						'cluster3': [ # The Global Experience
							 "HIS 120",
							 "HIS 125",
							 "AGRB 360",
							 "BIOE 240",
							 "PSG 250",
							 "GEO 200",
							 "HIS 121",
							 "ARCH 346"
							 ]
					 }
			#Extract courses for the cluster chosen
			for cluster in self.clusters:
					courses.extend(COE_GE[cluster])
		if self.college == "CIT":
			CIT_GE = {	'cluster1': [
							"ARCH 340",
							"HIS 133",
							"HSR 120",
							"HSR 130",
							"LIT 150",
							"TRS 200",
							"MSC 200",
							"MSC 240",
							"LNG 100",
							"LNG 110",
							"PHI 101",
							"PHI 270",
							"PHI 271"
							],
						'cluster2': [
							"AGRB 210",
							"ECON 110",
							"HSR 140",
							"HSR 150",
							"PSY 100",
							"SOC 260",
							"SWK 200"
							],
						'cluster3': [
							"HIS 120",
							"HIS 125",
							"AGRB 360",
							"BIOE 240",
							"PSG 250",
							"GEO 200",
							"HIS 121",
							"ARCH 346"
							]
			}
			#Extract courses for the cluster chosen
			for cluster in self.clusters:
					courses.extend(CIT_GE[cluster])
		if self.college == "CL":
			CL_GE = {	'cluster1': [
							"HSS 110",
							"ITBP 119",
							"PHI 180",
							"PSY 105"
							],
						'cluster2': [
							"MATH 120",
							"STAT 101"
							],
						'cluster3': [
							"ARAG 205",
							"ARAG 220",
							"BION 100",
							"CHEM 181",
							"FDSC 250",
							"GEOL 110",
							"PHED 201",
							"PHYS 100",
							"PHYS 101"
							]
			}
			#Extract courses for the cluster chosen
			for cluster in self.clusters:
				courses.extend(CL_GE[cluster])
		if self.college == "CS":
			CS_GE = {	'cluster1': [ # Ethics
							"PHI 121",
							"PHI 122",
							"PHI 226",
							"PHIL 120"
							],
						'cluster2': [ # Thinking Skills
							"HSS 110",
							"PHI 180",
							"ITBP 119",
							"PSY 105"
							 ],
						'cluster3': [ # Humanities / Fine Arts
							"ARCH 340",
							"HIS 133",
							"HSR 120",
							"HSR 130",
							"LIT 150",
							"TRS 200",
							"MSC 200",
							"MSC 240",
							"LNG 100",
							"LNG 110",
							"PHI 101",
							"PHI 270",
							"PHI 271"
							 ],
						'cluster4': [ # Social and Behavioral Sciences
							"AGRB 210",
							"ECON 110",
							"HSR 140",
							"HSR 150",
							"PSY 100",
							"SOC 260",
							"SWK 200"
							],
						'cluster5': [ # The Global Experience
							"HIS 120",
							"HIS 125",
							"AGRB 360",
							"BIOE 240",
							"PSG 250",
							"GEO 200",
							"HIS 121",
							"ARCH 346"
							]
					}
			#Extract courses for the cluster chosen
			for cluster in self.clusters:
					courses.extend(CS_GE[cluster])
		
		
		# REPEAT FOR OTHER MAJORS ONCE I GET THE REST OF THE GE PLANS
			# -----------------------------------
		return courses	
		
	def compare_timeranges(self, section_time):
		# Split the times into a list (10:00 am- 11:15 am   => ['10:00 am', '11:15 am'])
		timerange1 = self.timerange.strip(' ').split('-')
		timerange2 = section_time.strip(' ').split('-')
		
		# Get the start and end times
		start_time1 = datetime.strptime(timerange1[0], "%I:%M %p")
		end_time1 = datetime.strptime(timerange1[1], "%I:%M %p")
		start_time2 = datetime.strptime(timerange2[0], "%I:%M %p")
		end_time2 = datetime.strptime(timerange2[1], "%I:%M %p")
		
		# Return true if the section time is in the input timerange
		return (start_time2 >= start_time1 and end_time1 >= end_time2) 
		
	def start(self):
		'''Start the GE Course Finder'''
		# Get course data from file
		with open('classes/classes-{}.pickle'.format(self.term)) as f:
			all_courses = pickle.load(f)
			
		# Get general education courses based on college and cluster	
		courses = self.get_course_list()
		filtered_course_sections = {}
		
		for course in courses:
			abbrv, code = course.upper().strip(' ').split(' ')
			# If course does not exist in the course list then move on to the next one
			try:
				course_sections = all_courses[abbrv][code]
			except:
				continue
				
            # Filter course_sections by gender and timing
			for crn, section in course_sections.items():
				# Get the section timing
				if section['time'] != 'TBA':
					if section['gender'] == self.gender and self.compare_timeranges(section['time']):
						filtered_course_sections[crn] = section
		return filtered_course_sections
			
if __name__ == '__main__':
    pass
    # s = Scheduler(['math 1110', 'phys 1110', 'math 1120'], [], 'B').start()
    # print(s)
