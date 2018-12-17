[![Master Build Status](https://travis-ci.org/radeklat/todoist-habitica-points-sync.svg?branch=master)](https://travis-ci.org/radeklat/todoist-habitica-points-sync)
[![Develop Build Status](https://travis-ci.org/radeklat/todoist-habitica-points-sync.svg?branch=develop)](https://travis-ci.org/radeklat/todoist-habitica-points-sync)

# NOTE FOR PEOPLE ACCIDENTALLY FINDING THIS REPOSITORY

**This project is a not-at-all-production-ready-dark-ages-hardcore-alpha. Please refrain from filing bug reports of complaints until this notice disappears.** 

Compatible with Python 3.7+

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

1. Clone this repository
1. Create a copy of _.env.template_ into _.env_ and fill your details.
1. Run:

        $(cat .env | xargs) python src/main.py

## As a docker container

TODO

## As a service

TODO

# Planned work

* Synchronise overdue task to cause damage in habitica
* Parse difficulty from string (similar to p0-p4 in Todoist)
* Use @ Todoist labels for difficulty