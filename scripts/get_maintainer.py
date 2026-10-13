# Copyright (c) 2019 Nordic Semiconductor ASA
# SPDX-License-Identifier: Apache-2.0
#
# Adapted from Zephyr's scripts/get_maintainer.py for cosim-gpu.

import argparse
import operator
import os
import pathlib
import re
import shlex
import subprocess
import sys

from tabulate import tabulate
from yaml import YAMLError, load

try:
    # Use the speedier C LibYAML parser if available
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

_DESCRIPTION = """\
Lists maintainers for files or commits. Similar in function to
scripts/get_maintainer.pl from Linux, but geared towards GitHub. The mapping
is in MAINTAINERS.yml, and the comment at the top of that file documents the
file format.

See the help texts for the subcommands for more information, e.g.

    python3 scripts/get_maintainer.py path --help

This file doubles as a Python library: identifiers not prefixed with '_' are
part of the library API.
"""

AREA_KEYS = {"status", "maintainers", "collaborators", "inform", "files",
             "files-exclude", "files-regex", "files-regex-exclude",
             "labels", "description", "file-groups"}

AREA_STATUSES = {"maintained", "odd fixes", "unmaintained", "obsolete"}

FILE_GROUP_KEYS = {"name", "description", "collaborators", "files",
                   "files-exclude", "files-regex", "files-regex-exclude"}


def _main():
    # Entry point when run as an executable

    args = _parse_args()
    try:
        args.cmd_fn(Maintainers(args.maintainers), args)
    except (MaintainersError, GitError) as e:
        _serr(e)


def _parse_args():
    # Parses arguments when run as an executable

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=_DESCRIPTION, allow_abbrev=False)

    parser.add_argument(
        "-m", "--maintainers",
        metavar="MAINTAINERS_FILE",
        help="Maintainers file to load. If not specified, MAINTAINERS.yml "
             "in the top-level repository directory is used, and must "
             "exist. Paths in the maintainers file will always be taken "
             "as relative to the top-level directory.")

    subparsers = parser.add_subparsers(
        help="Available commands (each has a separate --help text)")

    id_parser = subparsers.add_parser(
        "path",
        help="List area(s) for paths")
    id_parser.add_argument(
        "paths",
        metavar="PATH",
        nargs="*",
        help="Path to list areas for")
    id_parser.set_defaults(cmd_fn=Maintainers._path_cmd)

    commits_parser = subparsers.add_parser(
        "commits",
        help="List area(s) for commit range")
    commits_parser.add_argument(
        "commits",
        metavar="COMMIT_RANGE",
        nargs="*",
        help="Commit range to list areas for (default: HEAD~..)")
    commits_parser.set_defaults(cmd_fn=Maintainers._commits_cmd)

    list_parser = subparsers.add_parser(
        "list",
        help="List files in areas")
    list_parser.add_argument(
        "area",
        metavar="AREA",
        nargs="?",
        help="Name of area to list files in. If not specified, all "
             "non-orphaned files are listed (all files that appear in "
             "some area).")
    list_parser.set_defaults(cmd_fn=Maintainers._list_cmd)

    areas_parser = subparsers.add_parser(
        "areas",
        help="List areas and maintainers")
    areas_parser.add_argument(
        "maintainer",
        metavar="MAINTAINER",
        nargs="?",
        help="List all areas maintained by maintainer.")
    areas_parser.add_argument(
        "--without-maintainers",
        action="store_true",
        help="Exclude areas that have maintainers")
    areas_parser.add_argument(
        "--without-collaborators",
        action="store_true",
        help="Exclude areas that have collaborators")
    areas_parser.set_defaults(cmd_fn=Maintainers._areas_cmd)

    area_parser = subparsers.add_parser(
        "area",
        help="List area(s) by name")
    area_parser.add_argument(
        "name",
        metavar="AREA",
        nargs="?",
        help="List all areas with the given name.")
    area_parser.set_defaults(cmd_fn=Maintainers._area_cmd)

    orphaned_parser = subparsers.add_parser(
        "orphaned",
        help="List orphaned files (files that do not appear in any area)")
    orphaned_parser.add_argument(
        "path",
        metavar="PATH",
        nargs="?",
        help="Limit to files under PATH")
    orphaned_parser.set_defaults(cmd_fn=Maintainers._orphaned_cmd)

    count_parser = subparsers.add_parser(
        "count",
        help="Count areas, unique maintainers, and / or unique "
             "collaborators")
    count_parser.add_argument(
        "-a",
        "--count-areas",
        action="store_true",
        help="Count the number of areas")
    count_parser.add_argument(
        "-c",
        "--count-collaborators",
        action="store_true",
        help="Count the number of unique collaborators")
    count_parser.add_argument(
        "-n",
        "--count-maintainers",
        action="store_true",
        help="Count the number of unique maintainers")
    count_parser.add_argument(
        "-o",
        "--count-unmaintained",
        action="store_true",
        help="Count the number of unmaintained areas")
    count_parser.set_defaults(cmd_fn=Maintainers._count_cmd)

    args = parser.parse_args()
    if not hasattr(args, "cmd_fn"):
        # Called without a subcommand
        sys.exit(parser.format_usage().rstrip())

    return args


class Maintainers:
    """
    Represents the contents of a maintainers YAML file.

    These attributes are available:

    areas:
        A dictionary that maps area names to Area instances, for all areas
        defined in the maintainers file

    filename:
        The path to the maintainers file
    """
    def __init__(self, filename=None):
        """
        Creates a Maintainers instance.

        filename (default: None):
            Path to the maintainers file to parse. If None, MAINTAINERS.yml
            in the top-level directory of the Git repository is used, and
            must exist.
        """
        if (filename is not None) and (pathlib.Path(filename).exists()):
            self.filename = pathlib.Path(filename)
            self._toplevel = self.filename.parent
        else:
            self._toplevel = pathlib.Path(
                _git("rev-parse", "--show-toplevel"))
            self.filename = self._toplevel / "MAINTAINERS.yml"

        self.areas = {}
        for area_name, area_dict in _load_maintainers(self.filename).items():
            area = Area()
            area.name = area_name
            area.status = area_dict.get("status")
            area.maintainers = area_dict.get("maintainers", [])
            area.collaborators = area_dict.get("collaborators", [])
            area.inform = area_dict.get("inform", [])
            area.labels = area_dict.get("labels", [])
            area.description = area_dict.get("description")

            area.file_groups = []
            for group_dict in area_dict.get("file-groups", []):
                file_group = FileGroup()
                file_group.name = group_dict.get("name", "Unnamed Group")
                file_group.description = group_dict.get("description")
                file_group.collaborators = \
                    group_dict.get("collaborators", [])

                file_group._match_fn = \
                    _get_match_fn(group_dict.get("files"),
                                  group_dict.get("files-regex"))

                file_group._exclude_match_fn = \
                    _get_match_fn(group_dict.get("files-exclude"),
                                  group_dict.get("files-regex-exclude"))

                # Store reference to parent area for inheritance
                file_group._parent_area = area

                area.file_groups.append(file_group)

            # area._match_fn(path) tests if the path matches files and/or
            # files-regex
            area._match_fn = \
                _get_match_fn(area_dict.get("files"),
                              area_dict.get("files-regex"))

            # Like area._match_fn(path), but for files-exclude and
            # files-regex-exclude
            area._exclude_match_fn = \
                _get_match_fn(area_dict.get("files-exclude"),
                              area_dict.get("files-regex-exclude"))

            self.areas[area_name] = area

    def name2areas(self, name):
        """
        Returns a list of Area instances for the areas that match 'name'.
        """
        return [area for area in self.areas.values() if area.name == name]

    def path2areas(self, path):
        """
        Returns a list of Area instances for the areas that contain 'path',
        taken as relative to the current directory
        """
        path = self._normalize_path(path)
        return [area for area in self.areas.values()
                if area._contains(path)]

    def path2area_info(self, path):
        """
        Returns a list of tuples (Area, FileGroup) for the areas that
        contain 'path'. FileGroup is None if the path matches the area's
        general files rather than a specific file group.
        """
        areas = self.path2areas(path)
        path = self._normalize_path(path)
        return [(area, area.get_file_group_for_path(path))
                for area in areas]

    def commits2areas(self, commits):
        """
        Returns a set() of Area instances for the areas that contain files
        that are modified by the commit range in 'commits'. 'commits' could
        be e.g. "HEAD~..", to inspect the tip commit
        """
        res = set()
        # Final '--' is to make sure 'commits' is interpreted as a commit
        # range rather than a path. That might give better error messages.
        for path in _git("diff", "--name-only", commits, "--").splitlines():
            res.update(self.path2areas(path))
        return res

    def _normalize_path(self, path):
        # Makes 'path' relative to the repository root and normalizes it.
        # Directory paths end in '/' so that foo/bar matches foo/bar/.
        # normpath() would remove a trailing '/', so it is added afterwards.
        # Submodule paths are gitlinks and stay without a trailing '/'.
        is_dir = os.path.isdir(path)

        path = os.path.normpath(os.path.join(
            os.path.relpath(os.getcwd(), self._toplevel),
            path))

        if is_dir and path not in self._submodule_paths():
            path += "/"

        return path

    def _submodule_paths(self):
        # Returns the set of gitlink (submodule) paths in the index
        if not hasattr(self, "_submodules"):
            entries = _git("-C", str(self._toplevel), "ls-files",
                           "--format=%(objectmode) %(path)").splitlines()
            self._submodules = {entry.split(" ", 1)[1] for entry in entries
                                if entry.startswith("160000 ")}
        return self._submodules

    def __repr__(self):
        return "<Maintainers for '{}'>".format(self.filename)

    #
    # Command-line subcommands
    #

    def _area_cmd(self, args):
        # 'area' subcommand implementation

        _print_areas(set(self.name2areas(args.name)))

    def _path_cmd(self, args):
        # 'path' subcommand implementation

        for path in args.paths:
            if not os.path.exists(path):
                _serr("'{}': no such file or directory".format(path))

        res = set()
        orphaned = []
        for path in args.paths:
            areas = self.path2areas(path)
            res.update(areas)
            if not areas:
                orphaned.append(path)

        _print_areas(res)
        if orphaned:
            if res:
                print()
            print("Orphaned paths (not in any area):\n" + "\n".join(orphaned))

    def _commits_cmd(self, args):
        # 'commits' subcommand implementation

        commits = args.commits or ("HEAD~..",)
        _print_areas({area for commit_range in commits
                      for area in self.commits2areas(commit_range)})

    def _areas_cmd(self, args):
        # 'areas' subcommand implementation

        def multiline(items):
            # Each item on its own line, empty string if none
            return "\n".join(items) if items else ""

        table = []
        for area in self.areas.values():
            if args.without_maintainers and area.maintainers:
                continue
            if args.without_collaborators and area.collaborators:
                continue
            if args.maintainer and args.maintainer not in area.maintainers:
                continue

            table.append([area.name,
                          multiline(area.maintainers),
                          multiline(area.collaborators)])

        if table:
            print(tabulate(
                table,
                headers=["Area", "Maintainers", "Collaborators"],
                tablefmt="grid",
                stralign="left",
                disable_numparse=True
            ))

    def _count_cmd(self, args):
        # 'count' subcommand implementation

        if not (args.count_areas or args.count_collaborators or
                args.count_maintainers or args.count_unmaintained):
            # If no specific count is provided, print them all
            args.count_areas = True
            args.count_collaborators = True
            args.count_maintainers = True
            args.count_unmaintained = True

        unmaintained = 0
        collaborators = set()
        maintainers = set()

        for area in self.areas.values():
            if area.status == "maintained":
                maintainers = maintainers.union(set(area.maintainers))
            elif area.status == "odd fixes":
                unmaintained += 1
            collaborators = collaborators.union(set(area.collaborators))

        if args.count_areas:
            print("{:14}\t{}".format("areas:", len(self.areas)))
        if args.count_maintainers:
            print("{:14}\t{}".format("maintainers:", len(maintainers)))
        if args.count_collaborators:
            print("{:14}\t{}".format("collaborators:", len(collaborators)))
        if args.count_unmaintained:
            print("{:14}\t{}".format("unmaintained:", unmaintained))

    def _list_cmd(self, args):
        # 'list' subcommand implementation

        if args.area is None:
            # List all files that appear in some area
            for path in _ls_files():
                for area in self.areas.values():
                    if area._contains(path):
                        print(path)
                        break
        else:
            # List all files that appear in the given area
            area = self.areas.get(args.area)
            if area is None:
                _serr("'{}': no such area defined in '{}'"
                      .format(args.area, self.filename))

            for path in _ls_files():
                if area._contains(path):
                    print(path)

    def _orphaned_cmd(self, args):
        # 'orphaned' subcommand implementation

        if args.path is not None and not os.path.exists(args.path):
            _serr("'{}': no such file or directory".format(args.path))

        for path in _ls_files(args.path):
            for area in self.areas.values():
                if area._contains(path):
                    break
            else:
                print(path)  # We get here if we never hit the 'break'


class FileGroup:
    """
    Represents a file group within an area in MAINTAINERS.yml.

    File groups inherit file patterns from their parent area. A file only
    matches a file group if it first matches the parent area's patterns,
    and then also matches the file group's own patterns.

    These attributes are available:

    name:
        The name of the file group, as specified in the 'name' key

    description:
        Text from 'description' key, or None if the group has no
        'description'

    collaborators:
        List of collaborators specific to this file group
    """
    def _parent_area_contains(self, path):
        # Returns True if the parent area contains 'path'
        return (self._parent_area._match_fn and
                self._parent_area._match_fn(path) and not
                (self._parent_area._exclude_match_fn and
                 self._parent_area._exclude_match_fn(path)))

    def _contains(self, path):
        # Returns True if the file group contains 'path', and False
        # otherwise. A file must match the parent area's patterns first,
        # then the file group's patterns.
        if not self._parent_area_contains(path):
            return False

        return self._match_fn and self._match_fn(path) and not \
            (self._exclude_match_fn and self._exclude_match_fn(path))

    def __repr__(self):
        return "<FileGroup {}>".format(self.name)


class Area:
    """
    Represents an entry for an area in MAINTAINERS.yml.

    These attributes are available:

    status:
        The status of the area, as a string. None if the area has no
        'status' key. See MAINTAINERS.yml.

    maintainers:
        List of maintainers. Empty if the area has no 'maintainers' key.

    collaborators:
        List of collaborators. Empty if the area has no 'collaborators'
        key.

    inform:
        List of people to inform on pull requests. Empty if the area has
        no 'inform' key.

    labels:
        List of GitHub labels for the area. Empty if the area has no
        'labels' key.

    description:
        Text from 'description' key, or None if the area has no
        'description' key

    file_groups:
        List of FileGroup instances for any file-groups defined in the
        area. Empty if the area has no 'file-groups' key.
    """
    def _contains(self, path):
        # Returns True if the area contains 'path', and False otherwise.
        # File groups take precedence over the area-level patterns.
        for file_group in self.file_groups:
            if file_group._contains(path):
                return True

        return self._match_fn and self._match_fn(path) and not \
            (self._exclude_match_fn and self._exclude_match_fn(path))

    def get_collaborators_for_path(self, path):
        """
        Returns a list of collaborators for a specific path.
        If the path matches a file group, returns the file group's
        collaborators. Otherwise, returns the area's general collaborators.
        """
        for file_group in self.file_groups:
            if file_group._contains(path):
                return file_group.collaborators

        return self.collaborators

    def get_file_group_for_path(self, path):
        """
        Returns the FileGroup instance that contains the given path,
        or None if the path doesn't match any file group.
        """
        for file_group in self.file_groups:
            if file_group._contains(path):
                return file_group
        return None

    def __repr__(self):
        return "<Area {}>".format(self.name)


def _print_areas(areas):
    first = True
    for area in sorted(areas, key=operator.attrgetter("name")):
        if not first:
            print()
        first = False

        print("""\
{}
\tstatus: {}
\tmaintainers: {}
\tcollaborators: {}
\tinform: {}
\tlabels: {}
\tdescription: {}""".format(area.name,
                            area.status,
                            ", ".join(area.maintainers),
                            ", ".join(area.collaborators),
                            ", ".join(area.inform),
                            ", ".join(area.labels),
                            area.description or ""))

        if area.file_groups:
            print("\tfile-groups:")
            for file_group in area.file_groups:
                print("\t\t{}: {}".format(
                    file_group.name,
                    ", ".join(file_group.collaborators)
                    if file_group.collaborators else "no collaborators"))
                if file_group.description:
                    print("\t\t  description: {}"
                          .format(file_group.description))


def _get_match_fn(globs, regexes):
    # Constructs a single regex that tests for matches against the globs in
    # 'globs' and the regexes in 'regexes'. Parts are joined with '|' (OR).
    # Returns the search() method of the compiled regex.
    #
    # Returns None if there are neither globs nor regexes, which should be
    # interpreted as no match.

    if not (globs or regexes):
        return None

    regex = ""

    if globs:
        glob_regexes = []
        for glob in globs:
            # Construct a regex equivalent to the glob
            glob_regex = glob.replace(".", "\\.").replace("*", "[^/]*") \
                             .replace("?", "[^/]")

            if not glob.endswith("/"):
                # Require a full match for globs that don't end in /
                glob_regex += "$"

            glob_regexes.append(glob_regex)

        # The glob regexes must anchor to the beginning of the path, since
        # we return search(). (?:) is a non-capturing group.
        regex += "^(?:{})".format("|".join(glob_regexes))

    if regexes:
        if regex:
            regex += "|"
        regex += "|".join(regexes)

    return re.compile(regex).search


def _load_maintainers(path):
    # Returns the parsed contents of the maintainers file 'filename', also
    # running checks on the contents. The returned format is plain Python
    # dicts/lists/etc., mirroring the structure of the file.

    with open(path, encoding="utf-8") as f:
        try:
            yaml = load(f, Loader=SafeLoader)
        except YAMLError as e:
            raise MaintainersError("{}: YAML error: {}".format(path, e))

        _check_maintainers(path, yaml)
        return yaml


def _is_str_list(lst):
    return isinstance(lst, list) and all(isinstance(elm, str) for elm in lst)


def _check_globs(root, area_dict, where, ferr):
    # Checks that every glob in 'files' and 'files-exclude' matches a file
    for files_key in "files", "files-exclude":
        for glob_pattern in area_dict.get(files_key, []):
            paths = tuple(root.glob(glob_pattern))
            if not paths:
                ferr("glob pattern '{}' in '{}' in {} does not match any "
                     "files".format(glob_pattern, files_key, where))
            if not glob_pattern.endswith("/") and \
               all(path.is_dir() for path in paths):
                ferr("glob pattern '{}' in '{}' in {} matches only "
                     "directories, but has no trailing '/'"
                     .format(glob_pattern, files_key, where))


def _check_regexes(area_dict, where, ferr):
    # Checks that every regex in 'files-regex' and 'files-regex-exclude'
    # compiles
    for files_regex_key in "files-regex", "files-regex-exclude":
        for regex in area_dict.get(files_regex_key, []):
            try:
                re.compile(regex)
            except re.error as e:
                ferr("bad regular expression '{}' in '{}' in {}: {}"
                     .format(regex, files_regex_key, where, e.msg))


def _check_file_groups(root, area_name, file_groups, ferr):
    # Checks the 'file-groups' list of area 'area_name'
    if not isinstance(file_groups, list):
        ferr("malformed 'file-groups' value for area '{}' -- should be a "
             "list".format(area_name))

    for i, group_dict in enumerate(file_groups):
        where = "file group {} in area '{}'".format(i, area_name)

        if not isinstance(group_dict, dict):
            ferr("malformed {} -- should be a dict".format(where))

        for key in group_dict:
            if key not in FILE_GROUP_KEYS:
                ferr("unknown key '{}' in {}".format(key, where))

        if not group_dict.keys() & {"files", "files-regex"}:
            ferr("{} must specify either 'files' or 'files-regex'"
                 .format(where))

        for str_field in "name", "description":
            if str_field in group_dict and \
               not isinstance(group_dict[str_field], str):
                ferr("malformed '{}' in {} -- should be a string"
                     .format(str_field, where))

        for list_field in "collaborators", "files", "files-exclude", \
                          "files-regex", "files-regex-exclude":
            if list_field in group_dict and \
               not _is_str_list(group_dict[list_field]):
                ferr("malformed '{}' in {} -- should be a list of strings"
                     .format(list_field, where))

        _check_globs(root, group_dict, where, ferr)
        _check_regexes(group_dict, where, ferr)


def _check_maintainers(maints_path, yaml):
    # Checks the maintainers data in 'yaml', which comes from the
    # maintainers file at maints_path, which is a pathlib.Path instance

    root = maints_path.parent

    def ferr(msg):
        _err("{}: {}".format(maints_path, msg))  # Prepend the filename

    if not isinstance(yaml, dict):
        ferr("empty or malformed YAML (not a dict)")

    ok_status_s = ", ".join('"' + s + '"' for s in sorted(AREA_STATUSES))

    for area_name, area_dict in yaml.items():
        where = "area '{}'".format(area_name)

        if not isinstance(area_dict, dict):
            ferr("malformed entry for {} (not a dict)".format(where))

        for key in area_dict:
            if key not in AREA_KEYS:
                ferr("unknown key '{}' in {}".format(key, where))

        if "status" in area_dict and \
           area_dict["status"] not in AREA_STATUSES:
            ferr("bad 'status' key on {}, should be one of {}"
                 .format(where, ok_status_s))

        if not area_dict.keys() & {"files", "files-regex", "file-groups"}:
            ferr("either 'files', 'files-regex', or 'file-groups' (or "
                 "combinations) must be specified for {}".format(where))

        if not area_dict.get("maintainers") and \
           area_dict.get("status") == "maintained":
            ferr("maintained {} with no maintainers".format(where))

        for list_name in "maintainers", "collaborators", "inform", "files", \
                         "files-exclude", "files-regex", \
                         "files-regex-exclude", "labels":
            if list_name in area_dict and \
               not _is_str_list(area_dict[list_name]):
                ferr("malformed '{}' value for {} -- should be a list of "
                     "strings".format(list_name, where))

        _check_globs(root, area_dict, where, ferr)
        _check_regexes(area_dict, where, ferr)

        if "file-groups" in area_dict:
            _check_file_groups(root, area_name, area_dict["file-groups"],
                               ferr)

        if "description" in area_dict and \
           not isinstance(area_dict["description"], str):
            ferr("malformed 'description' value for {} -- should be a "
                 "string".format(where))


def _git(*args):
    # Helper for running a Git command. Returns the rstrip()ed stdout
    # output. Called like git("diff"). Raises GitError on errors.

    git_cmd = ("git",) + args
    git_cmd_s = " ".join(shlex.quote(word) for word in git_cmd)

    try:
        git_process = subprocess.Popen(
            git_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        _giterr("git executable not found (when running '{}'). Check that "
                "it's listed in the PATH environment variable"
                .format(git_cmd_s))
    except OSError as e:
        _giterr("error running '{}': {}".format(git_cmd_s, e))

    stdout, stderr = git_process.communicate()
    if git_process.returncode:
        _giterr("error running '{}'\n\nstdout:\n{}\nstderr:\n{}".format(
            git_cmd_s, stdout.decode("utf-8"), stderr.decode("utf-8")))

    return stdout.decode("utf-8").rstrip()


def _ls_files(path=None):
    cmd = ["ls-files"]
    if path is not None:
        cmd.append(path)
    return _git(*cmd).splitlines()


def _err(msg):
    raise MaintainersError(msg)


def _giterr(msg):
    raise GitError(msg)


def _serr(msg):
    # For reporting errors when get_maintainer.py is run as a script.
    # sys.exit() shouldn't be used otherwise.
    sys.exit("{}: error: {}".format(sys.argv[0], msg))


class MaintainersError(Exception):
    "Exception raised for MAINTAINERS.yml-related errors"


class GitError(Exception):
    "Exception raised for Git-related errors"


if __name__ == "__main__":
    _main()
