import asyncio
import json
import os
import random
import string
import time
from typing import List

import aiohttp
import requests


BASE_URL = "eservices.uaeu.ac.ae"
PAGE_SIZE = 50
MAX_TIMEOUT = 10


def get_session_id():
    session_id = "".join(
        random.sample(string.ascii_lowercase + string.digits, 5)
    ) + str(int(time.time() * 1000))

    return session_id


class CourseGrabber:
    """Grabs courses for one or more terms.

    Args:
        base_url (str): Base Banner URL for university (e.g., eservices.uaeu.ac.ae)"
        timeout (int): Max timeout for each request, in seconds
    """
    def __init__(self, base_url: str=BASE_URL, timeout: int=MAX_TIMEOUT):
        self.timeout = timeout

        # Build university-specific URLs
        self.terms_url = "https://%s/StudentRegistrationSsb/ssb/classSearch/getTerms" \
                         "?dataType=json&searchTerm=&offset=1&max=-1" % base_url
        self.start_search_url = \
            "https://%s/StudentRegistrationSsb/ssb/term/search?mode=search" % base_url
        self.reset_search_url = \
            "https://%s/StudentRegistrationSsb/ssb/classSearch/resetDataForm" % base_url
        self.subjects_url = \
            "https://%s/StudentRegistrationSsb/ssb/classSearch/get_subject" \
            "?dataType=json&term={term}&offset=1&max=-1" % base_url
        self.courses_url = \
            "https://%s/StudentRegistrationSsb/ssb/searchResults/searchResults" \
            "?txt_subject={subject}&txt_term={term}&startDatepicker=&endDatepi" \
            "cker=&pageOffset={page_offset}&pageMaxSize={page_size}&sortColumn=subjectDescription&" \
            "sortDirection=asc&uniqueSessionId={session_id}" % base_url

    def get_terms(self):
        return [each["code"] for each in requests.get(self.terms_url).json()]

    async def _get_subjects(self, term: str):
        """Get all subjects for a given term."""
        args = {"term": term}
        url = self.subjects_url.format(**args)

        async with aiohttp.ClientSession() as client:
            async with client.get(url) as resp:
                data = await resp.json()

        return data

    async def _get_courses_page(self, term: str, subject: str, session_id: str,
                                client: aiohttp.ClientSession,
                                page_offset: int=0, page_size: int=PAGE_SIZE):
        args = {"session_id": session_id, "term": term, "subject": subject,
                "page_offset": page_offset, "page_size": page_size}
        url = self.courses_url.format(**args)

        try:
            async with client.get(url, timeout=self.timeout) as resp:
                data = await resp.json()
        except Exception:
            print(f"{subject}: timed out")
            return ([], 0)

        if not data["success"]:
            return ([], 0)

        return (data["data"], data["totalCount"])

    def _transform_courses(self, data, subject: str):
        # Transform list to dict of subject -> course number -> data
        transformed = {subject: {}}

        for info in data:
            course_number = info["courseNumber"]
            crn = info["courseReferenceNumber"]

            if course_number in transformed[subject]:
                transformed[subject][course_number][crn] = info
            else:
                transformed[subject][course_number] = {crn: info}

        return transformed

    async def _get_courses(self, term: str, subject: str):
        session_id = get_session_id()
        payload = {
            "uniqueSessionId": session_id,
            "dataType": "json",
            "term": term,
        }

        client = aiohttp.ClientSession()

        # Start new search session
        try:
            async with client.post(self.start_search_url, data=payload,
                                   timeout=self.timeout) as resp:
                data = await resp.json()
        except Exception:
            print(f"{subject}: search timed out")
            await client.close()
            return {subject: {}}

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

    async def search(self, term: str, subject: str):
        """Start a new Banner course search for a given term and subject."""
        print(f"Starting {subject}")
        result = await self._get_courses(term, subject)
        print(f"Done with {subject}")
        return result

    async def fetch(self, term: str):
        """Fetch all courses in a given term."""
        # Get all subjects for this term
        subjects = [each["code"] for each in
                    await self._get_subjects(term)]

        print(f"{term}: number of subjects is {len(subjects)})"

        tasks = [self.search(term, subject) for subject in subjects]

        print(f"{term}: started")
        results = await asyncio.gather(*tasks)
        print(f"{term}: completed")

        return results

    async def fetch_all(self, terms: List[str]):
        """Fetch all courses for one or more terms."""
        tasks = [self.fetch(term) for term in terms]
        return await asyncio.gather(*tasks)


def main():
    grabber = CourseGrabber()

    # Grab all course data for latest 3 terms
    terms = grabber.get_terms()[:3]
    results = asyncio.run(grabber.fetch_all(terms))

    for term, output in zip(terms, results):
        course_data = {}

        for each in output:
            subject = list(each.keys())[0]
            data = each[subject]

            course_data[subject] = data

        with open(f"/tmp/courses-{term}.json", "w") as f:
            json.dump(course_data, f)


if __name__ == "__main__":
    main()
