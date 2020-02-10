lfixer
======

Lfixer (log-fixer.py) is a simple tool to apply
custom fixing logic to log files,
processing several files in parallel line by line,
and keeping progress in local sqlite database.


Example usage
-------------

From source folder:

```
PYTHONPATH=. python3 bin/log-fixer.py Logs-In-Dir/ Logs-Out-Dir/ --parallel=64
```

After installing Debian package:

```
log-fixer.py Logs-In-Dir/ Logs-Out-Dir/ --parallel=64
```

Help page
---------
```
PYTHONPATH=. python3 bin/log-fixer.py --help
log-fixer.py --help
```


Usage with custom log fixer function
------------------------------------


By default, a `json_fixer` function from `lfixer.broken_json` module of `lfixer` package is used.

It is easy to write custom fixer function, which should take single required parameter,
and may be referenced using `--fixer-function` script argument, like:

```
log-fixer.py Logs-In-Dir/ Logs-Out-Dir/  --fixer-function=package.module.function_name
```

The fixer function should return fixed log line, or None in case if the line was irrecoverable.



Build debian package
--------------------

Currently having docker installed on your host is the only supported way to do this.

`make deb`

A debian package will reside in `out/` directory of the source folder.



Build docker image
------------------

`make docker`



Docker usage example
---------------------

```
docker run -v /home/user/Logs/:/opt/Logs/ -v /home/user/Logs-F/:/opt/Logs-F/ \
    -it lfixer:latest /opt/Logs/ /opt/Logs-F/
```

The progress database file is located at `/tmp/progress.db` inside docker file system.

If you want to keep progress on host, make sure to pass `-v some-host-path:/tmp/progress.db`
parameter to your docker run command.


Run test suite
--------------
```python setup.py test```


Run test suite in docker
-------------------------
`make test_docker`


TODO/FIXME
----------
Test & benchmark with https://github.com/s3fs-fuse/s3fs-fuse


LICENSE
-------
MIT.
