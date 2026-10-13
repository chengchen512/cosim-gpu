# Copyright (c) 2022 Intel Corp.
# SPDX-License-Identifier: Apache-2.0
#
# Adapted from Zephyr's scripts/ci/set_assignees.py for cosim-gpu.

import argparse
import datetime
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import yaml
from github import Auth, Github, GithubException
from github.GithubException import UnknownObjectException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from get_maintainer import Maintainers  # noqa: E402

_DESCRIPTION = """\
Assign maintainers, request reviewers and add labels on GitHub pull
requests and issues, based on the areas in MAINTAINERS.yml.
"""

# Areas whose maintainers are assigned only when no other area is affected
META_AREAS = ["Documentation"]

# GitHub limits the number of requested reviewers on a pull request
MAX_REVIEWERS = 15

# Pull requests that change more files than this are left alone
MAX_FILES = 500


def log(s):
    if args.verbose > 0:
        print(s, file=sys.stdout)


def parse_args():
    global args
    parser = argparse.ArgumentParser(
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )

    parser.add_argument(
        "-M",
        "--maintainer-file",
        required=False,
        default="MAINTAINERS.yml",
        help="Maintainer file to be used.",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-P",
        "--pull_request",
        required=False,
        default=None,
        type=int,
        help="Operate on one pull-request only.",
    )
    group.add_argument(
        "-I", "--issue", required=False, default=None, type=int,
        help="Operate on one issue only."
    )
    group.add_argument(
        "-s", "--since", required=False,
        help="Process pull-requests since date."
    )

    parser.add_argument(
        "-y", "--dry-run", action="store_true", default=False,
        help="Dry run only."
    )

    parser.add_argument(
        "-o", "--org", default="gevico", help="Github organisation"
    )

    parser.add_argument(
        "-r", "--repo", default="cosim-gpu", help="Github repository"
    )

    parser.add_argument(
        "--updated-maintainer-file",
        default=None,
        help="MAINTAINERS.yml from the pull request, compared against the "
             "maintainer file to find the changed areas",
    )

    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Verbose Output"
    )

    args = parser.parse_args()


def load_areas(filename: str):
    with open(filename) as f:
        doc = yaml.safe_load(f)
    return {
        k: v for k, v in doc.items()
        if isinstance(v, dict) and ("files" in v or "files-regex" in v)
    }


def set_or_empty(d, key):
    return set(d.get(key, []) or [])


def compare_areas(old, new):
    # Returns the names of the areas that were added, removed or changed
    old_areas = set(old.keys())
    new_areas = set(new.keys())

    changed_areas = set()
    added_areas = new_areas - old_areas
    removed_areas = old_areas - new_areas
    common_areas = old_areas & new_areas

    for area in sorted(common_areas):
        for key in ("maintainers", "collaborators", "labels", "files",
                    "files-regex"):
            if set_or_empty(old[area], key) != set_or_empty(new[area], key):
                changed_areas.add(area)
        if old[area].get("status") != new[area].get("status"):
            changed_areas.add(area)

    for area in sorted(added_areas):
        log(f"area added: {area}")
    for area in sorted(removed_areas):
        log(f"area removed: {area}")
    for area in sorted(changed_areas):
        log(f"area changed: {area}")

    return added_areas | removed_areas | changed_areas


def process_pr(gh, maintainer_file, number):
    gh_repo = gh.get_repo(f"{args.org}/{args.repo}")
    pr = gh_repo.get_pull(number)

    log(f"working on https://github.com/{args.org}/{args.repo}/pull/"
        f"{pr.number} : {pr.title}")

    labels = set()
    area_counter = defaultdict(int)
    found_maintainers = defaultdict(int)

    num_files = 0
    fn = list(pr.get_files())

    if len(fn) > MAX_FILES:
        log(f"Too many files changed ({len(fn)}), skipping....")
        return

    collab_per_path = set()
    additional_reviews = set()
    for changed_file in fn:
        num_files += 1
        log(f"file: {changed_file.filename}")

        areas = maintainer_file.path2areas(changed_file.filename)
        if changed_file.filename == "MAINTAINERS.yml" and \
           args.updated_maintainer_file:
            old_areas = load_areas(args.maintainer_file)
            new_areas = load_areas(args.updated_maintainer_file)
            for _area in compare_areas(old_areas, new_areas):
                area_match = maintainer_file.name2areas(_area)
                if area_match:
                    additional_reviews.update(area_match[0].maintainers)
            log(f"MAINTAINERS.yml changed, adding reviewers: "
                f"{additional_reviews}")

        log(f"  areas: {areas}")

        if not areas:
            continue

        for area in areas:
            c = 0 if area.name in META_AREAS else 1
            area_counter[area] += c
            labels.update(area.labels)
            for area_maintainer in area.maintainers:
                found_maintainers[area_maintainer] += c
            collab_per_path.update(
                area.get_collaborators_for_path(changed_file.filename))

    area_counter = dict(sorted(area_counter.items(),
                               key=lambda item: item[1], reverse=True))
    log(f"Area matches: {area_counter}")
    log(f"labels: {labels}")

    # Create a list of collaborators ordered by the area match
    collab = list()
    for area in area_counter:
        collab += maintainer_file.areas[area.name].maintainers
        collab += maintainer_file.areas[area.name].collaborators
    collab += sorted(collab_per_path)

    collab = list(dict.fromkeys(collab))
    # Add more reviewers based on maintainer file changes
    collab += sorted(additional_reviews - set(collab))
    log(f"collab: {collab}")

    _all_maintainers = dict(sorted(found_maintainers.items(),
                                   key=lambda item: item[1], reverse=True))

    log(f"Submitted by: {pr.user.login}")
    log(f"candidate maintainers: {_all_maintainers}")

    assignees = None

    # Start with the area with the most files changed and pick its
    # maintainers, skipping the pull request author.
    for area, count in area_counter.items():
        # If only a meta area is affected, assign its maintainers
        if area.name in META_AREAS and len(area_counter) == 1:
            assignees = area.maintainers
            break
        if count == 0 or len(area.maintainers) == 0:
            continue
        if pr.user.login in area.maintainers:
            if len(area.maintainers) > 1:
                assignees = area.maintainers.copy()
                assignees.remove(pr.user.login)
                break
            continue
        assignees = area.maintainers
        break

    if assignees:
        prop = (found_maintainers[assignees[0]] / num_files) * 100
        log(f"Picked assignees: {assignees} ({prop:.2f}% ownership)")
    elif len(_all_maintainers) > 0:
        # If maintainers were found but none could be picked based on the
        # area, pick the one with the most changes
        assignees = [next(iter(_all_maintainers))]

    if labels:
        for label in sorted(labels):
            log(f"adding label {label}...")
            if not args.dry_run:
                pr.add_to_labels(label)

    if collab:
        reviewers = []
        existing_reviewers = set()

        for review in pr.get_reviews():
            existing_reviewers.add(review.user)

        users, _ = pr.get_review_requests()
        existing_reviewers |= set(users)

        # Do not add reviewers again who removed themselves from the list
        self_removal = []
        for event in pr.get_issue_events():
            if event.event == "review_request_removed" and \
               event.actor == event.requested_reviewer:
                self_removal.append(event.actor)

        for collaborator in collab:
            try:
                gh_user = gh.get_user(collaborator)
                if pr.user == gh_user or gh_user in existing_reviewers:
                    continue
                if not gh_repo.has_in_collaborators(gh_user):
                    log(f"Skip '{collaborator}': not in collaborators")
                    continue
                if gh_user in self_removal:
                    log(f"Skip '{collaborator}': self removed")
                    continue
                reviewers.append(collaborator)
            except UnknownObjectException as e:
                log(f"Can't get user '{collaborator}', account does not "
                    f"exist anymore? ({e})")

        reviewers = reviewers[:max(0, MAX_REVIEWERS -
                                   len(existing_reviewers))]

        if reviewers:
            try:
                log(f"adding reviewers {reviewers}...")
                if not args.dry_run:
                    pr.create_review_request(reviewers=reviewers)
            except GithubException as e:
                log(f"can't add reviewers: {e}")
        else:
            log("no reviewers to add")

    if assignees and (not pr.assignee or args.dry_run):
        ms = []
        try:
            for assignee in assignees:
                ms.append(gh.get_user(assignee))
        except GithubException:
            log("Error: Unknown user")

        for mm in ms:
            log(f"Adding assignee {mm.login}...")
            if not args.dry_run:
                pr.add_to_assignees(mm)
    else:
        log("not setting assignee")

    time.sleep(1)


def process_issue(gh, maintainer_file, number):
    gh_repo = gh.get_repo(f"{args.org}/{args.repo}")
    issue = gh_repo.get_issue(number)

    log(f"Working on {issue.url}: {issue.title}")

    if issue.assignees:
        print(f"Already assigned {issue.assignees}, bailing out")
        return

    label_to_maintainer = defaultdict(set)
    for _, area in maintainer_file.areas.items():
        if not area.labels:
            continue

        labels = tuple(sorted(label.lower() for label in area.labels))
        for maintainer in area.maintainers:
            label_to_maintainer[labels].add(maintainer)

    # Add extra entries for areas with multiple labels so they match with
    # just one label if it's specific enough.
    for areas, maintainers in dict(label_to_maintainer).items():
        for area in areas:
            if tuple([area]) not in label_to_maintainer:
                label_to_maintainer[tuple([area])] = maintainers

    issue_labels = set()
    for label in issue.labels:
        label_name = label.name.lower()
        if tuple([label_name]) not in label_to_maintainer:
            print(f"Ignoring label: {label}")
            continue
        issue_labels.add(label_name)
    issue_labels = tuple(sorted(issue_labels))

    print(f"Using labels: {issue_labels}")

    if issue_labels not in label_to_maintainer:
        print("no match for the label set, not assigning")
        return

    for maintainer in label_to_maintainer[issue_labels]:
        log(f"Adding {maintainer} to {issue.html_url}")
        if not args.dry_run:
            issue.add_to_assignees(maintainer)


def main():
    parse_args()

    token = os.environ.get("GITHUB_TOKEN", None)
    if not token:
        sys.exit("Github token not set in environment, please set the "
                 "GITHUB_TOKEN environment variable and retry.")

    gh = Github(auth=Auth.Token(token))
    maintainer_file = Maintainers(args.maintainer_file)

    if args.pull_request:
        process_pr(gh, maintainer_file, args.pull_request)
    elif args.issue:
        process_issue(gh, maintainer_file, args.issue)
    else:
        if args.since:
            since = args.since
        else:
            today = datetime.date.today()
            since = today - datetime.timedelta(days=1)

        common_prs = (
            f"repo:{args.org}/{args.repo} is:open is:pr base:main "
            f"-is:draft no:assignee created:>{since}"
        )
        for issue in gh.search_issues(query=common_prs):
            process_pr(gh, maintainer_file, issue.number)


if __name__ == "__main__":
    main()
