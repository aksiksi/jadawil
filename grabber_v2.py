import asyncio
import os
import pprint
import random
import string
import time

import aiohttp
import requests


UAEU_BASE_URL = "eservices.uaeu.ac.ae"


def get_session_id():
    session_id = "".join(
        random.sample(string.ascii_lowercase + string.digits, 5)
    ) + str(int(time.time() * 1000))

    return session_id


class CourseGrabber:
    """Grabs courses for one or more terms.

    Args:
        loop: asyncio event loop
        base_url (str): Base Banner URL for university (e.g., eservices.uaeu.ac.ae)"
    """
    def __init__(self, base_url):
        self.session = None

        # Build university-specific URLs
        self.terms_url = "https://%s/StudentRegistrationSsb/ssb/classSearch/getTerms" \
                         "?dataType=json&searchTerm=&offset=1&max=-1" % base_url
        self.start_search_url = \
            "https://%s/StudentRegistrationSsb/ssb/term/search?mode=search" % base_url
        self.reset_search_url = \
            "https://%s/StudentRegistrationSsb/ssb/classSearch/resetDataForm" % base_url
        self.subjects_url = \
            "https://%s/StudentRegistrationSsb/ssb/classSearch/get_subject" \
            "?dataType=json&term={term}&offset=1&max=-1&uniqueSessionId=" \
            "{session_id}" % base_url
        self.courses_url = \
            "https://%s/StudentRegistrationSsb/ssb/searchResults/searchResults" \
            "?txt_subject={subject}&txt_term={term}&startDatepicker=&endDatepi" \
            "cker=&pageOffset={page_offset}&pageMaxSize={page_size}&sortColumn=subjectDescription&" \
            "sortDirection=asc&uniqueSessionId={session_id}" % base_url

    def get_terms(self):
        return [each["code"] for each in requests.get(self.terms_url).json()]

    async def _get_subjects(self, term, client):
        """Get all subjects for a given term."""
        args = {"session_id": self.session_id, "term": term}
        url = self.subjects_url.format(**args)

        async with client.get(url) as resp:
            data = await resp.json()
            print(data)

        return data

    async def _get_courses_page(self, term, subject, session_id, client,
                                page_offset=0, page_size=50):
        args = {"session_id": session_id, "term": term, "subject": subject,
                "page_offset": page_offset, "page_size": page_size}
        url = self.courses_url.format(**args)

        async with client.get(url) as resp:
            data = await resp.json()

        if not data["success"]:
            return ([], 0)

        return (data["data"], data["totalCount"])

    def _transform_courses(self, data, subject):
        # Transform list to dict of subject -> course number -> data
        transformed = {}

        for info in data:
            course_number = info["courseNumber"]
            crn = info["courseReferenceNumber"]

            if subject in transformed:
                if course_number in transformed[subject]:
                    transformed[subject][course_number][crn] = info
                else:
                    transformed[subject][course_number] = {crn: info}
            else:
                transformed[subject] = {course_number: {crn: info}}

        return transformed

    async def _get_courses(self, term, subject):
        session_id = get_session_id()
        payload = {
            "uniqueSessionId": session_id,
            "dataType": "json",
            "term": term,
        }

        client = aiohttp.ClientSession()

        # Start new search session
        async with client.post(self.start_search_url, data=payload) as resp:
            data = await resp.json()

        # Grab first page of course results
        data, total = \
            await self._get_courses_page(term, subject,
                                         session_id, client)
        fetched = len(data)
        if fetched:
            print(f"Requested: {subject}, Actual: {data[0]['subject']}, {fetched}, {total}")

        # Fetch remaining results (via paging)
        while fetched < total:
            # Grab next page of results
            next_data, _ = \
                await self._get_courses_page(term, subject,
                                             session_id, client,
                                             fetched)

            # Terminate if no data was returned for page
            if not next_data:
                break

            data += next_data
            fetched += len(next_data)

            print(f"{subject}: {fetched}, {len(next_data)}, {total}")

        transformed = self._transform_courses(data, subject)

        await client.close()

        return transformed

    async def _search(self, term, subjects):
        """Start a new Banner course search for a given term."""
        # Get all subjects for this term
        if not subjects:
            async with aiohttp.ClientSession() as client:
                subjects = [each["code"] for each in
                            await self._get_subjects(term, client)]

        tasks = [self._get_courses(term, subject) for subject in subjects]

        # Get course data for all subjects in the term
        results = [res for res in await asyncio.gather(*tasks)]

        return results

    async def fetch(self, terms, subjects=[]):
        """Start searching for courses in one or more terms."""
        tasks = [self._search(term, subjects) for term in terms]
        results = await asyncio.gather(*tasks)
        return results

def main():
    grabber = CourseGrabber(base_url=UAEU_BASE_URL)
    terms = grabber.get_terms()
    output = asyncio.run(grabber.fetch(["202010"], ["MATH", "ELEC", "MECH"]))

    #print(output)

if __name__ == "__main__":
    main()
