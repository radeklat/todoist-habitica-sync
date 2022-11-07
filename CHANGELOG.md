# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).
Types of changes are:

- **Breaking changes** for breaking changes.
- **Features** for new features or changes in existing functionality.
- **Fixes** for any bug fixes.
- **Deprecated** for soon-to-be removed features.

## [Unreleased]

## [2.1.3] - 2022-11-03

### Fixes

- Drop deprecated [`todoist-python`](https://github.com/Doist/todoist-python) library to communicate with the [v8 Sync API](https://developer.todoist.com/sync/v8, which has been also terminated. This has been replaced with [a custom implementation](src/todoist_api.py) of the [v9 Sync API](https://developer.todoist.com/sync/v9).

## [2.1.2] - 2022-07-06

### Fixes

- Dependencies update, including an upgrade from Python 3.10.4 to 3.10.5

## [2.1.1] - 2022-03-06

### Fixes

- Dependencies update, including an upgrade from Python 3.10.2 to 3.10.4

## [2.1.0] - 2022-03-06

### Features

- New optional configuration option `todoist_user_id`. When set, tasks completed in project will score points only if they were assigned to you or no one, not when assigned to someone else. Who completed the task is not taken into account.

### Fixes

- Delay between each Habitica API action has been increased from 0.5s to 30s, as mandated by the official documentation.
- `x-client` HTTP header is being sent to notify the API of the author of the tool, as mandated by the official documentation.

## [2.0.0] - 2022-01-30

## Breaking changes

- Recurring Todoist tasks are counted on every completion, not just the fist one. Please [reset the cache](README.md#resetting-sync-cache) as this fix doesn't work for already cached tasks.

## [1.2.0] - 2022-01-30

### Features

- Upgrade to Python 3.10

### Fixes

- Update library dependencies.

## [1.1.3] - 2022-01-25

### Fixes

- Update library dependencies.

## [1.1.2] - 2021-11-29

### Fixes

- Update library dependencies.

## [1.1.1] - 2021-10-31

### Fixes

- Change `Dockerfile` to use Python version from `pyproject.toml`.
- Updates build process to build docker images for multiple architectures.
- Load environment variables from a `.env` file in the compose file.

## [1.1.0] - 2021-03-20

### Features

- Automatically create nested path for sync cache.
- Guide for running from a docker image.
- Guide for running via docker-compose and a compose file.

### Fixes

- Virtualenv creation in docker image.
- Move sync cache file into a folder to allow easier mounting in docker images.

## [1.0.0] - 2019-10-06

### Features

- Initial release

[unreleased]: https://github.com/radeklat/todoist-habitica-points-sync/compare/2.1.2...HEAD
[2.1.2]: https://github.com/radeklat/todoist-habitica-points-sync/compare/2.1.1...2.1.2
[2.1.1]: https://github.com/radeklat/todoist-habitica-points-sync/compare/2.1.0...2.1.1
[2.1.0]: https://github.com/radeklat/todoist-habitica-points-sync/compare/2.0.0...2.1.0
[2.0.0]: https://github.com/radeklat/todoist-habitica-points-sync/compare/1.2.0...2.0.0
[1.2.0]: https://github.com/radeklat/todoist-habitica-points-sync/compare/1.1.3...1.2.0
[1.1.3]: https://github.com/radeklat/todoist-habitica-points-sync/compare/1.1.2...1.1.3
[1.1.2]: https://github.com/radeklat/todoist-habitica-points-sync/compare/1.1.1...1.1.2
[1.1.1]: https://github.com/radeklat/todoist-habitica-points-sync/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/radeklat/todoist-habitica-points-sync/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/radeklat/todoist-habitica-points-sync/compare/initial...1.0.0
