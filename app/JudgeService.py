# -*- coding: utf-8 -*-
import _judger
import hashlib
import json
import os
import shutil
import psutil
import glob
from multiprocessing import Pool
from Compiler import Compiler
from Compiler import CompilerException
import requests
import zipfile
import sys
from Constants.ResultCode import ResultCode
from Constants.JudgeResult import JudgeResult
SERVER_URL = os.environ.get("SERVER_URL")
class JudgeServiceException(Exception):
    def __init__(self, message,reason=""):
        super().__init__()
        self.message = message
        self.reason = reason

    def __str__(self):
        return self.message


def read_file_content(path):
    with open(path,'r',encoding='utf-8', errors="ignore") as file:
        return file.read()


def _generate_output_sha256(output_content):
    stripped_output_content = output_content.replace("\n", "").replace(" ", "")
    return hashlib.sha256(output_content.encode("utf-8")).hexdigest(), hashlib.sha256(
        stripped_output_content.encode("utf-8")).hexdigest()


def run(judger, id):
    return judger._once(id)


class JudgeService:
    def __init__(self, language_config, test_case_id, submission_id, src, max_cpu_time, max_memory,is_spj = False):
        self._src = src
        self._max_cpu_time = max_cpu_time
        self._test_case_id = str(test_case_id)
        self._submission_id = str(submission_id)
        self._test_case_path = os.path.join(os.getcwd(), "test_cases")
        self._submission_path = os.path.join(os.getcwd(), "submissions")
        self._submission_id_path = os.path.join(self._submission_path, self._submission_id)
        self._test_case_id_path = os.path.join(self._test_case_path, self._test_case_id)
        self._language_config = language_config
        self._max_memory = max_memory
        self._is_spj = is_spj
        self._spj_path = os.path.join(self._test_case_id_path,'spj.cpp')
        self._exe_path = os.path.join(self._submission_id_path, self._language_config["compile"]["exe_name"])
        self._pool = Pool(min(processes=psutil.cpu_count(),4))
        self._command = self._language_config["run"]["command"].format(exe_path=self._exe_path,
                                                                       exe_dir=os.path.dirname(self._exe_path),
                                                                       max_memory=int(self._max_memory / 1024)).split(" ")
        if not os.path.exists(self._test_case_path):
            os.mkdir(self._test_case_path)
        if not os.path.exists(self._submission_path):
            os.mkdir(self._submission_path)

    def _generate_test_case_info(self):
        info = {"test_cases": {}}
        index = 0
        for input_file in glob.glob(os.path.join(self._test_case_id_path, "*.in")):
            output_file = input_file.replace(".in", ".out")
            if not os.path.exists(output_file):
                raise JudgeServiceException(message="[ERROR] Missing test samples")
            input_content = read_file_content(path=input_file)
            output_content = read_file_content(path=output_file)
            output_sha256_data = _generate_output_sha256(output_content)
            item_info = {"input_name": os.path.basename(input_file), "input_size": len(input_content),
                         "output_name": os.path.basename(output_file), "output_size": len(output_content),
                         "output_sha256": output_sha256_data[0],
                         "stripped_output_sha256": output_sha256_data[1],
                         "test_case_name": input_file.replace(self._test_case_id_path + '/', "").replace(".in","")
                         }
            info["test_cases"][index] = item_info
            index += 1
        info["test_case_number"] = index
        if index == 0:
            raise JudgeServiceException(message="[ERROR] The number of test samples is zero")
        return info

    def _generate_judge_result(self,run_result,user_output_path,test_case_info):
        result = {}
        status = ret = ResultCode.Accepted
        user_output_content = read_file_content(user_output_path)
        user_output_content = user_output_content
        user_output_size = sys.getsizeof(user_output_content)
        user_output_sha256,user_stripped_output_sha256 = _generate_output_sha256(user_output_content)
        if not self._is_spj and run_result["result"] == JudgeResult.SUCCESS:
            if user_output_sha256 != test_case_info["output_sha256"] and user_stripped_output_sha256 != test_case_info["stripped_output_sha256"]:
                status = ret = ResultCode.WRONG_ANSWER
            elif user_output_sha256 != test_case_info["output_sha256"] and user_stripped_output_sha256 == test_case_info["stripped_output_sha256"]:
                status = ret = ResultCode.PRESENTATION_ERROR
        if run_result["result"] == JudgeResult.MEMORY_LIMIT_EXCEEDED:
            ret = ResultCode.MEMORY_LIMIT_EXCEEDED
        if run_result["result"] == JudgeResult.CPU_TIME_LIMIT_EXCEEDED or run_result["result"] == JudgeResult.REAL_TIME_LIMIT_EXCEEDED:
                ret = ResultCode.TIME_LIMIT_EXCEEDED
        if run_result["result"] == JudgeResult.RUNTIME_ERROR:
            ret = ResultCode.RUNTIME_ERROR
        if user_output_size >= test_case_info["max_output_size"]:
            ret = ResultCode.Output_Limit_Exceeded
        if run_result["result"] == JudgeResult.SYSTEM_ERROR:
            ret = ResultCode.SYSTEM_ERROR

        result["result"] = ret
        if self._is_spj and ret == ResultCode.Accepted:
            code = run_result['code']
            if code == 0:
                ret = ResultCode.Accepted
            if code == 1:
                ret = ResultCode.WRONG_ANSWER
            if code == 255:
                ret = ResultCode.RUNTIME_ERROR
        result['result'] = ret
        result["status"] = status
        result["expected_output_size"] = test_case_info["output_size"]
        result["user_output_size"] = user_output_size
        result["user_output_sha256"] = user_output_sha256
        result["user_stripped_output_sha256"] = user_stripped_output_sha256
        result["expected_output_sha256"] = test_case_info["output_sha256"]
        result["expected_stripped_output_sha256"] = test_case_info["stripped_output_sha256"]
        result["test_case_name"] = test_case_info["test_case_name"]
        result["Judge_Result"] = run_result
        return result
    def _once(self, test_case_id):
        test_case_info = self._test_case_id_info["test_cases"][test_case_id]
        input_path = os.path.join(self._test_case_id_path, test_case_info["input_name"])
        output_path = os.path.join(self._test_case_id_path, test_case_info["output_name"])
        user_output_path = os.path.join(self._submission_path, self._submission_id, test_case_info["output_name"])
        expected_output_content = read_file_content(output_path)
        expected_output_size = sys.getsizeof(expected_output_content)
        max_output_size = max(int(expected_output_size * 2.5), int(16 * 1024 * 1024))
        run_result = _judger.run(
            exe_path=self._command[0],
            input_path=input_path,
            output_path=user_output_path,
            error_path=os.path.join(self._submission_path, self._submission_id,'error.log'),
            max_cpu_time=self._max_cpu_time,
            max_real_time=self._max_cpu_time*60,
            max_memory=self._max_memory,
            args=self._command[1::], env=self._language_config["run"]["env"], log_path=os.path.join(os.getcwd(), "judge.log"),
            max_process_number=-1,
            max_stack=32 * 1024 * 1024,
            max_output_size=max_output_size,
            uid=0, gid=0, seccomp_rule_name=self._language_config["run"]['seccomp_rule'],
            memory_limit_check_only=self._language_config["run"].get("memory_limit_check_only", 0),
        )
        if self._is_spj:
            cmd = "timeout 30 {} {} {} {}".format(self._spj_exe,input_path,output_path,user_output_path)
            code = os.system(cmd) >> 8
            run_result['code'] = code
        test_case_info["max_output_size"] = max_output_size
        test_case_info["expected_output_content"] = expected_output_content
        return self._generate_judge_result(run_result=run_result,user_output_path = user_output_path,test_case_info = test_case_info)

    def _download_latest_test_case(self):
        print("update........")
        zip_path = os.path.join(self._test_case_path, self._test_case_id) + ".zip"
        if os.path.exists(zip_path):
            os.remove(zip_path)
        r = requests.get(url="http://{}/api/test_cases/{}/download".format(SERVER_URL,self._test_case_id))
        if r.status_code == 200:
            with open(zip_path, "wb") as file:
                file.write(r.content)
            zip_file = zipfile.ZipFile(zip_path)
            zip_list = zip_file.namelist()
            if os.path.exists(self._test_case_id_path):
                shutil.rmtree(self._test_case_id_path)
            for _file in zip_list:
                zip_file.extract(_file, self._test_case_id_path)
            zip_file.close()
            os.remove(zip_path)
        else:
            raise JudgeServiceException("UpdateTestCaseFailed",r.__str__())

    def _get_latest_test_case(self):
        # 没有测试样例直接下载
        if not os.path.exists(self._test_case_id_path):
            self._download_latest_test_case()
        try:
            res = json.loads(requests.get(url="http://{}/api/test_cases/{}".format(SERVER_URL,self._test_case_id)).text)
        except requests.RequestException as e:
            raise JudgeServiceException("GetRemoteTestCaseInfoFailed",e.__str__())
        latest_time = res["updated_at"]
        cur_time = os.path.getctime(os.path.join(self._test_case_id_path, "touch"))
        if latest_time - cur_time > 0:
            self._download_latest_test_case()

    def _run(self):
        if os.path.exists(self._submission_id_path) :
            shutil.rmtree(self._submission_id_path)
        compiler = Compiler(
            compile_config=self._language_config["compile"],
            src=self._src,
            submission_id=self._submission_id
        )
        try:
            compiler._run()
        except CompilerException as e:
            return {"error": e.message, "reason": e.reason}
        try:
            self._get_latest_test_case()
            self._test_case_id_info = self._generate_test_case_info()
        except JudgeServiceException as e:
            return {"error": e.message, "reason": e.reason}
        try:
            if self._is_spj:
                cmd = "timeout 10 /usr/bin/g++ -std=c++11 {} -o {} 2> {}".format(self._spj_path,os.path.join(self._submission_id_path,"spj"),os.path.join(self._submission_id_path,'spj_error.log'))
                code = os.system(cmd)
                if code:
                    with open(os.path.join(self._submission_id_path, "spj_error.log"), "r") as error:
                        error_content = error.read()
                        error_content = error_content.replace(self._submission_id_path, "")
                    raise JudgeServiceException("Spj Compile error", error_content)
                self._spj_exe = os.path.join(self._submission_id_path,'spj')
        except JudgeServiceException as e:
            return {"error": e.message, "reason": e.reason}
        tmp_result = []
        result = {}
        for i in range(self._test_case_id_info["test_case_number"]):
            tmp_result.append(self._pool.apply_async(run, (self, i)))
        self._pool.close()
        self._pool.join()
        for item in tmp_result:
            result[item.get()['test_case_name']] = item.get()
        return result

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict["_pool"]
        return self_dict


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
     #include<bits/stdc++.h>
    using
    namespace
    std;

    int
    main()
    {
    // ios::sync_with_stdio(false);
    double
    a, ans, temp;
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
    judger = JudgeService(
        language_config=cpp_lang_config,
        test_case_id="6Lf7h13icaiHMbMtnKIZWGUgh9jzDKap",
        submission_id="1",
        src=cpp_src,
        max_memory=1024 * 1024 * 32,
        max_cpu_time=1000
    )
    with open("./ret.json","w+") as f:
        f.write(json.dumps(judger._run()))
