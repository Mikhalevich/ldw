#!/usr/bin/env python3

import argparse
import time
import os
import os.path
import subprocess
import re


class LibNotDefinedError(RuntimeError):
    def __init__(self):
        pass

    def __repr__(self):
        return "library path is not defined"


class Collector:
    def __init__(self, root, lib=None):
        self.__root = os.path.abspath(root)
        self.__lib = None
        if lib:
            self.__lib = os.path.abspath(lib)
        self.__not_found = {}
        self.__group = {}
        self.__all_libs = set()
        self.__unique = set()
        self.__print_separator = "================================>"

        self.__collect()

    @property
    def not_found(self):
        return self.__not_found

    @property
    def group(self):
        return self.__group

    @property
    def unique(self):
        return self.__unique

    @property
    def useless(self):
        if not self.__lib:
            raise LibNotDefinedError()
        return self.__all_libs.difference(self.__unique)

    @property
    def external(self):
        if not self.__lib:
            raise LibNotDefinedError()
        return self.__unique.difference(self.__all_libs)

    @property
    def separator(self):
        return self.__print_separator

    @separator.setter
    def separator(self, sep):
        self.__print_separator = sep

    @staticmethod
    def __execute_shell(command):
        res = subprocess.run(command, stdout=subprocess.PIPE, check=False, shell=True)
        return res.stdout.decode("utf-8")

    @staticmethod
    def __is_lib(filename):
        return ".so" in filename

    @staticmethod
    def __is_executable(filename):
        if os.access(filename, os.X_OK):
            return True
        return Collector.__is_lib(filename)

    @staticmethod
    def __ldd_deps(filename):
        """return list with dependencies and not found dependencies for current shared object
        without address which is returned by ldd command"""
        re_remove_address_pattern = re.compile(r"\s*\(.+\)\s*$", re.MULTILINE)
        re_pattern = re.compile(r"^\s*(.+)\s*$", re.MULTILINE)
        not_found_pattern = re.compile(r"not found", re.IGNORECASE)

        deps_list = []
        not_found_list = []

        output = Collector.__execute_shell("ldd {0}".format(filename))
        output = re_remove_address_pattern.sub("", output)

        for match in re_pattern.finditer(output):
            if match:
                dep = match.group(1)
                if not_found_pattern.search(dep):
                    not_found_list.append(dep)
                deps_list.append(dep)

        return deps_list, not_found_list

    def __collect_libs(self):
        for file in os.listdir(self.__lib):
            if self.__is_lib(file):
                self.__all_libs.add(file)

    def __collect(self):
        """collect all dependencies, returns tuple where
        first value it's dictionary with not found dependencies
        second value it's dictionary where key - library or executable value - list of dependencies
        third value it's set with unique library dependencies"""
        for root, dirs, files in os.walk(self.__root):
            for file in files:
                filename = os.path.abspath(os.path.join(root, file))
                if self.__is_executable(filename):
                    deps_list, not_found_list = self.__ldd_deps(filename)
                    if not_found_list:
                        self.__not_found[filename] = not_found_list
                    if deps_list:
                        self.__group[filename] = deps_list

                    for dep in deps_list:
                        index = dep.find("=>")
                        if index >= 0:
                            dep = dep[0:index]
                        self.__unique.add(dep.strip())

        if self.__lib:
            self.__collect_libs()

    def __print_deps(self, description, deps):
        print("{0}: {1}".format(description, self.__print_separator))
        for dep in sorted(deps):
            print("\t\t{0}".format(dep))

    def print(self, all_flag, group_flag):
        if group_flag:
            for lib, deps in self.__group.items():
                self.__print_deps("\ndependencies for {0}".format(lib), deps)

        if all_flag:
            self.__print_deps("\nall dependencies", self.__unique)

        if self.__not_found:
            for lib, deps in self.__not_found.items():
                self.__print_deps("\nnot found dependencies for {0}".format(lib), deps)
        else:
            print("\nno missing libs found...")

        if self.external:
            self.__print_deps("\nexternal dependecies", self.external)
        else:
            print("\nno external libs found...")

        if self.useless:
            self.__print_deps("\nusless dependencies", self.useless)
        else:
            print("\nno useless libs found...")


def main():
    parser = argparse.ArgumentParser(description="Linux dependency walker")
    parser.add_argument("root", action="store", help="root directory for scan")
    parser.add_argument("-a", "--all", dest="all", action="store_true", default=False, help="Print all dependencies")
    parser.add_argument("-g", "--group", dest="group", action="store_true", default=False,
                        help="Print dependencies for each executable or library")
    parser.add_argument("-l", "--lpath", dest="lib_path", action="store", default=None,
                        help="Print useless dependencies which is not in lib path")
    args = parser.parse_args()

    start_time = time.time()

    c = Collector(args.root, args.lib_path)
    c.print(args.all, args.group)

    end_time = time.time()
    print("script execution: {0} ms".format((end_time - start_time) * 1000))


if __name__ == "__main__":
    main()
