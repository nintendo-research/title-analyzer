## Title Analyzer
This repository contains scripts that analyze the exefs section of Nintendo Switch and Nintendo Switch 2 games. The scripts collect metadata, such as embedded SDK names and segment sizes.

In the future, NPDM files may be analyzed as well, but this is not yet implemented.

The metadata is displayed publicly at https://titledb.nintendo-research.com.

### Output
The scripts produce an `executables.json` file in the `data` folder. If you share this file with me, I can add them to the public database. The following communication channels may be used:
* E-mail: ymarchand@me.com
* Discord: yannik9647

### Requirements
The following packages are required to run the scripts: `pip3 install lz4 zbic`.

### Setup
To analyze your files, run `python3 main.py <path>`. The `<path>` must refer to a folder with the following structure:

```
<path>/
  <title id>/
    v<title version>/
        main
        main.npdm
        rtld
        sdk
        subsdk0
        ...
```

The title version must be the upper part of the title version in decimal. For example, when `nxdumptool` displays the title version as `131072`, the folder must be named `v2`.

Some titles may contain multiple exefs sections that are identified by an "offset". Currently, Super Mario 3D All-Stars is the only game that I am aware of that uses this feature. In that case, the title version folder should have the following structure:

```
v<title version>/
    <id offset>/
        main
        main.npdm
        ...
```

Below is an example of a folder structure:

```
/home/yannik/files/switch/exefs/
    01009b90006dc000/
        v0/
            main
            main.npdm
            rtld
            sdk
        v7/
            main
            main.npdm
            rtld
            sdk
    010049900f546000/
        v0/
            0/
                main
                main.ndpm
                rtld
                sdk
                subsdk0
            1/
                main
                ...
                subsdk2
            2/
                main
                ...
                subsdk2
            3/
                main
                ...
                subsdk4
        v1/
            ...
```

Titles that have already been analyzed will not be reanalyzed unless you provide a "reanalyze" argument on the command line behind the path.
