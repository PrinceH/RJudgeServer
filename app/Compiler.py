import os
import shutil


class CompilerException(Exception):
    def __init__(self, message, reason=""):
        super().__init__()
        self.message = message
        self.reason = reason

    def __str__(self):
        return self.message


class Compiler:
    def __init__(self, compile_config, src, submission_id):
        self._compile_config = compile_config
        self._src = src
        self._submission = submission_id
        self._submission_path = os.path.join(os.getcwd(), "submissions")
        self._submission_id_path = os.path.join(self._submission_path, submission_id)
        self._exe_path = os.path.join(self._submission_id_path, self._compile_config["exe_name"])
        self._src_path = os.path.join(self._submission_id_path, self._compile_config["src_name"])
        self._command = self._compile_config["compile_command"].format(src_path=self._src_path,
                                                                       exe_dir=self._submission_path,
                                                                       exe_path=self._exe_path)
        if not os.path.exists(self._submission_path):
            os.mkdir(self._submission_path)
        if not os.path.exists(self._submission_id_path):
            os.mkdir(self._submission_id_path)
        with open(self._src_path, "w") as file:
            file.write(self._src)

    def __del__(self):
        shutil.rmtree(self._submission_id_path)

    def _run(self):
        max_compile_time = int(self._compile_config["max_compile_time"] / 1000)
        code = os.system(
            "timeout {} ".format(max_compile_time) + self._command + " 2> " + os.path.join(self._submission_id_path,
                                                                                           "error.log"))
        with open(os.path.join(self._submission_id_path, "error.log"), "r") as error:
            error_content = error.read()
            error_content = error_content.replace(self._submission_id_path, "")
        if code:
            raise CompilerException("Compile error", error_content)


if __name__ == "__main__":
    cpp_lang_config = {
        "compile": {
            "src_name": "main.cpp",
            "exe_name": "main",
            "max_compile_time": 3000,
            "max_memory": 128 * 1024 * 1024,
            "compile_command": "/usr/bin/g++ -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c++11 {src_path} -lm -o {exe_path}",
        },
        "run": {
            "command": "{exe_path}",
            "seccomp_rule": "c_cpp",
        }
    }
    cpp_src = r"""
         # include<bits/stdc++.h>
        using
        namespace
        std;

        int
        main()
        {
        // ios::sync_with_stdio(false);
        double
        a, ans, temp
        long
        long
        k;
        while (scanf("%lf%lld", & a,& k)){
        ans = 0;
        for (int i = 1; i <= k; i ++){
        ans += a;
        a /= 2;
        if (a < 0.001)
        break;
        temp = a;
        if (i != k)ans += a;
    }
    printf("%.1f %.1f\n", ans, temp);
    }
    return 0;
    }"""
    compiler = Compiler(compile_config=cpp_lang_config["compile"], src=cpp_src, submission_id="abc")
    try:
        compiler._run()
    except CompilerException as e:
        print(e.message)
