#!/usr/bin/env python3

import argparse
import time
import os
import subprocess
import re


def execute_shell(command):
    res = subprocess.run(command, stdout=subprocess.PIPE, check=False, shell=True)
    return res.stdout.decode("utf-8")


def is_executable(filename):
    if os.access(filename, os.X_OK):
        return True

    if ".so" in filename:
        return True

    return False


def collect_dependencies(root_dir):
    """collect all dependencies, returns tuple where
    first value it's dictionary where key - library or executable value - list of dependencies
    second value it's set with unique library dependencies"""
    group_deps = {}
    unique_deps = set()
    re_pattern = re.compile(r"^(.+)\s+\(.*\)$", re.MULTILINE)
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            filename = os.path.abspath(os.path.join(root, file))
            if is_executable(filename):
                output = execute_shell("ldd {0}".format(filename))
                deps = []
                for match in re_pattern.finditer(output):
                    if match:
                        dep = match.group(1)
                        deps.append(dep)
                        index = dep.find("=>")
                        if index >= 0:
                            dep = dep[0:index]
                        unique_deps.add(dep)
                if len(deps) > 0:
                    group_deps[filename] = deps

    return group_deps, unique_deps


def print_results(group_deps, unique_deps, all_flag, group_flag):
    if group_flag:
        for lib, deps in group_deps.items():
            print("dependencies for {0}: ================================>".format(lib))
            for dep in sorted(deps):
                print("\t\t{0}".format(dep))

    if all_flag:
        print("all dependencies: ================================>")
        for dep in sorted(unique_deps):
            print("\t\t{0}".format(dep))


def main():
    parser = argparse.ArgumentParser(description="Linux dependency walker")
    parser.add_argument("root", action="store", help="root directory for scan")
    parser.add_argument("-a", "--all", dest="all", action="store_true", default=False, help="Print all dependencies")
    parser.add_argument("-g", "--group", dest="group", action="store_true", default=False,
                        help="Print dependencies for each executable or library")
    args = parser.parse_args()

    start_time = time.time()

    group_deps, unique_deps = collect_dependencies(args.root)
    print_results(group_deps, unique_deps, args.all, args.group)

    end_time = time.time()
    print("script execution: {0} ms".format((end_time - start_time) * 1000))


if __name__ == "__main__":
    main()
