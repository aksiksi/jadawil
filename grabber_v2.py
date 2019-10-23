import os
import random
import string
import time

import requests

from selenium import webdriver

ESERVICES_REG_PAGE = "https://eservices.uaeu.ac.ae/StudentRegistrationSsb/ssb/registration"
USERNAME = os.getenv("BANNER_USERNAME")
PASSWORD = os.getenv("BANNER_PASSWORD")
SESSION_CHARS = string.ascii_lowercase + string.digits


def get_new_timestamp():
    return str(int(time.time() * 1000))


print("Starting up Selenium...")
options = webdriver.FirefoxOptions()
options.add_argument('--headless')
driver = webdriver.Firefox(options=options)
driver.delete_all_cookies()

print("Getting first page...")
driver.get(ESERVICES_REG_PAGE)

# Authenticate via SAML/SSO
# Go to auth. only page
#elem = driver.find_element_by_id("preRegLink")
#elem.click()
#
## Enter user/pass and submit
#print("Authenticating...")
#user = driver.find_element_by_name("username")
#password = driver.find_element_by_name("password")
#user.send_keys(USERNAME)
#password.send_keys(PASSWORD)
#driver.find_element_by_class_name("credentials_input_submit").click()

# Store cookies in a Requests session
session = requests.Session()
# cookies = driver.get_cookies()
# print(cookies)
# for cookie in cookies:
#     session.cookies.set(cookie["name"], cookie["value"])

# Get all available terms
resp = session.get("https://eservices.uaeu.ac.ae/StudentRegistrationSsb/ssb/classSearch/getTerms?dataType=json&searchTerm=&offset=1&max=-1")
latest_term = resp.json()[2]["code"]
print(resp.json())

# Generate a random 18 character session ID
# From Banner JS: combine a random 5-letter string with current timestamp
session_id = "".join(random.sample(string.ascii_lowercase, 5)) + get_new_timestamp()

# Start a search
data = {
    "uniqueSessionId": session_id,
    "dataType": "json",
    "term": latest_term,
}
resp = session.post("https://eservices.uaeu.ac.ae/StudentRegistrationSsb/ssb/term/search?mode=search", data=data)
print(resp)

# Get all available subjects for latest term
resp = session.get(f"https://eservices.uaeu.ac.ae/StudentRegistrationSsb/ssb/classSearch/get_subject?dataType=json&term={latest_term}&offset=1&max=-1&uniqueSessionId={session_id}&_={get_new_timestamp()}")
print(resp.json())

subject = "MATH"

# Get MATH subject
resp = session.get(f"https://eservices.uaeu.ac.ae/StudentRegistrationSsb/ssb/classSearch/get_subject?dataType=json&term={latest_term}&offset=1&max=10&searchTerm={subject}&uniqueSessionId={session_id}&_={get_new_timestamp()}")
print(resp.json())

resp = session.get(f"https://eservices.uaeu.ac.ae/StudentRegistrationSsb/ssb/searchResults/searchResults?txt_subject={subject}&txt_term={latest_term}&startDatepicker=&endDatepicker=&pageOffset=0&pageMaxSize=10&sortColumn=subjectDescription&sortDirection=asc&uniqueSessionId={session_id}")
print(resp.json().keys())

# To start another search
resp = session.post("https://eservices.uaeu.ac.ae/StudentRegistrationSsb/ssb/classSearch/resetDataForm", data={"uniqueSessionId": session_id})

resp = session.get(f"https://eservices.uaeu.ac.ae/StudentRegistrationSsb/ssb/searchResults/searchResults?txt_subject=ELEC&txt_term={latest_term}&startDatepicker=&endDatepicker=&pageOffset=0&pageMaxSize=10&sortColumn=subjectDescription&sortDirection=asc&uniqueSessionId={session_id}")
print(resp.json().keys())
