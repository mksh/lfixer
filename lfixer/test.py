import functools
import os
import shutil
import sys
import subprocess
import tempfile
import threading
import unittest
try:
    import inotify
    import inotify.adapters
except ImportError:
    inotify = None


_curdir = os.path.abspath(os.path.dirname(__file__))
os.environ['PYTHONPATH'] = os.path.join(_curdir, '../')


class LFixerIntegrationTestCase(unittest.TestCase):

    def setUp(self):
        self._testdatadir = os.path.join(_curdir, 'test_data')
        self._testoutdir = os.path.join(_curdir, 'out')
        self._testlogdir = os.path.join(self._testoutdir, 'Logs/')
        self._progress_db_location = tempfile.mkstemp()
        if not os.path.exists(self._testoutdir):
            os.makedirs(self._testoutdir)
        if not os.path.exists(self._testlogdir):
            os.makedirs(os.path.join(self._testlogdir))

    def tearDown(self):
        os.unlink(self._progress_db_location[1])
        shutil.rmtree(self._testoutdir)

    def kill_lfixer(self):
        self.p.kill()

    def call_lfixer(self, *args):
        self.e = threading.Event()
        self.p = subprocess.Popen([
                sys.executable,
                'bin/log-fixer.py', self._testdatadir,
                self._testoutdir,
                '--progress-db-location={}'.format(
                    self._progress_db_location[1]
                ),
            ] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,)
        self.outs, self.errs = self.p.communicate()
        self.e.set()
        return self.p.returncode

    def assert_file_lines_equal(self, _file_path, _lines):
        with open(os.path.join(self._testoutdir, _file_path), 'r') as fl:
            lines = list(fl.readlines())
        self.assertListEqual(lines, _lines)

    def test_fix_json_logs_overwrite(self):
        retcode = self.call_lfixer('--overwrite')
        self.assertFalse(retcode)
        self.assert_file_lines_equal(
            'Logs/Logs-08-02-2020',
            ['{"json": "world"}\n', '{"field": "value"}\n'],
        )
        self.assert_file_lines_equal(
            'Logs/Logs-09-02-2020',
            ['{"goodbye": "json"}\n', '{"hello": "json"}\n'],
        )

    def test_fix_json_logs_progress_no_append(self):
        retcode = self.call_lfixer('--overwrite')
        self.assertFalse(retcode)
        retcode = self.call_lfixer()
        # Log file content was added once
        self.assert_file_lines_equal(
            'Logs/Logs-08-02-2020',
            ['{"json": "world"}\n', '{"field": "value"}\n'],
        )
        self.assert_file_lines_equal(
            'Logs/Logs-09-02-2020',
            ['{"goodbye": "json"}\n', '{"hello": "json"}\n'],
        )

    def test_fix_json_logs_append(self):
        retcode = self.call_lfixer('--overwrite')
        self.assertFalse(retcode)
        # Remove progress
        os.unlink(self._progress_db_location[1])
        retcode = self.call_lfixer()
        self.assertFalse(retcode)
        # Output was written twice
        self.assert_file_lines_equal(
            'Logs/Logs-08-02-2020',
            ['{"json": "world"}\n', '{"field": "value"}\n'] * 2,
        )
        self.assert_file_lines_equal(
            'Logs/Logs-09-02-2020',
            ['{"goodbye": "json"}\n', '{"hello": "json"}\n'] * 2,
        )

    @unittest.skipUnless(
        inotify,
        'This test runs only on systems with '
        ' python3-inotify installed')
    def test_kill_continue_progress(self):
        i = inotify.adapters.Inotify()

        i.add_watch(self._testlogdir)
        threading.Thread(
            target=functools.partial(self.call_lfixer,
                                     '--progress-fsync=1',
                                     '--log-fsync=1')).start()

        for event in i.event_gen(yield_nones=False):
            # Wait until first file has been written.
            if 'IN_CLOSE_WRITE' in event[1]:
                # Received first modify event
                self.kill_lfixer()
                self.e.wait()
                break

        # Run one more time.
        retcode = self.call_lfixer()
        self.assertFalse(retcode)
        # Output was written in full.
        self.assert_file_lines_equal(
            'Logs/Logs-08-02-2020',
            ['{"json": "world"}\n', '{"field": "value"}\n'],
        )
        self.assert_file_lines_equal(
            'Logs/Logs-09-02-2020',
            ['{"goodbye": "json"}\n', '{"hello": "json"}\n'],
        )


if __name__ == '__main__':
    if inotify is None:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                               '--user', 'inotify'])
        subprocess.check_call([sys.executable, '-m', 'lfixer.test'])
    else:
        unittest.main()
