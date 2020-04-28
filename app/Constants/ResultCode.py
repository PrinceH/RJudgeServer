class ResultCode:
    # 重判
    ReJudge = -3
    # 等待判题中
    Pending = -2
    # 正在判题
    Judging = -1
    # 答案错误
    WRONG_ANSWER = 0
    # 答案正确
    Accepted = 1
    # 部分正确
    Partial_Accepted = 2
    # 格式错误
    PRESENTATION_ERROR = 3
    # cpu超时
    TIME_LIMIT_EXCEEDED = 4
    # 内存超出
    MEMORY_LIMIT_EXCEEDED = 5
    # 输出内容过多
    Output_Limit_Exceeded = 6
    # 运行时错误
    RUNTIME_ERROR = 7
    # 系统错误
    SYSTEM_ERROR = 8
    # 编译错误
    COMPILE_ERROR = 9

