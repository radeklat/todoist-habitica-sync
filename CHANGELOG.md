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

## [3.2.0] - 2024-03-14

### Features

- Improve logging of authentication errors.

## [3.1.0] - 2024-03-06

### Features

- Log path to sync cache file on app startup.

### Fixes

- Path to sync cache in `docker-compose.yml`
- Improved iteration over Habitica states (less waiting).

## [3.0.2] - 2024-02-17

### Fixes

- Incorrect awarding of points for rescheduled recurring tasks. There is no difference between rescheduled and completed once other than completed being scheduled to the future. Therefore, only recurring tasks rescheduled to the future will be awarded points. This can still be a false positive, if a recurring task is scheduled to the future manually. 

## [3.0.1] - 2023-11-13

### Fixes

- Incorrect transition.

## [3.0.0] - 2023-11-13

### Breaking changes

- Rewritten the state logic to the state design pattern for easier understanding and extensibility. This has resulted in changing how the data is stored in the sync cache. Please [reset the cache](README.md#resetting-sync-cache) before upgrading to this version.

### Fixes

- Tasks deleted in habitica being stuck in a loop and logging errors.
- Recurring tasks completed forever in Todoist being stuck in a loop.

## [2.1.10] - 2023-11-01

### Fixes

- Upgrade to Python 3.12.0.
- Upgrade to `pydantic` 2.x.
- Switch to `settings-doc` in `pre-commit` config.

## [2.1.9] - 2023-10-31

### Fixes

- Move verbose logging of unexpected HTTP errors.

## [2.1.8] - 2023-09-14

### Fixes

- Dependencies update.
- Better handling of invalid Todoist API token.

## [2.1.7] - 2022-12-30

### Fixes

- Downgrade `cryptography` to allow build for armv7.

## [2.1.6] - 2022-12-29

### Fixes

- Dependencies update

## [2.1.5] - 2022-12-09

### Fixes

- Dependencies update

## [2.1.4] - 2022-12-03

### Fixes

- Recurring task stuck in a loop when permanently finished.

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

### Breaking changes

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

[Unreleased]: https://github.com/radeklat/todoist-habitica-sync/compare/3.2.0...HEAD
[3.2.0]: https://github.com/radeklat/todoist-habitica-sync/compare/3.1.0...3.2.0
[3.1.0]: https://github.com/radeklat/todoist-habitica-sync/compare/3.0.2...3.1.0
[3.0.2]: https://github.com/radeklat/todoist-habitica-sync/compare/3.0.1...3.0.2
[3.0.1]: https://github.com/radeklat/todoist-habitica-sync/compare/3.0.0...3.0.1
[3.0.0]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.10...3.0.0
[2.1.10]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.9...2.1.10
[2.1.9]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.8...2.1.9
[2.1.8]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.7...2.1.8
[2.1.7]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.6...2.1.7
[2.1.6]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.5...2.1.6
[2.1.5]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.4...2.1.5
[2.1.4]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.3...2.1.4
[2.1.3]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.2...2.1.3
[2.1.2]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.1...2.1.2
[2.1.1]: https://github.com/radeklat/todoist-habitica-sync/compare/2.1.0...2.1.1
[2.1.0]: https://github.com/radeklat/todoist-habitica-sync/compare/2.0.0...2.1.0
[2.0.0]: https://github.com/radeklat/todoist-habitica-sync/compare/1.2.0...2.0.0
[1.2.0]: https://github.com/radeklat/todoist-habitica-sync/compare/1.1.3...1.2.0
[1.1.3]: https://github.com/radeklat/todoist-habitica-sync/compare/1.1.2...1.1.3
[1.1.2]: https://github.com/radeklat/todoist-habitica-sync/compare/1.1.1...1.1.2
[1.1.1]: https://github.com/radeklat/todoist-habitica-sync/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/radeklat/todoist-habitica-sync/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/radeklat/todoist-habitica-sync/compare/initial...1.0.0
