from __future__ import print_function
import mechanize
import cookielib
import cPickle as pickle
import os
from bs4 import BeautifulSoup
from collections import defaultdict
from secret import username, password

# Terms
terms = ['201620', '201610', '201520', '201510']

def html_to_pickle(source, term):
    '''Collect data from HTML source and write it to a pickle.'''
    headers = ['status', 'crn', 'abbrev', 'code', 'section', 'gender', 'credits',
               'title', 'days', 'time', 'total', 'current', 'remaining', 'instructor',
               'duration', 'location', 'attribute']

    print("Parsing HTML...")

    # Create BeautifulSoup object with lxml as parser
    soup = BeautifulSoup(source, 'lxml')

    # Get all courses from DOM
    rows = soup.find_all('tr')
    courses = [row for row in rows if row.select('.dddefault')] # Keep only valid courses

    # Order course data by course abbreviation (ex: PHYS)
    courses_by_abbrev = {}

    for index, course in enumerate(courses):
        # Get the cols from each course row
        cols = [each.text for each in course.select('.dddefault')]

        # Create dict for each valid section and add to final dict
        if len(cols) == 17:
            info = {header:col for header, col in zip(headers, cols)}

            # If there are 11 or 12 empty columns, check if this entry is related to previous entry; if it is, do some magic
            if cols.count(u'\xa0') in [11, 12]:
                # Find info of previous entry (already in the form of a dict)
                previous_info = courses[index-1]

                abbrev, code, crn, days = previous_info['abbrev'], previous_info['code'], \
                                          previous_info['crn'], info['days']

                # DEBUG
                # c = abbrev == 'ITBP' and code == '219' and previous_info['gender'] == 'G'

                # Check if previous entry is indeed the correct parent AND not a lab
                if previous_info.values().count(u'\xa0') not in [11, 12] and 'L' not in crn:
                    try:
                        # Days of duration in dd/m-dd/m format
                        duration_days = info['duration'].split('-')
                    except:
                        duration_days = [-1, -1]

                    # Verify duration to make sure it's not a final exam date
                    if duration_days[0] != duration_days[1]:

                        # If the instructor is the same, simply add the second day to the original entry
                        if info['instructor'] in [previous_info['instructor'], 'TBA']:
                            if days != previous_info['days']:
                                # Append day to previous day only if different
                                courses_by_abbrev[abbrev][code][crn]['days'] += days
                            else:
                                # Stupid fix for MECH labs..
                                courses_by_abbrev[abbrev][code][crn]['days'] = days

                        # Otherwise, make it a lab section (see: ITBP 319 Spring 2013)
                        else:
                            for key in info:
                                # Fill up any empty info
                                if info[key] == u'\xa0':
                                    # Append a 'L' to section or crn
                                    if key == 'section' or key == 'crn':
                                        info[key] = 'L' + previous_info[key]
                                    # Add lab to title
                                    elif key == 'title':
                                        info[key] = previous_info[key] + ' (Lab)'
                                    # Set credits to 0 for lab
                                    elif key == 'credits':
                                        info[key] = '0.00'
                                    else:
                                        info[key] = previous_info[key]

                    # In case it is a final exam date
                    else:
                        if duration_days[0] != -1:
                            courses_by_abbrev[abbrev][code][crn]['final_date'] = duration_days[0]
                            courses_by_abbrev[abbrev][code][crn]['final_time'] = info['time']

                # If the previous entry is "invalid" or a lab, go back two steps -- for final exam checks and additional days
                else:
                    # Get the info of the entry two steps back
                    previous_info = courses[index-2]

                    # Verify that this is the correct parent
                    if previous_info.values().count(u'\xa0') not in [11, 12]:
                        # Add the info needed
                        abbrev, code, crn, days = previous_info['abbrev'], previous_info['code'], \
                                                  previous_info['crn'], info['days']

                        duration_days = info['duration'].split('-')

                        # Maybe final exam date? If so, record that shit
                        if duration_days[0] == duration_days[1]:
                            courses_by_abbrev[abbrev][code][crn]['final_date'] = duration_days[0]
                            courses_by_abbrev[abbrev][code][crn]['final_time'] = info['time']

                        # If instructor same but days not same, add new day
                        elif info['instructor'] in [previous_info['instructor'], 'TBA'] and days != previous_info['days']:
                            courses_by_abbrev[abbrev][code][crn]['days'] += days

                        # If diff. instructor, perhaps a lab??
                        else:
                            for key in info:
                                # Fill up any empty info
                                if info[key] == u'\xa0':
                                    # Append a 'L' to section or crn
                                    if key == 'section' or key == 'crn':
                                        info[key] = 'L' + previous_info[key]
                                    # Add lab to title
                                    elif key == 'title':
                                        info[key] = previous_info[key] + ' (Lab)'
                                    # Set credits to 0 for lab
                                    elif key == 'credits':
                                        info[key] = '0.00'
                                    else:
                                        info[key] = previous_info[key]

                    # WOW INCEPTION -- move back 3 entries to find parent (?)
                    else:
                        pass

            abbrev, code, crn = info['abbrev'], info['code'], info['crn']

            # Add course to course dict under correct abbrev, code, and crn
            if abbrev not in courses_by_abbrev:
                courses_by_abbrev[abbrev] = {code: {crn: info}}
            else:
                current = courses_by_abbrev[abbrev]
                if code in current:
                    current[code][crn] = info
                else:
                    current[code] = {crn: info}

            courses[index] = info

    # Write final dict to pickle dir
    with open('classes/classes-{}.pickle'.format(term), 'wb') as f:
        pickle.dump(courses_by_abbrev, f)

    # TESTING
    # with open('testingabc.pickle', 'wb') as f:
    #     pickle.dump(courses_by_abbrev, f)

def source_grabber(term):
    '''Grab the course search source code using a Mechanize browser.'''
    # Browser instance
    br = mechanize.Browser()

    # Browser emulation settings
    br.set_handle_equiv(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    br.set_debug_http(False)
    br.set_debug_responses(False)
    br.set_debug_redirects(False)
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    # Open eServices
    br.open('https://ssb.uaeu.ac.ae/prod/bwskfcls.p_sel_crse_search')

    # Login
    br.select_form(name='loginform')
    br['sid'] = username
    br['PIN'] = password
    br.submit()

    print("Logging in as {}".format(username))

    # Go to course search page
    br.open('https://ssb.uaeu.ac.ae/prod/bwskfcls.p_sel_crse_search')

    # Choose current term by manipulating first form on page then submit
    br.select_form(nr=1)
    br['p_term'] = [term]
    br.submit()

    print("Selected term {}".format(term))

    # Move to advanced search page
    br.select_form(nr=1)
    br.submit(name='SUB_BTN', label='Advanced Search')

    # Find possible selections for select control, then select all subjects and search
    br.select_form(nr=1)
    select = br.controls[13]
    options = [item.name for item in select.items]
    br.controls[13].value = options
    br.submit()

    print("Search submitted")

    # Get page source
    response = br.response()
    source = response.read()

    return source

def main():
    # Get source, collect data from it, then write it to pickle
    html_to_pickle(source_grabber(terms[0]), terms[0])

    # for term in terms:
    #     html_to_pickle(source_grabber(term), term)

    #TESTING
    # with open('testingabc.html') as f:
    #     html_to_pickle(f.read(), '201610')

if __name__ == '__main__':
    main()
