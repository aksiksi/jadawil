import mechanize
import cookielib
import cPickle
from bs4 import BeautifulSoup

def html_to_pickle(source):
    '''Collect data from HTML source and write it to a pickle.'''
    headers = ['status', 'crn', 'abbrev', 'code', 'section', 'gender', 'credits',
               'title', 'days', 'time', 'total', 'current', 'remaining', 'instructor',
               'duration', 'location', 'attribute']

    # Create BeautifulSoup object with lxml as parser
    soup = BeautifulSoup(source, 'lxml')

    # Get all courses from DOM
    rows = soup.find_all('tr')
    courses = [row for row in rows if row.select('.dddefault')] # Keep only valid courses

    # Order course data by course abbreviation (ex: PHYS)
    courses_by_abbrev = {}

    for course in courses:
        cols = [each.text for each in course.select('.dddefault')]
        
        # Create dict for each valid section
        if len(cols) == 17:
            info = {header:col for header, col in zip(headers, cols)}
        
        # Add course to course dict under correct abbrev, code, and crn
        if info['abbrev'] not in courses_by_abbrev:
            courses_by_abbrev[info['abbrev']] = {info['code']: {info['crn']: info}}
        else:
            current = courses_by_abbrev[info['abbrev']]
            if info['code'] in current:
                current[info['code']][info['crn']] = info
            else:
                current[info['code']] = {info['crn']: info}

    # Write dict to pickle
    cPickle.dump(courses_by_abbrev, open('classes.pickle', 'wb'))

def source_grabber():
    '''Grab the course search source code using a Mechanize browser.'''
    # Required inputs
    terms = ['201320', '201310'] # Terms (spring, fall, etc.)
    username = '201150160'
    password = 'kasserine'

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
    br.select_form(nr=0)
    br['sid'] = username
    br['PIN'] = password
    br.submit()

    # Go to course search page
    br.open('https://ssb.uaeu.ac.ae/prod/bwskfcls.p_sel_crse_search')

    # Choose current term by manipulating first form on page then submit
    br.select_form(nr=1)
    br['p_term'] = [terms[0]]
    br.submit()

    # Find possible selections for select control, then select all subjects and search
    br.select_form(nr=1)
    select = br.controls[11]
    options = [item.name for item in select.items]
    br.controls[11].value = options
    br.submit()

    # Get page source
    response = br.response()
    source = response.read()

    return source

def main():
    # Get source, collect data from it, then write it to pickle
    html_to_pickle(source_grabber())

if __name__ == '__main__':
    main()