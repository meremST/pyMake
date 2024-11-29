#!/usr/bin/python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024 Maxime Méré.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#   3. Neither the name of the [ORGANIZATION] nor the names of its contributor
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#===============================================================================
#
#          FILE: pyMake.py
#
#         USAGE: python pyMake.py --help
#
#   DESCRIPTION: pyMake is a tool to build and flash ST project
#
#       OPTIONS: ---
#  REQUIREMENTS: ---
#          BUGS: ---
#         NOTES: ---
#        AUTHOR: MME (maxime.mere@st.com)
#  ORGANIZATION: STMicroelectronics
#       CREATED: 2023-07-03
#      REVISION:  v2.1
#===============================================================================
#
# pyMake is a tool that parses TOML files that contains information to build or
# flash projects.
#
# To work properly, pyMake must be in a folder that is located in the same place
# as the various projects you wish to compile.
# This gives the following file structure (with some projects as example):
#
#   WORKING directory tree
#   ├── devpack/
#   ├── linux/
#   ├── u-boot/
#   ├── tf-a/
#   |   ├── tf-a
#   |   └── build/
#   ├── optee/
#   │   ├── optee-mp2/
#   │   ├── optee-mp15/
#   │    ...
#   │   └──  optee_os/
#   ├── pyMake/
#   │   ├── pyMake.py
#   │   ├── mp1.toml
#   |   ├── mp2.toml
#   |   ├── mp157f-dk2.toml
#   │   └── ...
#   └── ...
#
# TOML files must respect a certain number of rules:
#   - The table [header] is mandatory and should contain the keys: name, type,
#     and can optionally have the keys 'include' and 'source'.
#       - By including another TOML file you can use its content and and inherit
#         of the key/value.
#   - You can define a command by declaring a [table], the directory  that
#     contain the source code must be named ientically. 'all' is a reserved
#     keyword.
#   - You must define inside a command at least the key 'exeCommand' and/or
#     'flashCommand' (they can be defined in an included file).
#       - These commands are arrays that contain keys (in the form of strings)
#         that must contain string with correspond to part of the command to
#         execute to build or flash your project.
#       - The key inside a commed are defined only for this command.
#       - The whole key defined in flash and build command must be defined in
#         toml files. If some key aren't defined, they are searched in the toml
#         file included in the header table. They must be string type.
#       - '_make', '_cmake' and '_src_' are special values that aren't keys.
#           - '_make' is used to generate a make command
#           - '_cmake' is used to generate a cmake command
#           - '_src_' is used to add the source directory of the code to compile
#       - add underscores before and after a _key_, inside the command array
#         will remove the space with the next value. they are spaced otherwise.
#         Please note that the underscore aren't part of the key name.
#         Use underscore in key name is not recomended.
#       - Put a string with and '=' sign inside the array will add it as is to
#         the command without space with the next value.
# See bellow an example of a complete toml that can run the build command:
# ```make all BUILD_PLAT=../build```
#
# ```
# [header]
# name="test"
# type="core"
#
# [example]
# exeCommand=[
#               "_make","optimization","target",
#               "BUILD_PLAT=","buildDir"
#            ]
#
# optimization="" # Could be overwritten in another file that include this one
# target="all"
# buildDir="../build"
# ```
#
# I recommend organizing the TOML file hierarchy as follows (optional):
# mp.toml <- mp1.toml <- mp157f-dk2.toml <- mp157f-dk2-custom.toml
# The first TOML file (mp.toml) contains the command to execute, mp1.toml adds
# the arguments common to all mp1 platforms. mp157f-dk2.toml is complete and
# will build the stm32mp157f-dk2.dts device tree with basic options.
# mp157f-dk2-custom.toml is a file that uses the dk2 as a base but will add
# specific options such as trusted boot or firmware update. The device tree can
# also be changed.
#
import subprocess, os, argparse
import tomli # TOML library

class Override:
    def __init__(self, option=""):
        __sep = ":"
        if option != "" and __sep in option:
            self.element = option[:option.index(__sep)].strip()
            self.arg = ' ' + option[option.index(__sep)+1:].strip()
        else:
            self.element = ""
            self.arg = ""

def exec(command, stop=False):
    #print(command)
    print("")
    p = subprocess.run(command, shell=True)
    if (stop == True) and (p.returncode != 0):
        print("Error: failed to execute command: " + command)
        exit(-1)

def lf_args(element, command, dict_list):
    for dict in dict_list:
        if element in dict[command]:
            return dict[command][element]
    print("Error: element '"+element+"' not found in any TOML files.")
    exit(-1)

def checkCommand(command, dict_list):
    for dict in dict_list:
        if 'status' in dict[command]:
            return "Error: received the status: '"+dict[command]['status']+"' from the TOML file:"\
                +dict['header']['name']

    return 0

def generateCommand(command, dict_list, source, run_flash, override=Override()):
    ret = checkCommand(command, dict_list)
    if ret != 0:
        return ret

    if run_flash:
        run = 'flashCommand'
    else:
        run = 'exeCommand'
    for dict in dict_list:
        if run in dict[command]:
            exe_command=dict[command][run]
            break
    if not 'exe_command' in locals():
        return "Error: "+run+" not found in any TOML files."

    commands_to_run=""
    next_no_space=False
    first_cmd=True

    for element in exe_command:
        if "_make" in element[0:5]:
            if not first_cmd:
                commands_to_run += ";"
            else: first_cmd = False
            commands_to_run += " make -j$(($(nproc) - 1)) -C "+source
        elif "_cmake" in element[0:6]:
            if not first_cmd:
                commands_to_run+=";"
            else: first_cmd=False
            commands_to_run += " cmake -S " + source
        elif "_src_" in element[0:5]:
            if not next_no_space:
                commands_to_run+=" "
            commands_to_run += source
            next_no_space = True
        elif override.element == element and element != "":
            commands_to_run += override.arg
        elif element[0] == '_' and element[len(element)-1] == '_':
            # var written _likeThis_ have no space with the next element
            commands_to_run += lf_args(element[1:(len(element)-1)],command,dict_list)
            next_no_space=True
        elif element[len(element)-1] == "=":
            commands_to_run+=" "+element
            next_no_space = True
        else:
            if "_" in element:
                print("Warning: the use of underscores is reserved."\
                      " Try not to use them in the TOML keys! (in '"+element+"')")
            arg = lf_args(element, command, dict_list)
            if next_no_space:
                commands_to_run += arg
                next_no_space = False
            else:
                commands_to_run += " " + arg

    commands_to_run += " "

    #string=string[:len(string)-2]+"."
    return commands_to_run

def getSource(cmd):
    directories = next(os.walk('../'+cmd))[1]
    for n in range(0,len(directories)):
        print(str(n+1)+".",directories[n])

    try:
        inpt = input("Choice: ")

        choice = 0
        for i in range(1,n+2):
            if int(inpt) == i:
                choice = i
    except KeyboardInterrupt:
        print("")
        exit(0)
    except Exception as e:
        print("Input error:",e)
        exit(-1)

    if choice < 0 or choice > len(directories):
        print("Error: choice out of range")
        exit(-1)
    # Changing source according to code
    source = "../"+cmd+"/"+directories[choice-1]+"/"

    return source

def main():

    parser = argparse.ArgumentParser(
        description="Script that use a .toml file to build ST MPU projects."\
                    " Don't forget to set the correct SDK."\
                    " Usage example: "\
                    "'python pyMake.py tfa -s ../tf-a/tuto/ -if mp157c-dk2-sdmmc.toml'"
                    )
    parser.add_argument("command", nargs='?',
                        help="The module you want to build. "\
                        "If not set, the program will run in interactive mode.")
    parser.add_argument("--source","-s",required=False, help="The source directory")
    parser.add_argument("--inputFile","-if",required=True, help="The target TOML description file.")
    parser.add_argument("--debug",'-d',required=False,action='store_true',
                        help="Change the debug level: 10..50 (30: warning, 40: info)")
    parser.add_argument("--flash",required=False,action='store_true',
                        help="This execute the flash command, which usually updates or prepares"\
                        " the firmware, and write it to the SD card.")
    parser.add_argument("--override","-or",required=False,
                        help="Override one command option. You must put a string after the"\
                        " argument composed of the option name then a colon (:) and the string"\
                        " value you want to override.")
    parser.add_argument("--noexe",required=False,action='store_true',
                        help="Disables execution (displays commands only).")
    args = parser.parse_args()

    lst_toml_files = [] # A table containing the whole toml files related to the initial toml file

    if args.debug:
        print("debug:",args.debug)

    if args.flash:
        run_flash = True
    else:
        run_flash = False

    with open(args.inputFile, "rb") as f:
        toml_dict = tomli.load(f)

    lst_toml_files.append(toml_dict)

    interactive_mode = (args.command == None)

    if 'header' in toml_dict:
        if not 'name' in toml_dict['header']: # or not 'type' in toml_dict['header']
            print("Error: header needs a 'name' key.")
            exit(-1)
    else:
        print("Error: header not found in TOML file.")
        exit(-1)

    if 'all' in toml_dict:
        print("Error 'all' can't be used as a table.")
        exit(-1)

    try:
        while 'include' in toml_dict['header']:
            with open(toml_dict['header']['include'], "rb") as f:
                toml_dict = tomli.load(f)
                lst_toml_files.append(toml_dict)
    except Exception as e:
        print("Error during parsing of",f.name,":",e)
        exit(-1)

    if args.debug:
        print("debug: source:",args.source)
        print("debug: ",lst_toml_files)

    cmd = ""

    if not interactive_mode: # standard mode with a complete command

        if args.command != "all":
            if not args.source:
                if not ('source' in lst_toml_files[0]['header']):
                    print("Error: missing a source argument in TOML header or in command option.")
                    exit(-1)
                else:
                    source=lst_toml_files[0]['header']['source']
            else:
                source=args.source
            if os.path.isdir(source):
                if "/" != source[len(source)-1]:
                    source+="/"
            else:
                print("Error: The source directory specified is not found.")
                exit(-20)

        cmd = args.command
    else: # Interactive mode
        print("=== No command found, starting in interactive mode ===")
        print("Select the program you want to build:")
        n=1
        for key in list(lst_toml_files[0]):
            if key != "header":
                print(str(n)+".",key)
                n+=1

        print(str(n)+". all")

        try:
            inpt = input("Choice: ")

            choice = 0
            for i in range(1,n+1):
                if int(inpt) == i:
                    choice = i
        except KeyboardInterrupt:
            print("")
            exit(0)
        except Exception as e:
            print("Input error:",e)
            exit(-1)

        if choice <= 0 or choice > len(list(lst_toml_files[0])):
            print("Error: choice out of range.")
            exit(-1)

        if choice != n:
            cmd =list(lst_toml_files[0])[choice]

            print("Select the source directory:")
            source = getSource(cmd)
        else:
            cmd = "all"

        print("Do you want to flash or build?")
        print("1. Flash")
        print("2. Build")

        try:
            inpt = input("Choice: ")

            if int(inpt) == 1:
                run_flash = True
                rf_text="--flash"
            else:
                run_flash = False
                rf_text=""
        except KeyboardInterrupt:
            print("")
            exit(0)
        except Exception as e:
            print("Input error:",e)
            exit(-1)

        if cmd != "all":
            print("======================================================")
            print("       next time you can run pyMake like this:")
            print("python pyMake.py",cmd,"-s",source,"-if",args.inputFile,rf_text)
            print("======================================================")

    if args.debug:
        print("debug: cmd:",cmd)

    #call a function that create the command line.")
    if cmd != "all":
        unsuported_com = False
        for dict in lst_toml_files:
            if not (cmd in dict):
                unsuported_com = True
                filename = dict['header']['name']
        if unsuported_com:
            print("Error the command: '"+cmd+"' is not found. Check the file: "+filename+".toml")
            exit(-1)

        command = checkCommand(cmd,lst_toml_files)
        if command == 0:
            if args.override:
                override = args.override
            else:
                override = ""

            override = Override(override) # overcharge the string name into the class
            command = generateCommand(cmd, lst_toml_files, source, run_flash, override)

        # Print and execute the command is there is no issue
        print("")
        print(command)

        if command[:5] == "Error":
            exit(-1)

        if not args.noexe:
            exec(command)

    else: # all
        print("Warning: 'all' is still in beta-test")

        commands = []

        for cmd in list(lst_toml_files[0]):
            ret = checkCommand(cmd, lst_toml_files)
            if cmd != "header" and ret == 0:
                print("select the",cmd,"source:")
                source = getSource(cmd)
                command = generateCommand(cmd, lst_toml_files, source, run_flash)
                if command[:5] != "Error":
                    commands.append(command)
                else:
                    print(command)
            elif ret != 0:
                print(cmd+":",ret)


        if not args.noexe:
            for command in commands:
                exec(command)
        else:
            print(commands)

    exit(0)

if __name__ == "__main__":
    main()