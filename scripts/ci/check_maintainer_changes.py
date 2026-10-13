# SPDX-License-Identifier: Apache-2.0
# Copyright The Zephyr Project Contributors
#
# Adapted from Zephyr's scripts/ci/check_maintainer_changes.py for
# cosim-gpu.

import argparse
import os
import sys

import yaml
from github import Auth, Github
from github.GithubException import GithubException

# Repository roles that are allowed to review pull requests
REVIEW_ROLES = ("admin", "maintain", "write", "triage")


def load_areas(filename: str):
    with open(filename) as f:
        doc = yaml.safe_load(f)
    return {
        k: v for k, v in doc.items()
        if isinstance(v, dict) and ("files" in v or "files-regex" in v)
    }


def set_or_empty(d, key):
    return set(d.get(key, []) or [])


def check_github_access(usernames, repo):
    # Returns the users without at least triage access to 'repo'
    missing_access = set()
    for username in usernames:
        try:
            role = repo.get_collaborator_role_name(username)
            if role not in REVIEW_ROLES:
                missing_access.add(username)
        except GithubException:
            missing_access.add(username)
    return missing_access


def print_list_change(changes, title, old_entry, new_entry, key):
    added = set_or_empty(new_entry, key) - set_or_empty(old_entry, key)
    removed = set_or_empty(old_entry, key) - set_or_empty(new_entry, key)
    if added:
        changes.append(f"  {title} added: {', '.join(sorted(added))}")
    if removed:
        changes.append(f"  {title} removed: {', '.join(sorted(removed))}")
    return added


def compare_areas(old, new):
    # Prints the differences between two sets of areas and returns the
    # maintainers and collaborators that were added
    old_areas = set(old.keys())
    new_areas = set(new.keys())

    added_areas = new_areas - old_areas
    removed_areas = old_areas - new_areas
    common_areas = old_areas & new_areas

    all_added_maintainers = set()
    all_added_collaborators = set()

    print("=== Areas Added ===")
    for area in sorted(added_areas):
        print(f"+ {area}")
        entry = new[area]
        all_added_maintainers.update(set_or_empty(entry, "maintainers"))
        all_added_collaborators.update(set_or_empty(entry, "collaborators"))

    print("\n=== Areas Removed ===")
    for area in sorted(removed_areas):
        print(f"- {area}")

    print("\n=== Area Changes ===")
    for area in sorted(common_areas):
        changes = []
        old_entry = old[area]
        new_entry = new[area]

        all_added_maintainers.update(print_list_change(
            changes, "Maintainers", old_entry, new_entry, "maintainers"))
        all_added_collaborators.update(print_list_change(
            changes, "Collaborators", old_entry, new_entry,
            "collaborators"))

        old_status = old_entry.get("status")
        new_status = new_entry.get("status")
        if old_status != new_status:
            changes.append(f"  Status changed: {old_status} -> {new_status}")

        print_list_change(changes, "Labels", old_entry, new_entry, "labels")
        print_list_change(changes, "Files", old_entry, new_entry, "files")
        print_list_change(changes, "files-regex", old_entry, new_entry,
                          "files-regex")

        if changes:
            print(f"* {area}")
            for c in changes:
                print(c)

    print("\n=== Summary ===")
    print(f"Total areas added: {len(added_areas)}")
    print(f"Total maintainers added: {len(all_added_maintainers)}")
    if all_added_maintainers:
        print("  Added maintainers: " +
              ", ".join(sorted(all_added_maintainers)))
    print(f"Total collaborators added: {len(all_added_collaborators)}")
    if all_added_collaborators:
        print("  Added collaborators: " +
              ", ".join(sorted(all_added_collaborators)))

    return all_added_maintainers, all_added_collaborators


def find_line_for_users(yaml_file, users):
    # Returns a dict of user -> last line number in yaml_file that names
    # the user
    user_lines = {}
    with open(yaml_file) as f:
        for idx, line in enumerate(f, 1):
            for user in users:
                if line.strip() == f"- {user}":
                    user_lines[user] = idx
    return user_lines


def main():
    parser = argparse.ArgumentParser(
        description="Compare two MAINTAINERS.yml files, show the changes "
                    "in areas, maintainers and collaborators, and check that "
                    "added people have at least triage access.",
        allow_abbrev=False,
    )
    parser.add_argument("old", help="Old MAINTAINERS.yml file")
    parser.add_argument("new", help="New MAINTAINERS.yml file")
    parser.add_argument("--repo", required=True,
                        help="GitHub repository in org/repo format")
    parser.add_argument("--annotate-file", default=None,
                        help="Repository path reported in GitHub Actions "
                             "annotations (default: NEW)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN must be set for the access check.")

    added_maint, added_collab = compare_areas(load_areas(args.old),
                                              load_areas(args.new))

    print("\n=== GitHub Access Check ===")
    repo = Github(auth=Auth.Token(token)).get_repo(args.repo)
    missing_maint = check_github_access(added_maint, repo)
    missing_collab = check_github_access(added_collab, repo)
    if missing_maint:
        print("Maintainers without at least triage access:")
        for u in sorted(missing_maint):
            print(f"  - {u}")
    if missing_collab:
        print("Collaborators without at least triage access:")
        for u in sorted(missing_collab):
            print(f"  - {u}")
    if not missing_maint and not missing_collab:
        print("All added maintainers and collaborators have required "
              "access.")
        return

    print("Some added maintainers or collaborators do not have sufficient "
          "access.")

    annotate_file = args.annotate_file or args.new
    all_missing_users = missing_maint | missing_collab
    user_lines = find_line_for_users(args.new, all_missing_users)
    for user, line in sorted(user_lines.items()):
        print(f"::error file={annotate_file},line={line},"
              f"title=User lacks access::{user} does not have needed "
              f"access level to {args.repo}")
    for user in sorted(all_missing_users - set(user_lines)):
        print(f"::error title=User lacks access::{user} does not have "
              f"needed access level to {args.repo}")

    sys.exit(1)


if __name__ == "__main__":
    main()
