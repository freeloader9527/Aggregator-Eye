# Aggregator-Eye

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

Aggregator-Eye 是一个基于 ZoomEye Aggregation Search 的企业资产聚合检索工具。

它的使用方式很直接：把公司名称批量导入系统，工具会自动调用 ZoomEye 聚合接口，返回网页标题、应用组件、网络节点等结果，再在本地界面中进行二次筛选和导出。这个项目更适合用来做目标初筛、资产摸排和 CNVD 相关目标发现。

## 功能

- 批量导入公司名称，自动执行聚合搜索
- 支持网页标题、应用组件、网络节点三种维度
- 内置噪音词过滤和匹配规则
- 支持本地二次筛选
- 支持导出 XLSX / CSV
- 支持导入离线结果继续分析

## 界面

### 1. 首页总览

<img width="1920" height="979" alt="image" src="https://github.com/user-attachments/assets/1a000a73-215a-4cf4-9868-bcf7083cc596" />

### 2. 结果筛选 / 导出结果

<img width="1920" height="979" alt="image" src="https://github.com/user-attachments/assets/f1540cdd-c9f4-49cd-a2cf-761a72754a2b" />

## 技术栈

- Backend: Flask, Flask-SocketIO, Requests, Pandas
- Frontend: Vue 3, Socket.IO
- Auth: Playwright

## 使用流程

1. 准备一个文本、CSV 或 Excel 文件，第一列放公司名称。
2. 启动项目并登录 ZoomEye。
3. 在页面中导入公司名称列表。
4. 选择需要的搜索维度：
   - `title`：网页标题
   - `product`：应用组件
   - `device`：网络节点
5. 查看聚合结果并在页面内继续过滤。
6. 导出结果或导入已有离线结果继续分析。

## 安装

```bash
git clone https://github.com/freeloader9527/Aggregator-Eye.git
cd Aggregator-Eye
pip install -r requirements.txt
playwright install chromium
```

## 配置

推荐使用环境变量提供 ZoomEye 账号。

PowerShell:

```powershell
$env:ZOOMEYE_USERNAME="your_zoomeye_email"
$env:ZOOMEYE_PASSWORD="your_zoomeye_password"
```

项目中的 [config.py](config.py) 会自动读取这两个环境变量。

如果你想了解可调参数，可以参考 [config.example.py](config.example.py)。

## 启动

```bash
python app.py
```

打开 `http://127.0.0.1:5000`

## 输入文件格式

- `.txt`：每行一个公司名称
- `.csv` / `.xlsx`：默认读取第一列作为公司名称

示例：

```text
奇安信科技集团股份有限公司
深圳市腾讯计算机系统有限公司
```

## 匹配规则说明

项目支持简单的逻辑匹配，不是完整正则引擎。

- `foo`：包含 `foo`
- `foo&&bar`：同时包含 `foo` 和 `bar`
- `foo||bar`：包含 `foo` 或 `bar`
- `!(foo)`：排除包含 `foo`

相关配置项：

- `NOISE_WORDS`：噪音词过滤
- `MATCH_RULES`：命中规则
- `LIMIT`：单次聚合返回上限

## 目录说明

```text
Aggregator-Eye/
├─ app.py
├─ auth.py
├─ scanner.py
├─ utils.py
├─ config.py
├─ config.example.py
├─ templates/
├─ img/
└─ results/
```

`results/` 目录默认只保留空目录结构，不建议把运行结果提交到 GitHub。

## 注意事项

- 首次运行需要安装 Playwright 的 Chromium。
- 登录流程依赖 ZoomEye 当前页面结构，若官方页面改版，认证流程可能需要调整。
- 请只在合法授权场景下使用。

## 免责声明

本项目仅用于合法的安全研究、资产识别和授权测试。使用者应自行遵守当地法律法规与目标系统授权要求。
