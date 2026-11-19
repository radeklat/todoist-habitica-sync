<h1 align="center" style="border-bottom: none;">:ballot_box_with_check::crossed_swords:&nbsp;&nbsp; Todoist ⇒ Habitica Sync &nbsp;&nbsp;:crossed_swords::ballot_box_with_check:</h1>
<h3 align="center">One way synchronisation from Todoist to Habitica</h3>

<p align="center">
    <img alt="CircleCI" src="https://img.shields.io/circleci/build/github/radeklat/todoist-habitica-sync">
    <img alt="Codecov" src="https://img.shields.io/codecov/c/github/radeklat/todoist-habitica-sync">
    <img alt="GitHub tag (latest SemVer)" src="https://img.shields.io/github/tag/radeklat/todoist-habitica-sync">
    <img alt="Maintenance" src="https://img.shields.io/maintenance/yes/2025">
    <img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/radeklat/todoist-habitica-sync">
    <img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/radeklat/todoist-habitica-sync">
    <img alt="Docker Image Version (latest semver)" src="https://img.shields.io/docker/v/radeklat/todoist-habitica-sync?label=image%20version">
    <img alt="Docker Image Size (latest semver)" src="https://img.shields.io/docker/image-size/radeklat/todoist-habitica-sync">
</p>

Because if you want to be productive, you should not track tasks in two places. Habitica is great for tracking habits, Todoist for tracking TODOs. Now you can get the best of both.

## How it works

Tasks are not added immediately. Only when you finish a task in Todoist, new task will be created in Habitica, finished and immediately deleted. So you won't see any Todoist tasks in Habitica but still get the rewards.

# Features

* Scores points in Habitica when Todoist task is finished.
* Works for recurring tasks in Todoist: every completion scores, read from the Todoist API v1 activity log.
* Only tasks completed by you score, not ones completed by collaborators in shared projects.
* Optional nightly penalty for overdue tasks (off by default, see below).

## Nightly penalty

Off by default. When `NIGHTLY_PENALTY_ENABLED=true`, once a night at `PENALTY_TIME` (in your Todoist timezone) the service counts overdue Todoist tasks that are assigned to you or to no one. It then taps a negative Habitica habit (`PENALTY_HABIT_NAME`, created if missing) once per task, up to `PENALTY_MAX_PER_NIGHT`. The aim is to have every task accounted for (done, rescheduled or dropped) before bed.

* Tasks with any of the `PENALTY_EXCLUDE_LABELS` never count.
* If any active task has the `PENALTY_PAUSE_LABEL` label, the night is skipped (e.g. for holidays).
* On the first start, nothing is charged; penalties start the following night.
* If the service could not run within `PENALTY_WINDOW_HOURS` after `PENALTY_TIME` (e.g. the server was off), that night is skipped. It never charges late.
* Progress is stored in the sync cache, so a restart in the middle of the night neither skips nor repeats taps.

# Installation

## As a script

1. Open terminal
2. Make sure [`git`](https://github.com/git-guides/install-git) is installed:
   ```shell script
   git --version   
   ```
   The output should look something like:
   ```text
   git version 2.25.1
   ```
3. Make sure Python 3.12.x is installed:
   ```shell script
   python --version
   ```
   The output should look something like:
   ```text
   Python 3.12.0
   ```
   * If it shows `2.7.x` instead, try `python3` instead and use it in the rest of the guide.
   * If it shows `3.11.x` or lower, use [`pyenv`](https://github.com/pyenv/pyenv#installation) to install a higher version of Python on your system.
4. Make sure [`poetry`](https://python-poetry.org/docs/#installation) is installed:
   ```shell script
   poetry --version
   ```
   The output should look something like:
   ```
   Poetry (version 1.7.1)
5. Clone this repository:
   ```shell script
   git clone https://github.com/radeklat/todoist-habitica-sync.git
   cd todoist-habitica-sync
   ```
6. Copy the `.env.template` file into `.env` file:
   ```shell script
   cp .env.template .env
   ```
7. Edit the `.env` file, fill all missing values and/or change existing ones to suit your needs.
8. Install all application dependencies:
   ```shell script
   poetry install --no-root --without=dev
   ```
9. Run the app:
    ```shell script
    poetry run python src/main.py
    ```

## As a docker container

1. Open terminal
2. Make sure [`docker`](https://docs.docker.com/get-docker/) is installed:
   ```shell script
   docker --version   
   ```
   The output should look something like:
   ```text
   Docker version 20.10.5, build 55c4c88
   ```
3. Create a base folder structure for the service:
   ```shell script
   mkdir -p todoist-habitica-sync/.sync_cache
   cd todoist-habitica-sync
   chmod 0777 .sync_cache
   # Download .env file template
   curl https://raw.githubusercontent.com/radeklat/todoist-habitica-sync/master/.env.template --output .env
   ```
4. Edit the `.env` file and fill the missing details.
5. Run the container:
   ```shell script
   docker run \
      --pull always --rm --name todoist-habitica-sync \
      --env-file=.env \
      -v $(pwd)/.sync_cache:/app/.sync_cache \
      radeklat/todoist-habitica-sync:latest
   ```
   This configuration will run the service in the foreground (you need to keep the terminal open) and always use the latest version.
   * Change `latest` to [a specific version](https://hub.docker.com/repository/registry-1.docker.io/radeklat/todoist-habitica-sync/tags) if you don't always want the latest version or remove the `--pull always` flag to not update.


Add `--detach` flag to run in the background. You can close the terminal, but it will not start on system start up.
* To see the log of the service running in the background, run `docker logs todoist-habitica-sync`
* To stop the service, run `docker container stop todoist-habitica-sync`

## As a service

You can use the above mentioned docker image to run the sync as a service on server or even your local machine. The simples way is to use docker compose:

1. Make sure you have [`docker`](https://docs.docker.com/get-docker/) installed:
   ```shell script
   docker --version
   docker compose version
   ```
   The output should look something like:
   ```text
   Docker version 23.0.2, build 569dd73
   Docker Compose version v2.17.2
   ```
2. Download the example compose file:
   ```shell script
   mkdir -p todoist-habitica-sync/.sync_cache
   cd todoist-habitica-sync
   chmod 0777 .sync_cache
   ```
3. Download a compose file and an example .env file:
   ```shell script
   BASE_URL=https://raw.githubusercontent.com/radeklat/todoist-habitica-sync/master
   curl $BASE_URL/.env.template --output .env
   curl $BASE_URL/docker-compose.yml -O
   ```
4. Edit the `.env` file and fill the missing details.
5. Run the service:
   ```shell script
   docker compose up
   ```
   This command will run the service in the foreground (you need to keep the terminal open) and always use the latest version.
   * Change `latest` to [a specific version](https://hub.docker.com/repository/registry-1.docker.io/radeklat/todoist-habitica-sync/tags) if you don't always want the latest version.


Add `--detach` flag to run in the background. You can close the terminal. The service should start on system start up.
* To see the log of the service running in the background, run `docker-compose logs todoist-habitica-sync`
* To stop the service, run `docker-compose stop todoist-habitica-sync`

# Update

## As a script

1. Open terminal
2. Navigate to the project repository:
   ```shell script
   cd todoist-habitica-sync
   ```
3. Update the source code:
   ```shell script
   git pull
   ```

4. Update application dependencies:
   ```shell script
   poetry install --no-dev
   ```
5. Run the application again.

## From docker-compose

If you used the `latest` tag, run:

```shell script
docker compose stop  # stop the container
docker compose pull todoist-habitica-sync  # pull a new image
docker compose up -d --force-recreate  # re-create container with the new image
docker image prune -f  # clean up unused images
```

# Environment variables
<!-- settings-doc start -->
## `TODOIST_USER_ID`

*Optional*, default value: `None`

See "user_id" mentioned in a link under "Calendar Subscription URL" at https://todoist.com/prefs/integrations. Needed only for shared projects to score points for tasks owned by you.

## `TODOIST_API_KEY`

**Required**

See https://todoist.com/prefs/integrations under "API token".

## `HABITICA_USER_ID`

**Required**

See https://habitica.com/user/settings/api under "User ID".

## `HABITICA_API_KEY`

**Required**

See https://habitica.com/user/settings/api under "API Token", the "Show API Token" button.

## `SYNC_DELAY_MINUTES`

*Optional*, default value: `1`

Repeat sync automatically after N minutes.

## `DATABASE_FILE`

*Optional*, default value: `.sync_cache/sync_cache.sqlite`

Where to store synchronisation details. No need to change.

## `PRIORITY_TO_DIFFICULTY`

*Optional*, default value: `{'P1': 'HARD', 'P2': 'MEDIUM', 'P3': 'EASY', 'P4': 'TRIVIAL'}`

Defines how Todoist priorities map to Habitica difficulties. Keys/values are case-insensitive and can be both names or numerical values defines by the APIs. See https://habitica.com/apidoc/#api-Task-CreateUserTasks and https://developer.todoist.com/api/v1/ (task `priority`: 4 is p1, 1 is p4) for numerical values definitions.

## `LABEL_TO_DIFFICULTY`

*Optional*

Defines how Todoist labels map to Habitica difficulties. Keys are case-insensitive. See https://habitica.com/apidoc/#api-Task-CreateUserTasks for difficulty values. If a task has no matching label, the `priority_to_difficulty` mapping is used. If a task has multiple labels, the highest difficulty is used.

## `NIGHTLY_PENALTY_ENABLED`

*Optional*, default value: `False`

Once a night, tap a negative Habitica habit for each overdue Todoist task assigned to you or to no one. Costs HP, so it is off by default.

## `PENALTY_TIME`

*Optional*, default value: `00:05`

Local time (HH:MM, in your Todoist timezone) to run the nightly penalty.

## `PENALTY_WINDOW_HOURS`

*Optional*, default value: `4`

If the nightly penalty could not run within this many hours after `PENALTY_TIME` (e.g. the server was off), that night is skipped. It never charges late.

## `PENALTY_MAX_PER_NIGHT`

*Optional*, default value: `5`

Most habit taps per night.

## `PENALTY_HABIT_NAME`

*Optional*, default value: `Unaccounted task`

The Habitica habit to tap for the nightly penalty. It is created if missing.

## `PENALTY_EXCLUDE_LABELS`

*Optional*, default value: `Exclude,no_penalty`

Comma-separated Todoist labels (case-insensitive) whose tasks never count for the nightly penalty.

## `PENALTY_PAUSE_LABEL`

*Optional*, default value: `pause_penalties`

If any active Todoist task has this label (case-insensitive), the nightly penalty skips the night.
<!-- settings-doc end -->

# Resetting sync cache

Sometimes certain changes require to reset the sync cache. The cache holds state information only to allow recovery after an unexpected termination of the program. So it is not needed in between restarts and can be safely removed.

To reset the cache:
1. Stop the application.
2. Remove the `.sync_cache/sync_cache.sqlite` file or any other location given in the [`DATABASE_FILE`](#database_file) config option.
3. Optionally, [update the application](#update).
4. Start to application again.

# Development

Tests mock all HTTP calls and never reach the real Todoist or Habitica APIs. Run them against the pinned dependencies in `poetry.lock`:

```shell script
poetry install --no-root
poetry run pytest
```

GitHub Actions runs the tests on every pull request. On every push to `main` it builds a `linux/amd64` image and pushes it to `ghcr.io/<owner>/todoist-habitica-sync` with the tags `latest` and `sha-<commit>`.
