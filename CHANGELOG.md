# Changelog
All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- First stable version.
- API documentation.
- A command-line interface for easy automated fetching of data.
- A stable relational data model, to make further analysis or data processing
  independent of the details of data ingest.
- Support for fetching follow-graph edges, tweets, lists and user info.
- Support for a variety of database backends via sqlalchemy.
- Type-2 SCD for tracking the follow graph and list membership over time.
- Many sanity checks in the data model to ensure correctness of loaded data.
- Loaded data is extensively normalized: mentions, replies, retweets, and
  entities like hashtags are extracted into first-class objects for more
  convenient and accessible analysis.
- Users can be tagged into arbitrary groups for greater convenience in analysis
  or data collection.
- Support for both app-only and user authentication to the Twitter API.
