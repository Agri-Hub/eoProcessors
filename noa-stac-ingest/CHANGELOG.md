# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
## [0.18.0] - 2025-08-01
- Service can now ingest from/to s3 bucket paths and store them to s3 STAC catalogs (#143)

## [0.17.0] - 2025-05-23
### Added
- Can now ingest Change Detection Mapping (ChDM) product made by NOA-Beyond (#130)
- ChDM and Cloud Free Median (CFM) products can be ingested from the service

## [0.16.0] - 2025-05-05
### Added
- Can now ingest Sentinel 2 monthly medians made by NOA-Beyond (#126)

## [0.15.1] - 2025-03-12
### Fixed
- Bug on Sentinel 1 ingestion (#118)

## [0.15.0] - 2025-02-18
### Added
- More and corrected log messages (#42)
### Changed
- Do not launch service if no kafka topics are found. Do not create them instead (#42)

## [0.14.1] - 2025-02-12
### Fixed
- Fixed Dockerfile paths and a config access bug (#111)

## [0.3.0] - 2024-12-18
### Fixed
- Fixed access kafka json and added some logs (#102)

## [0.2.5] - 2024-12-13
### Fixed
- Fixed access to STAC properties (#92)

### Added
- pgSTAC credentials to docker compose (#92)

## [0.2.4] - 2024-12-11
### Fixed
- External bug: read proper key (#90)

## [0.2.3] - 2024-12-04
### Fixed
- UUID to str bug (#84)

## [0.2.2] - 2024-12-04
### Fixed
- Pass kafka topics as a list, not as a nested list (#82)

## [0.2.1] - 2024-12-03
### Added
- Added NOA Product Id in Item properties (#80)

## [0.2.0] - 2024-12-02
### Changed
- Working version. Also wrapped for kafka interfacing (#53)

## [0.1.0] - 2024-11-08
### Added
- Initial functionality - Alpha version (#53)


### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security