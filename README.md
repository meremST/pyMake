# pyMake

pyMake is a tool that parses TOML files that contains information to build or
flash projects.

To work properly, pyMake must be in a folder that is located in the same place
as the various projects you wish to compile.
This gives the following file structure (with some projects as example):

```
   WORKING directory tree
  ├── devpack/
  ├── linux/
  ├── u-boot/
  ├── tf-a/
  |   ├── tf-a
  |   └── build/
  ├── optee/
  │   ├── optee-mp2/
  │   ├── optee-mp15/
  │    ...
  │   └──  optee_os/
  ├── pyMake/
  │   ├── pyMake.py
  │   ├── mp1.toml
  |   ├── mp2.toml
  |   ├── mp157f-dk2.toml
  │   └── ...
  └── ...
```

TOML files must respect a certain number of rules:
* The table [header] is mandatory and should contain the keys: name, type, and can optionally have the keys 'include' and 'source'.
  * By including another TOML file you can use its content and and inherit of the key/value.
* You can define a command by declaring a [table], the directory  that contain the source code must be named ientically. 'all' is a reserved keyword.
* You must define inside a command at least the key 'exeCommand' and/or 'flashCommand' (they can be defined in an included file).
  * These commands are arrays that contain keys (in the form of strings) that must contain string with correspond to part of the command to execute to build or flash your project.
  * The key inside a commed are defined only for this command.
  * The whole key defined in flash and build command must be defined in toml files. If some key aren't defined, they are searched in the toml file included in the header table. They must be string type.
   * '_make', '_cmake' and '_src_' are special values that aren't keys.
      * '_make' is used to generate a make command
      * '_cmake' is used to generate a cmake command
      * '_src_' is used to add the source directory of the code to compile
   * add underscores before and after a _key_, inside the command array will remove the space with the next value. they are spaced otherwise. Please note that the underscore aren't part of the key name. Use underscore in key name is not recomended.
   * Put a string with and '=' sign inside the array will add it as is to the command without space with the next value.
See bellow an example of a complete toml that can run the build command:
```bash
make all BUILD_PLAT=../build
```

```toml
[header]
name="test"
type="core"
[example]
exeCommand=[
            "_make","optimization","target",
            "BUILD_PLAT=","buildDir"
           ]

optimization="" # Could be overwritten in another file that include this one
target="all"
buildDir="../build"
```

I recommend organizing the TOML file hierarchy as follows (optional):
```
mp.toml <- mp1.toml <- mp157f-dk2.toml <- mp157f-dk2-custom.toml
```

The first TOML file (*mp.toml*) contains the command to execute, *mp1.toml* adds
the arguments common to all mp1 platforms. *mp157f-dk2.toml* is complete and
will build the *stm32mp157f-dk2.dts* device tree with basic options.
*mp157f-dk2-custom.toml* is a file that uses the dk2 as a base but will add
specific options such as trusted boot or firmware update. The device tree can
also be changed.
