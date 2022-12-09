import re
from collections import Counter
from pathlib import Path
from typing import List

import pytest


@pytest.fixture(scope="module")
def changelog() -> str:
    with open(Path(__file__).parent.parent.parent / "CHANGELOG.md", "r", encoding="utf8") as changelog:
        return changelog.read()


@pytest.fixture(scope="module")
def all_versions(changelog) -> List[str]:
    return re.findall(r"## \[([0-9]+\.[0-9]+\.[0-9]+)\]", changelog)


class TestChangelog:
    @staticmethod
    def should_contain_current_version(poetry, all_versions):
        assert all_versions[0] == poetry.version

    @staticmethod
    def should_contain_each_version_only_once(all_versions):
        cnt = Counter(all_versions)
        for version, count in cnt.most_common():
            if count > 1:
                raise AssertionError(f"Version '{version}' appears {count}x in the changelog.")
            break

    @staticmethod
    def should_use_latest_version_in_the_unreleased_section_link(poetry, changelog):
        regex = r"\[Unreleased\]: " + poetry.homepage + r"/compare/" + poetry.version + r"\.\.\.HEAD"
        links = re.findall(regex, changelog)
        assert len(links) == 1, f"Pattern '{regex}' must be present exactly once."

    @staticmethod
    def should_link_to_the_current_version(poetry, changelog):
        regex = r"\[" + poetry.version + r"\]: " + poetry.homepage + r"/compare/.*\.\.\." + poetry.version
        links = re.findall(regex, changelog)
        assert len(links) == 1, f"Pattern '{regex}' must be present exactly once."

    @staticmethod
    def should_contain_version_and_date_in_add_second_level_headings(changelog):
        headings = re.findall(r"\n## .*", changelog)
        assert headings, "The should be at least one second level heading"
        regex = r"\n## \[[0-9]+\.[0-9]+\.[0-9]+\] - [0-9]{4}-[0-9]{2}-[0-9]{2}"

        assert headings[0] == "\n## [Unreleased]", "First heading must be for unreleased changes"
        headings.pop(0)

        for heading in headings:
            match = re.match(regex, heading)
            assert match, f"Heading '{heading}' doesn't match the '## [<VERSION>] - <DATE>' pattern "

    @staticmethod
    def should_contain_change_type_in_third_level_headings(changelog):
        headings = set(re.findall(r"\n### (.*)", changelog))
        assert headings, "The should be at least one thrid level heading"
        assert headings <= {"Features", "Fixes", "Deprecated", "Breaking changes"}
