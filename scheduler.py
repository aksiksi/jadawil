import itertools
import random
import time
from datetime import datetime
from collections import defaultdict, OrderedDict

import jsonlines


DAYS_OF_WEEK = [
    ("U", "Sunday"),
    ("M", "Monday"),
    ("T", "Tuesday"),
    ("W", "Wednesday"),
    ("R", "Thursday"),
    ("F", "Friday"),
]

TIME_FORMAT = "%H%M"


def validate_inputs(courses, constants, term):
    """Make sure inputs are valid courses."""
    courses_found = []
    crns_found = []

    courses = [c.upper() for c in courses]

    with jsonlines.open(f"classes/{term}.jsonl") as sections:
        for section in sections:
            subject, number = section["subject"], section["courseNumber"]
            crn = section["courseReferenceNumber"]
            course_code = f"{subject} {number}".upper()

            if course_code in courses:
                courses_found.append(course_code)

            if constants and crn in constants:
                crns_found.append(crn)

    course_errors = set(courses) - set(courses_found)
    crn_errors = set(constants) - set(crns_found)

    return list(course_errors), list(crn_errors)


class CombinationError(Exception):
    pass


class MissingInfoError(Exception):
    pass


class TimeRange:
    """Simple class for checking if a time (or times) lie(s) within a time range."""
    datetimes = {}

    def __init__(self, start, end):
        """Add datetime object to datetimes dict if not already there."""
        index = 0
        for time in [start, end]:
            if not index:
                if time not in self.datetimes:
                    self.start = datetime.strptime(start, TIME_FORMAT)
                    self.datetimes[time] = self.start
                else:
                    self.start = self.datetimes[time]
            elif index:
                if time not in self.datetimes:
                    self.end = datetime.strptime(end, TIME_FORMAT)
                    self.datetimes[time] = self.end
                else:
                    self.end = self.datetimes[time]

            index += 1

    def construct(self, *args):
        """Construct a list of datetime objects for given arguments."""
        times = []

        for time in args:
            if time not in self.datetimes:
                time_obj = datetime.strptime(time, TIME_FORMAT)
                self.datetimes[time] = time_obj
                times.append(time_obj)
            else:
                times.append(self.datetimes[time])

        return times

    def contains(self, *args):
        """Return True if any of the inputs lies in the range."""
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
        """Return time range as string."""
        return "{0}-{1}".format(datetime.strftime(self.start, TIME_FORMAT),
                                datetime.strftime(self.end, TIME_FORMAT))


class Scheduler:
    """Basic course scheduler.

    Attributes:
        - results: the schedules
        - success: True if no conflicts
        - conflicts: possible conflicts in sections
        - final_conflicts: any final conflicts
    """
    timeranges = {}

    def __init__(self, courses, constants, campus, term):
        self.courses = courses
        self.constants = constants
        self.campus = campus
        self.term = term
        self.success = False

    def get_course_lab_info(self, courses):
        """Return course and lab information in dict form."""
        # Build dict to hold structured course info
        all_courses = {}
        for c in courses:
            subject, number = c.upper().split(" ")
            if subject not in all_courses:
                all_courses[subject] = {number: {}}
            else:
                all_courses[subject][number] = {}

        courses = [c.upper() for c in courses]

        # Get course data from file
        with jsonlines.open("classes/{}.jsonl".format(self.term)) as reader:
            for section in reader:
                subject, number = section["subject"], section["courseNumber"]
                course_code = f"{subject} {number}".upper()
                if course_code in courses:
                    all_courses[subject][number][section["courseReferenceNumber"]] = section

        filtered_courses = {}

        # Loop through required courses
        for course in courses:
            abbrev, code = course.upper().strip(" ").split(" ")
            course_sections = all_courses[abbrev][code]
            course_labs = {}

            filtered_course_sections = {}

            # Filter course_sections by gender/campus and availability
            # (!TBA for loc, time, and instructor)
            for crn, section in course_sections.items():
                new_section = {}

                class_info = [s["meetingTime"] for s in section["meetingsFaculty"]
                              if s["meetingTime"]["meetingType"] == "CLAS"]
                final_info = [s["meetingTime"] for s in section["meetingsFaculty"]
                              if s["meetingTime"]["meetingType"] == "FINL"]

                if not class_info:
                    continue

                new_section["classInfo"] = class_info[0] if class_info else {}
                new_section["finalInfo"] = final_info[0] if final_info else {}

                class_info = new_section["classInfo"]
                final_info = new_section["finalInfo"]

                # NOTE(aksiksi): Campus can be one of "B", "G", or "BG"
                campus = class_info["campus"]
                if not campus or self.campus not in campus:
                    continue

                days = ""
                for d, day in DAYS_OF_WEEK:
                    day_lower = day.lower()
                    if class_info[day_lower]:
                        days += d
                new_section["days"] = days

                new_section["start_time"] = class_info["beginTime"]
                new_section["end_time"] = class_info["endTime"]
                new_section["time"] = \
                    f'{class_info["beginTime"]}-{class_info["endTime"]}'

                # Build a string of "start_time-end_time D_1,D_2"
                new_section["time_string"] = \
                    f'{new_section["time"]} {new_section["days"]}'

                new_section["open"] = section["openSection"]
                new_section["title"] = section["courseTitle"]
                new_section["instructor"] = \
                    " & ".join(f["displayName"] for f in section["faculty"]) or "TBA"
                new_section["crn"] = crn
                new_section["subject"] = section["subject"]
                new_section["course_number"] = section["courseNumber"]
                new_section["building"] = class_info["building"]
                new_section["room"] = class_info["room"]
                new_section["seats_available"] = section["seatsAvailable"]
                new_section["seats_total"] = section["maximumEnrollment"]
                new_section["section"] = class_info["category"]
                new_section["credit_hours"] = class_info["creditHourSession"]

                new_section["final"] = {
                    "date": "TBA",
                    "time": "TBA",
                }

                if final_info:
                    new_section["final"]["date"] = final_info["startDate"]
                    new_section["final"]["time"] = \
                        f'{final_info["beginTime"]}-{final_info["endTime"]}'
                    new_section["final"]["start_time"] = final_info["beginTime"]
                    new_section["final"]["end_time"] = final_info["endTime"]

                if new_section["open"] and new_section["start_time"]:
                    filtered_course_sections[crn] = new_section

            filtered_courses[course] = filtered_course_sections

            # TODO: Investigate if lab processing required
            continue

            # Loop through filtered sections
            for crn, section in filtered_course_sections.items():
                # If lab section, add to lab dict and remove from section dict
                if "L" in section["section"]:
                    course_labs[crn] = filtered_course_sections.pop(crn)

            # Add labs (if any) to filtered_courses; key is course name with "Lab" appended
            if filtered_course_sections: # Make sure that there are sections
                if course_labs:
                    filtered_courses[course], filtered_courses[course + " Lab"] = filtered_course_sections, course_labs
                else:
                    filtered_courses[course] = filtered_course_sections

        return filtered_courses

    def is_conflict(self, s1, s2):
        """Check for a conflict between two sections."""
        # Get start and end times for each section
        start1, end1 = s1["start_time"], s1["end_time"]
        start2, end2 = s2["start_time"], s2["end_time"]

        # Create a TimeRange object for section1 if it's not in timeranges
        text_time = s1["time_string"]
        if text_time in self.timeranges:
            timerange = self.timeranges.get(text_time)
        else:
            timerange = TimeRange(start1, end1)
            self.timeranges[text_time] = timerange

        # Check if there is a conflict in days and/or time
        if any(day in s2["days"] for day in s1["days"]):
            if timerange.contains(start2, end2):
                return True
        else:
            return False

    def check_conflicts(self, current_section, other_sections):
        """Return True if there are any conflicts."""
        return any([self.is_conflict(current_section, each) for each in other_sections])

    def check_schedule_conflicts(self, schedule):
        """Check if a schedule contains conflicts."""
        sections = schedule.values()
        for section in sections:
            other_sections = [each for each in sections if each != section]
            if self.check_conflicts(section, other_sections):
                return True
        return False

    def generate_products(self, course_info):
        """Return all possible schedule combinations as a generator."""
        possible_products = list(itertools.product(*course_info))
        random.shuffle(possible_products)
        for product in possible_products:
            yield product

    def convert_to_week_based(self, schedules):
        """Convert normal schedules to week-based schedules."""
        week_schedules = []

        for schedule in schedules:
            # Initialize week_schedule - need it to be in order
            week_schedule = OrderedDict()
            for letter, word in DAYS_OF_WEEK:
                week_schedule[word] = []

            # Populate days of the week with courses
            for course in schedule.values():
                days = list(course["days"])
                for letter, word in DAYS_OF_WEEK:
                    if letter in days:
                        week_schedule[word].append(course)

            # Sort each schedule
            sorted_week_schedule = OrderedDict()
            for day, day_schedule in week_schedule.items():
                sorted_week_schedule[day] = self.sort_courses_in_day(day_schedule)

            week_schedules.append(sorted_week_schedule)

        return week_schedules

    def sort_courses_in_day(self, schedule):
        """Given a list of courses in a day, return the courses in chronological order."""
        sorted_schedule = [0 for _ in range(len(schedule))]

        for course in schedule:
            # Track position of course; this basically tracks how many courses this course is after
            position = 0
            time_string = course["time_string"] 

            # Get timeranges from dict (they're definitely there already - maybe not?)
            if time_string in self.timeranges:
                current_timerange = self.timeranges[time_string]
            else:
                # Pass in start and end time to object
                timerange = TimeRange(course["start_time"],
                                      course["end_time"])
                self.timeranges[time_string] = timerange
                current_timerange = timerange

            other_timeranges = [self.timeranges[time_string]
                                for each in schedule if each != course]

            # Compare current course to the rest of them
            for timerange in other_timeranges:
                if current_timerange > timerange:
                    position += 1

            sorted_schedule.insert(position, course)

        return [course for course in sorted_schedule if course]

    def is_final_conflict(self, s1, s2):
        """Check for conflict between two sections."""
        if s1["final"]["date"] == "TBA" or s2["final"]["date"] == "TBA":
            return False

        if s1["final"]["time"]== "TBA" or s2["final"]["time"] == "TBA":
            return False

        if s1["final"]["date"] != s2["final"]["date"]:
            return False

        t1 = TimeRange(s1["final"]["start_time"], s1["final"]["end_time"])
        t2 = TimeRange(s2["final"]["start_time"], s2["final"]["end_time"])

        return t1 in t2

    def find_exam_conflicts(self, courses):
        """Quick check between courses to ensure no final exam date conflicts."""
        samples = []

        # Store pairs of conflicted (LOL) courses
        conflicted = []

        for course in courses.values():
            samples.append(list(course.values())[0])

        for s in samples:
            for e in samples:
                if e != s and self.is_final_conflict(e, s):
                    if [e["title"], s["title"]] not in conflicted:
                        conflicted.append([s["title"], e["title"]])

        return conflicted

    def combs(self, l, c, p=0):
        """Generate unique combinations of length 2."""
        if p == len(l):
            return c
        else:
            for n in l[p+1:]:
                c.append([l[p], n])
            return self.combs(l, c, p+1)

    def find_section_conflicts(self, combs):
        """Catch section overlaps for later."""
        for c in combs:
            s1, s2 = c

            # Possible conditions for comparison:
            # 1. Compare a lab with a course section (TODO)
            # 2. Compare sections from two diff. courses
            c2 = s1["course_number"] != s2["course_number"]

            # Only compare if from different courses
            if c2:
                t1 = TimeRange(s1["start_time"], s1["end_time"])
                t2 = TimeRange(s2["start_time"], s2["end_time"])

                # Check for conflict in both days and time
                if any([d in s2["days"] for d in s1["days"]]):
                    if t1 in t2:
                        self.conflicts.append([s1, s2])

    def start(self):
        """Start the scheduler."""
        # Get course info, filtered by gender
        unfiltered_courses = self.get_course_lab_info(self.courses)
        if all([not c for c in unfiltered_courses.values()]):
            raise MissingInfoError

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
            raise CombinationError

        # Get titles and corresponding sections
        course_titles, course_info = list(courses.keys()), list(courses.values())

        # Save sections
        section_info = []
        for v in course_info:
            for s in v.values():
                section_info.append(s)

        # Get final exam conflicts
        self.final_conflicts = self.find_exam_conflicts(courses)

        # Section combinations and conflicts
        combs = self.combs(section_info, [])
        self.conflicts = []
        self.find_section_conflicts(combs)

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
            if (time.time() - start) >= 10 or len(schedules) >= 50:
                break

        self.results = self.convert_to_week_based(schedules)

        # If results, then there are no conflicts
        if self.results:
            self.success = True


if __name__ == "__main__":
    s = Scheduler(["math 1110", "phys 110", "math 1120"], [], "B", "202010")
    s.start()
    print(s.success, len(s.results))
