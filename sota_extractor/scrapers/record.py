import requests

from sota_extractor.errors import HttpClientError
from sota_extractor.scrapers.utils import date_from_timestamp, sround
from sota_extractor.taskdb.v01 import SotaRow, Dataset, Task, Link, TaskDB


URL = "https://sheng-z.github.io/ReCoRD-explorer/"
JSON_URL = (
    "https://raw.githubusercontent.com/sheng-z/ReCoRD-explorer/master/"
    "codalab/output/out-v1.0.json"
)

TASK_NAME = "Common Sense Reasoning"
DATASET_NAME = "ReCoRD"


def get_sota_rows(data):
    rows = data["leaderboard"]

    sota_rows = []
    for row in rows:
        # HACK: This hack with the timezone is needed because the person who
        #       maintains the leaderboard uses local timezone. He just runs the
        #       gulp html generation script in (from github profile) Redmond/WA
        #       which is in the US/Pacific zone so we need to parse the
        #       timestamp like we are in that zone to get the same dates they
        #       get.
        date = date_from_timestamp(
            row.get("submission", {}).get("created", None), tz="US/Pacific"
        )

        description = row.get("submission", {}).get("description", "").strip()
        # This peace of a the code is taken from gulpfile.js translated to py
        model_name = description[: description.rfind("(")].strip()
        # _first_part = description[description.rfind("(") + 1 :]
        # _institution = _first_part[: _first_part.rfind(")")]
        if description.rfind("http") != -1:
            link = description[description.rfind("http") :].strip()
        else:
            link = ""

        em = row.get("scores", {}).get("exact_match", None)
        f1 = row.get("scores", {}).get("f1", None)

        # Skip rows with no values
        if em is None or f1 is None:
            continue

        sota_rows.append(
            SotaRow(
                model_name=model_name,
                paper_title=link,
                paper_url=link,
                paper_date=date,
                metrics={"EM": sround(em, 3), "F1": sround(f1, 3)},
            )
        )
    return sota_rows


def record() -> TaskDB:
    """Extract ReCoRD SOTA tables."""
    try:
        data = requests.get(JSON_URL).json()
    except Exception as e:
        raise HttpClientError(message=str(e))

    dataset = Dataset(name=DATASET_NAME, is_subdataset=False,)
    task = Task(name=TASK_NAME)
    task.datasets = [dataset]
    task.source_link = Link(title="ReCoRD Leaderboard", url=URL)

    # scrape the evaluation values on the two datasets
    dataset.sota.metrics = ["EM", "F1"]

    dataset.sota.rows = get_sota_rows(data)

    tdb = TaskDB()
    tdb.add_task(task)
    return tdb
