#!/usr/bin/env python3

"""
There are no dependencies apart from standard Python3 library.
"""
import argparse
import collections
import itertools
import logging
import os
import sqlite3

from pydoc import locate


logger = logging.getLogger(__name__)
arg_parser = argparse.ArgumentParser('Log file fixer')

arg_parser.add_argument('input_directory',
                        help='Directory, which contains input files.')
arg_parser.add_argument('output_directory',
                        help='Directory, which contains output files.')
arg_parser.add_argument('-p', '--parallels', type=int, default=8,
                        help='How many files in parallel should we process.')
arg_parser.add_argument('-f', '--fixer-function',
                        help='How to locate fixer function.',
                        default='lfixer.broken_json.json_fixer')
arg_parser.add_argument('--progress-db-location',
                        help='Location of progress database.',
                        default='.lfixer.db')
arg_parser.add_argument('--progress-fsync', default=100, type=int,
                        help='How often to fsync progress into SQLite db.')
arg_parser.add_argument('--log-fsync', default=100, type=int,
                        help='How often to fsync logs into output directory.')
arg_parser.add_argument('--overwrite', action='store_true',
                        help='Whether to overwrite result files.')
arg_parser.add_argument('--clean', action='store_true',
                        help='Whether to clean database before running.')


class LoggingPipe:
    """Open needed files.
       Process them line by line.
       Write fixed output for each line.
    """

    def __init__(self, in_file_paths, out_file_paths,
                 progress_db_location, progress_fsync=100, log_fsync=100,
                 overwrite=False):
        """Initialize given logging pipe.

        Make sure in_file_path and out_file_path do contain
        corresponding file pairs on the corresponding indexes in list.

        :param in_file_paths: Input file path.
        :type in_file_path: list[str]

        :param out_file_paths: Output file path.
        :type in_file_path: list[str]

        :param progress_db_location: Location of progress database.
        :type progress_db_location: str

        :param progress_fsync: Number of iterations before progress fsync.
        :type progress_fsync: int

        :param log_fsync: Number of iterations before log file flush.
        :type log_fsync: int

        :param overwrite: Whether to overwrite file or not.
        :type overwrite: bool
        """
        self.progress_fsync = progress_fsync
        self.log_fsync = log_fsync

        self.in_file_paths = in_file_paths
        self.out_file_paths = out_file_paths

        # Maps file name --> file socket.
        self.in_files = collections.OrderedDict(
            [(i_f, None) for i_f in in_file_paths],
        )
        self.out_files = collections.OrderedDict(
            [(o_f, None) for o_f in out_file_paths],
        )

        # Tracks line progress in each file.
        self.progress = collections.OrderedDict(
            [(i_f, 0) for i_f in in_file_paths],
        )

        # Tracks loop counter.
        self.iteration = 0
        self.progress_db_location = progress_db_location
        self.progress_db = None

        self.overwrite = overwrite

    @staticmethod
    def _remove_index_from_list(l, idx_to_remove):
        return [p for (num, p) in enumerate(l) if num != idx_to_remove]

    ########################################
    #   PROGRESS DATABASE METHODS
    ########################################

    def _init_progress(self):
        """Initialize progress database."""
        self.progress_db = sqlite3.connect(self.progress_db_location)
        cursor = self.progress_db.cursor()
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS progress
               (fpath text PRIMARY KEY, fline integer);''')
        cursor.close()

    def _read_progress(self, cursor):
        """Read saved progress from SQLite."""
        cursor.execute('''SELECT fline, fpath FROM progress;''')
        previous_progress = cursor.fetchall()
        cursor.close()
        for fline, fpath in previous_progress:
            fline = int(fline)
            self.progress[fpath] = fline

            if fpath in self.in_file_paths:
                if fline == -1:
                    # File have been processed before.
                    # Remove it from further processing.
                    logger.warning('File %s have been '
                                   'processed in full before.',
                                   fpath)
                    idx_to_remove = self.in_file_paths.index(fpath)
                    ofilename = self.out_file_paths[idx_to_remove]

                    self.in_file_paths = self._remove_index_from_list(
                        self.in_file_paths, idx_to_remove)
                    self.out_file_paths = self._remove_index_from_list(
                        self.out_file_paths, idx_to_remove)

                    self.in_files.pop(fpath)
                    self.out_files.pop(ofilename)
                else:
                    logger.warning('File %s was already processed before.'
                                   ' Seeking to %s.', fpath, fline)

    def _fsync_progress(self, cursor):
        """Write current progress into SQlite."""
        for (fpath, progress_line) in self.progress.items():
            if progress_line is None:
                # -1 == means file processed in full
                progress_line = -1
            cursor.execute(
                '''REPLACE INTO progress (fline,fpath) VALUES (?,?)''',
                (progress_line, fpath)
            )
        self.progress_db.commit()
        cursor.close()

    ########################################
    #   FILE HANDLING METHODS
    ########################################

    def _fsync_logs(self):
        for fsock in self.out_files.values():
            fsock.flush()

    def __enter__(self):
        """Open in files for reading, out files for writing."""

        # initialize progress from DB
        self._init_progress()
        self._read_progress(self.progress_db.cursor())

        for (file_dict, mode) in [
                    (self.in_files, 'rb'),
                    (self.out_files, 'wb+' if self.overwrite else 'ab+'),
                ]:
            for path in file_dict.keys():
                try:
                    file_dict[path] = open(path, mode)
                except OSError:
                    logger.exception('Can not open given file by '
                                     'given path: %s in mode %s', path, mode)
                else:
                    logger.info('Opened file %s in mode %s;', path, mode)
                    if mode == 'rb' and path in self.progress:
                        file_dict[path].seek(self.progress[path])
        return self

    def __exit__(self, *args):
        """Close all file handles in use."""

        for (file_dict, do_flush) in [
                    (self.in_files, False), (self.out_files, True)
                ]:

            for (path, sock) in file_dict.items():

                if sock is not None:
                    if do_flush:
                        sock.flush()
                    sock.close()

        if self.progress_db:
            self._fsync_progress(self.progress_db.cursor())
            self.progress_db.close()

    ########################################
    #   HIGH-ORDER PROCESSING
    ########################################

    def process(self, fixer_function):
        """Process open files line by line.

        Record progress every self.progress_fsync lines.
        Fsync logs every self.log_fsync lines.

        :param fixer_function: A fixer function callable.
        :type fixer_function: function
        """

        # zip_longest will either produce lines for files in self.in_files,
        # or None in case if EOF have been reached.
        for lines in itertools.zip_longest(*self.in_files.values()):

            for findex, line in enumerate(lines):

                fname = self.in_file_paths[findex]
                ofname = self.out_file_paths[findex]
                ofile = self.out_files[ofname]

                if line is None:
                    # EOF reached
                    if self.progress[fname] is not None:
                        self.progress[fname] = None
                else:
                    fixed_line = fixer_function(line)
                    if fixed_line is not None:
                        ofile.write(fixed_line)

                    self.progress[fname] += len(line)

            self.iteration += 1

            # Write progress into SQLite
            if not (self.iteration % self.progress_fsync):
                self._fsync_progress(self.progress_db.cursor())

            # Flush output log files
            if not (self.iteration % self.log_fsync):
                self._fsync_logs()

        # Mark all files as processed
        self.progress = {k: None for k in self.progress.keys()}

        # Fsync after last lines were processed.
        self._fsync_progress(self.progress_db.cursor())
        self._fsync_logs()


def process_log_file_buffer(args, directories, fixer_fn, db_location, fbuf):
    """Process file log buffer: all files in set."""
    input_files = []
    output_files = []
    for file_path in fbuf:
        input_files.append(file_path)
        output_files.append(
            file_path.replace(directories['input'], directories['output'])
        )
    with LoggingPipe(input_files, output_files,
                     db_location, args.progress_fsync,
                     args.log_fsync,
                     overwrite=args.overwrite) as pipe:
        pipe.process(fixer_fn)

    fbuf.clear()


def process_log_directory(args, directories, fixer_fn, db_location):
    # Iterate over files. Process (fix) --parallels files at once.
    fbuf = set()
    for dpath, dirs, files in os.walk(directories['input']):
        dirs.sort()

        for fname in sorted(files):

            fbuf.add(os.path.join(dpath, fname))

            if len(fbuf) == args.parallels:
                process_log_file_buffer(args, directories,
                                        fixer_fn, db_location, fbuf)

    if fbuf:
        process_log_file_buffer(args, directories, fixer_fn, db_location, fbuf)


def main():
    """Fixes log stream."""

    excode = 1
    args = arg_parser.parse_args()

    # Validate and fix input and output directory input parameters.
    directories = {}
    for (directory_parameter_input, directory_type) in [
                (args.input_directory, 'input'),
                (args.output_directory, 'output'),
            ]:

        directory_parameter = os.path.abspath(
            os.path.expanduser(directory_parameter_input))

        if not os.path.exists(directory_parameter):
            if directory_type == 'input':
                logger.critical('Can not locate input directory')
                excode = 4
                break
            else:
                os.makedirs(directory_parameter, exists_ok=True)

        if not directory_parameter.endswith('/'):
            directory_parameter = '{}/'.format(directory_parameter)

        directories[directory_type] = directory_parameter

    else:

        fixer_fn = locate(args.fixer_function)
        if fixer_fn is None:
            logger.error('Can not locate log fixer function.')
            excode = 3
        else:

            db_location = os.path.expanduser(args.progress_db_location)
            if args.clean:
                os.unlink(db_location)

            process_log_directory(args, directories, fixer_fn, db_location)
            # We have walked over everything.
            excode = 0

    exit(excode)


if __name__ == '__main__':
    main()
