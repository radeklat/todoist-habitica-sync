[![Master Build Status](https://travis-ci.org/radeklat/todoist-habitica-points-sync.svg?branch=master)](https://travis-ci.org/radeklat/todoist-habitica-points-sync)
[![Develop Build Status](https://travis-ci.org/radeklat/todoist-habitica-points-sync.svg?branch=develop)](https://travis-ci.org/radeklat/todoist-habitica-points-sync)

Compatible with Python 3.7+

# Purpose

One way synchronisation from Todoist to Habitica.

Tasks are not added immediately. Only when you finish a task in Todoist, new task will be created in Habitica, finished and immediately deleted.

# Features

* Scores points in Habitica when Todoist task is finished
* Works for repeated tasks in Todoist, as long as the date string contains `every`

# Installation

## As a script

1. Clone this repository
1. Create a copy of _.env.template_ into _.env_ and fill your details.
1. Run:

        $(cat .env | xargs) python src/main.py

## As a docker container

    docker run --rm --env-file .env --name toist-habitica-points-sync radeklat/todoist-habitica-points-sync
