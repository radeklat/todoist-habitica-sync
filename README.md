[![Master Build Status](https://travis-ci.org/radeklat/todoist-habitica-points-sync.svg?branch=master)](https://travis-ci.org/radeklat/todoist-habitica-points-sync)
[![Develop Build Status](https://travis-ci.org/radeklat/todoist-habitica-points-sync.svg?branch=develop)](https://travis-ci.org/radeklat/todoist-habitica-points-sync)

# NOTE FOR PEOPLE ACCIDENTALLY FINDING THIS REPOSITORY

**This project is a not-at-all-production-ready-dark-ages-hardcore-alpha. Please refrain from filing bug reports of complaints until this notice disappears.** 

Compatible with Python 3.8+

# Purpose

One way synchronisation from Todoist to Habitica.

Why? Because if you want to be productive, you probably should not use two track tasks in two places. Habitica is great for tracking habits, Todoist for tracking TODOs. Now you can use the best of both.

## How it works

Tasks are not added immediately. Only when you finish a task in Todoist, new task will be created in Habitica, finished and immediately deleted. So you won't see any Todoist tasks in Habitica but still get the rewards.

# Features

* Scores points in Habitica when Todoist task is finished.
* Works for repeated tasks in Todoist, as long as the date string contains `every`.
* To form a positive habit of prioritizing long term tasks, difficulty in Habitica is assigned by priority in Todoist. The priority is them assumed to match [Eisenhower Matrix](https://en.wikipedia.org/wiki/Time_management#The_Eisenhower_Method) quadrants.

| Todoist Priority | Habitica Difficulty |    Eisenhower Quadrant    |
|:----------------:|:-------------------:|:-------------------------:|
|        p1        |        Medium       |     Important, urgent     |
|        p2        |         Hard        | Important, not urgent     |
|        p3        |         Easy        |   Not important, urgent   |
|        p4        |       Trivial       | Not important, not urgent |

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
3. Make sure Python 3.8+ is installed:
   ```shell script
   python --version
   ```
   The output should look something like:
   ```text
   Python 3.8.6
   ```
   * If it shows `2.7.x` instead, try `python3` instead and use it in the rest of the guide.
   * If it shows `3.7.x` or lower, use [`pyenv`](https://github.com/pyenv/pyenv#installation) to install a higher version of Python on your system.
4. Make sure `poetry` is installed:
   ```shell script
   poetry --version
   ```
   The output should look something like:
   ```
   Poetry version 1.1.5
   ```
   If it is not installed, install it with:
   ```shell script
   pip install poetry
   ```
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
   poetry install --no-dev
   ```
9. Run the app:
    ```shell script
    poetry run python src/main.py
    ```

## As a docker container

TODO

## As a service

TODO

# Planned work

* Synchronise overdue task to cause damage in habitica
* Parse difficulty from string (similar to p0-p4 in Todoist)
* Use @ Todoist labels for difficulty