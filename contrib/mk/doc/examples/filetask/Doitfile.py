from doitlib.task import Task

class answer(Task):
    default = True
    deps = ["one.txt", "two.txt"]
    outputs = ["answer.txt"]
    def doit(self):
        answer = 0
        for dep in self.deps:
            answer += int(open(dep).read().strip())
        self.log.info("answer is %r" % answer)
        open(self.outputs[0], 'w').write(answer)


