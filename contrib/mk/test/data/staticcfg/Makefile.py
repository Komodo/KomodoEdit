
from mklib import Task, File, Configuration
from mklib.sh import run, run_in_dir, rm, mkdir


class cfg(Configuration):
    pass

class hello(Task):
    def make(self):
        self.log.info("cfg is %r", self.cfg)
        self.log.info("cfg foo=%r", self.cfg.foo)
