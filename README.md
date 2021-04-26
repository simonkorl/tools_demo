# tools_demo

辅助 AItransDTP 进行测试的工具目录

## 快速上手

在上手之前，请准备好 AItransDTP 中规定格式的 block_trace 以及 network_trace 文件。具体格式可见附录。

1. 运行`make baseline_dtp`，如果命令行最后一行显示类似`qoe: 639.099999`的结果则说明命令运行成功。
2. 可以测试运行`make baseline_tcp`、`make baseline_space`来测试不同的协议版本的运行情况
3. 打开 Makefile ，查看`NETWORK_S`、`NETWORK_C`、`BLOCK`变量的值，并且进行修改配置为准备好的文件路径。运行`make network`测试非对称带宽。
3. 运行`make baseline TYPE=0`得到测试用 baseline。改变 TYPE 变量的值即可运行对应的协议生成 baseline 。在`baseline_bk`目录下找到生成的结果目录
4. 打开 baseline.py ，根据 [baseline 测试](#baseline-测试) 一节的内容修改 baseline 的测试值，并且重复上述步骤生成 baseline

## 指令说明

* `make baseline_tcp` | `make baseline_dtp` | `make baseline_space`：利用**本地的镜像**进行 baseline 测试。默认名称为 simonkorl0228/qoe_test_image。如果本地没有对应的镜像，请从 dockerhub 上进行下载。得到的结果会在`baselines_bk`目录下的最新的目录中
* `make network`：可以进行一次非对称信道运行测试。不会生成测试 baseline 目录。
* `make retest`：通过给定环境参数 TESTID ，将其为`baselines_bk`目录中对应目录的`t`开头的字符串，即可进行重新测试。可以通过给定 RTIME 环境变量来改变 client 结束后等待 server 的时间。默认值为 3
* `make copy`：将所有的测试数据复制到`~/baseline_data_process`目录中
* `make parse`：对`baselines_bk`中的每一个目录进行数据解析，每个目录生成一个与目录同名的 csv 文件

## 更新说明 1.0.0

### baseline.py

baseline.py 基于 main.py 设计，提供了更加丰富的测试方式。

#### 非对称带宽模拟

baseline.py 允许分别对 server 和 client 端进行网络限速。

`--network_s`可以用来指定服务端的网络限速文件，`--network_c`则可以用来指定客户端的网络限速文件。使用方法和 main.py 的`--network`参数相同

举例：`python baseline.py --server_name aitrans-server --client_name aitrans-client --network_s ./network_s.txt --network_c ./network_c.txt --type 0`

#### baseline 测试

baseline 测试指的是**利用当前已经生成的容器**，根据指定的若干组参数分别进行测试的过程。目前如果希望使用多个不同的参数只能在 baseline.py 的文件中直接修改。在文件的一开头你会看到如下代码

```python
S_BWS = [100, 42] # Mbps
RTTS = [600, 800] # ms
LOSSES = [0.01]
C_BWS = [0.1, 0.05] #Mbps
```

通过修改其中的值就可以改变测试 baseline 时的网络参数。其中 S_BWS 代表服务端的带宽，C_BWS 代表客户端的带宽，这两个数组中的值是一一对应的，也就是说每一个服务端的带宽的值需要对应一个对应的客户端的带宽的值。除此之外，所有的参数都是相互组合的，也就是说如果有`len(S_BWS) == 2 && len(RTTS) == 2 && len(LOSSES) == 2`，那么就会有 2 * 2 * 2，一共八组不同的实验数据。

在每次测试的时候，请务必添加本次测试时使用的程序的类型，0 代表 aitrans-dtp, 1 代表 TCP , 2 代表 dtp-space （正在开发中）

你也可以通过使用参数来指定某个参数的值，这个值会是唯一的:

* `--loss` 指定唯一的 loss rate，[0, 1]
* `--rtt` 指定唯一的 rtt （ms）

完成了上述的参数指定后，提供 `--baselines` 参数，运行类似下方的指令：

```bash
python baseline.py --type 2 --server_name aitrans-server --client_name aitrans-client --baselines
```

即可进行 baseline 测试。

baseline 测试的结果会被保存到 baseline_bk 目录下

##### baseline 的解析

运行完一次测试之后，会在`baseline_bk`目录下生成一个`t`开头的目录，代表本次 baseline 测试。目录下的 config.json 代表了本次实验所利用的数值。之后可以运行`python data_process.py`命令，将本次测试得到的实验结果解析为 .csv 文件，生成位置为本次实验的目录(`t`开头的目录)。

在这个过程中会同时生成一个名为`server_error.log`的文件，这里面的每一行都代表了 server 在某个网络参数下运行的时候并没有正常退出，这使得 server 生成的 log 文件无法解析。你可以通过`python baseline.py --retest t1241141 --rtime 10`这样的命令，使用`--retest`参数指定需要重跑测试的目录名，`--rtime`参数可以改变从 client 结束运行到 server 结束运行的时间，一般来说如果设置得比较大可以让 server 得到正常的 log 。

## 附录

### block_trace 文件格式

| Time(s)  | Deadline(ms) | Block size(Bytes) | Priority |
| -------- | ------------ | ----------------- | -------- |
| 0.0      | 200          | 8295              | 2        |
| 0.021333 | 200          | 2560              | 1        |
| ……       | ……           | ……                | ……       |

- time : 该block的创建时间与上一个block的创建时间之差；
- Deadline ： 该block的有效时间；
- Block size ： 该block的总大小；
- Priority ： 该block的优先级。数字越小优先级越高

示例如下:

```txt
0.0 200 8295 2
0.021333 200 2560 1
```
### network_trace 文件格式

| Time(s)  | Bandwidth (Mbps) | Loss rate | Latency (s)|
| -------- | ------------ | ----------------- | -------- |
| 0      | 1.986697198821283         | 0.1              | 0.001        |
|4|7.885867347821831|0.01|0.001|
| ……       | ……           | ……                | ……       |

要求的 net trace 的格式为类似`0,1.986697198821283,0.1,0.001`格式的若干行文本文件。用逗号隔开的数字分别表示：

1. 开始秒数(s)
2. 带宽(MB)
3. 丢包率
4. 延迟(s)

示例如下：

```txt
0,1.986697198821283,0.01,0.001
1,1.986697198821283,0.01,0.001
2,1.986697198821283,0.01,0.001
3,1.986697198821283,0.01,0.001
4,7.885867347821831,0.01,0.001
5,7.885867347821831,0.01,0.001
6,7.885867347821831,0.01,0.001
7,7.885867347821831,0.01,0.001
8,7.885867347821831,0.01,0.001
9,9.217531006413294,0.01,0.001
10,9.217531006413294,0.01,0.001
```