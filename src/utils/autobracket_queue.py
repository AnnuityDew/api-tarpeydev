"""These files are meant to run locally when necessary, not on the web."""

from itertools import combinations
import pandas as pd
import pathlib
from google.cloud import tasks_v2
from instance.config import (
    GCP_LOCATION,
    GCP_MM_QUEUE,
    GCP_PROJECT,
    GCP_QUEUE_SA_EMAIL,
    OKTA_ENCODED_ID_SECRET,
    API_KEY_NAME,
    API_KEY,
)
import requests


def simulate_all_matchups():
    """Used to queue up all possible matchups for the March Madness simulator."""
    year = input("Year: ")

    # need all team combos for simulation
    all_matchups_df = pd.read_csv(
        pathlib.Path(f"src/db/matchup_table_{year}.csv"),
    )

    # build list of tournament teams
    away_keys = list(all_matchups_df.away_key.unique())
    home_keys = list(all_matchups_df.home_key.unique())
    # TBD is a placeholder not a team
    away_keys.remove("TBD")
    home_keys.remove("TBD")
    tournament_teams = away_keys + home_keys
    tournament_matchups = list(combinations(tournament_teams, 2))
    # generate list of request URLs to queue up
    tournament_game_urls = [
        f"https://api.tarpey.dev/autobracket/sim/{year}/{matchup[0]}/{matchup[1]}/500/10"
        for matchup in tournament_matchups
    ]

    # Create a cloud tasks client
    client = tasks_v2.CloudTasksClient()

    # google cloud task queue info
    project = GCP_PROJECT
    queue = GCP_MM_QUEUE
    location = GCP_LOCATION
    service_account_email = GCP_QUEUE_SA_EMAIL

    # Construct the fully qualified queue name.
    parent = client.queue_path(project, location, queue)

    # initial request for JWT if necessary
    # r = requests.post(
    #     f"https://api.tarpey.dev/security/token",
    #     headers={
    #         "accept": "application/json",
    #         "authorization": "Basic " + OKTA_ENCODED_ID_SECRET,
    #     },
    #     data={"grant_type": "client_credentials", "scope": "all_data"},
    # )

    # now we can construct task queue headers/body
    headers = {
        "accept": "application/json",
        API_KEY_NAME: API_KEY,
    }
    payload = None

    # Construct the requests.
    response_list = []
    for url in tournament_game_urls:
        new_task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "oidc_token": {"service_account_email": service_account_email},
            }
        }
        if headers is not None:
            new_task["http_request"]["headers"] = headers
        if payload is not None:
            # The API expects a payload of type bytes.
            converted_payload = payload.encode()

            # Add the payload to the request.
            new_task["http_request"]["body"] = converted_payload

        response = client.create_task(request={"parent": parent, "task": new_task})
        print("Created task {}".format(response.name))
        response_list.append(response)

    return response_list


if __name__ == "__main__":
    simulate_all_matchups()
