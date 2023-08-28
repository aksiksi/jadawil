import asyncio
import logging
import random
import string
import time
from typing import List

import aiohttp
import jsonlines
import requests


BASE_URL = "eservices.uaeu.ac.ae"
PAGE_SIZE = 50
MAX_TIMEOUT = 10
MAX_RESULTS = 100_000

# Setup a basic stdout logger
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(fmt="[%(asctime)s] %(message)s",
                      datefmt="%d/%m/%Y %I:%M:%S %p")
)
log.addHandler(handler)


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
                         "?dataType=json&searchTerm=&offset=1&max=%d" % (base_url, MAX_RESULTS)
        self.start_search_url = \
            "https://%s/StudentRegistrationSsb/ssb/term/search?mode=search" % base_url
        self.reset_search_url = \
            "https://%s/StudentRegistrationSsb/ssb/classSearch/resetDataForm" % base_url
        self.subjects_url = \
            "https://%s/StudentRegistrationSsb/ssb/classSearch/get_subject" \
            "?dataType=json&term={term}&offset=1&max=%d" % (base_url, MAX_RESULTS)
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
            log.info(f"{subject}: timed out")
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
            log.info(f"{subject}: search timed out")
            await client.close()
            return []

        # Grab first page of course results
        data, total = \
            await self._get_courses_page(term, subject,
                                         session_id, client)
        fetched = len(data)
        if fetched:
            log.info(f"Requested: {subject}, Actual: {data[0]['subject']}, "
                     f"{fetched}, {total}")

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

            log.info(f"{subject}: {fetched}, {len(next_data)}, {total}")

        await client.close()

        return data

    async def search(self, term: str, subject: str):
        """Start a new Banner course search for a given term and subject."""
        log.info(f"Starting {subject}")
        result = await self._get_courses(term, subject)
        log.info(f"Done with {subject}")
        return result

    async def fetch(self, term: str):
        """Fetch all courses in a given term."""
        # Get all subjects for this term
        subjects = [each["code"] for each in
                    await self._get_subjects(term)]

        log.info(f"{term}: number of subjects is {len(subjects)}")

        tasks = [self.search(term, subject) for subject in subjects]

        log.info(f"{term}: started")
        results = []
        for result in await asyncio.gather(*tasks):
            results += result
        log.info(f"{term}: completed")

        return results

    async def fetch_all(self, terms: List[str]):
        """Fetch all courses for one or more terms."""
        tasks = [self.fetch(term) for term in terms]
        return await asyncio.gather(*tasks)


def collect_stats(term: str, data):
    """Collect stats on each term."""
    stats = {
        "num_courses": {
            "b": 0,
            "g": 0,
        },
        "num_instructors": {
            "b": 0,
            "g": 0,
        },
        "num_sections": {
            "b": 0,
            "g": 0,
            "mw": {
                "b": 0,
                "g": 0,
            },
            "tu": {
                "b": 0,
                "g": 0,
            },
        },
        "num_seats_available": {
            "b": 0,
            "g": 0,
        },
        "num_seats_taken": {
            "b": 0,
            "g": 0,
        },
        "total_credit_hours": {
            "b": 0,
            "g": 0,
        },
    }

    courses = {
        "b": set(),
        "g": set(),
    }

    instructors = {
        "b": set(),
        "g": set(),
    }

    for section in data:
        class_info = [s["meetingTime"] for s in section["meetingsFaculty"]
                      if s["meetingTime"]["meetingType"] == "CLAS"]
        if not class_info or not class_info[0] or not class_info[0]["campus"]:
            continue

        class_info = class_info[0]

        if "B" in class_info["campus"]:
            campus = "b"
        else:
            campus = "g"

        subject, number = section["subject"], section["courseNumber"]
        course_code = f"{subject} {number}".upper()
        courses[campus].add(course_code)

        for f in section["faculty"]:
            instructors[campus].add(f["displayName"])

        stats["num_sections"][campus] += 1

        if class_info["monday"] and class_info["wednesday"]:
            stats["num_sections"]["mw"][campus] += 1
        elif class_info["sunday"] and class_info["tuesday"]:
            stats["num_sections"]["tu"][campus] += 1

        stats["num_seats_available"][campus] += section["maximumEnrollment"]
        stats["num_seats_taken"][campus] += (
            section["maximumEnrollment"] - section["seatsAvailable"]
        )

        if class_info["creditHourSession"]:
            stats["total_credit_hours"][campus] += class_info["creditHourSession"]

    for c in ["b", "g"]:
        stats["num_courses"][c] = len(courses[c])
        stats["num_instructors"][c] = len(instructors[c])

    stats["timestamp"] = time.time() * 1000

    return stats


def main():
    grabber = CourseGrabber()

    terms = [t for t in grabber.get_terms()[:3]
             if t[-2:] != "00"]

    # Grab all course data for latest 3 valid terms
    results = asyncio.run(grabber.fetch_all(terms))

    for term, output in zip(terms, results):
        data_file = f"classes/{term}.jsonl"
        stats_file = f"classes/{term}-stats.jsonl"

        # Dumps all sections for the course, one JSON object per line
        # Uses the JSON lines format
        with jsonlines.open(data_file, mode="w") as writer:
            writer.write_all(output)

        # Dump stats for this term
        stats = collect_stats(term, output)
        with jsonlines.open(stats_file, mode="a") as writer:
            writer.write(stats)


if __name__ == "__main__":
    # Update course data
    main()

    # Write last update time to file
    with open("last.txt", "w") as f:
        f.write(str(time.time()))
