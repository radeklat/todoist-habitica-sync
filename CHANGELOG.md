# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).
Types of changes are:

* **Added** for new features.
* **Changed** for changes in existing functionality.
* **Deprecated** for soon-to-be removed features.
* **Removed** for now removed features.
* **Fixed** for any bug fixes.
* **Security** in case of vulnerabilities.

## [Unreleased]

## [1.1.0] - 2021-03-20

### Added

* Automatically create nested path for sync cache.
* Guide for running from a docker image.
* Guide for running via docker-compose and a compose file.

### Fixed

* Virtualenv creation in docker image.

### Changed

* Move sync cache file into a folder to allow easier mounting in docker images.

## [1.0.0] - 2019-10-06

* Initial release

[Unreleased]: https://github.com/radeklat/todoist-habitica-points-sync/compare/1.1.0...HEAD
[1.1.0]: https://github.com/radeklat/todoist-habitica-points-sync/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/radeklat/todoist-habitica-points-sync/compare/initial...1.0.0