joinMOTD
---------
這Fork原作來自 [TISUnion/joinMOTD](https://github.com/TISUnion/joinMOTD) ，原作者為Fallen_Breath  
修改者為：Eric_Yang, a3510377, shane0411

一個 MCDReforged 插件，需要 MCDR > 2.0  
主要功能如下：
1. **歡迎訊息（MOTD）**：
	- 當玩家加入伺服器時，顯示自訂的歡迎訊息，包括伺服器名稱、開服天數、伺服器列表等。

2. **伺服器列表**：
	- 支援多伺服器資訊顯示，分類展示，並可點擊快速切換伺服器。

3. **上次加入時間查詢**：
	- 玩家可查詢自己或指定玩家距離上次加入伺服器的天數。
	- 支援指令查詢單一玩家（get）、玩家列表分頁顯示（list）、幫助說明（help）。

4. **活躍度顏色標示**：
	- 根據玩家距離上次上線天數，顯示不同顏色（綠/黃/紅/灰）以反映活躍度。

5. **忽略名單**：
	- 可設定正則表達式，自動忽略特定機器人或不需統計的玩家。

6. **數據儲存與載入**：
	- 自動儲存/讀取玩家上次加入時間，並支援多種天數計算來源（自訂、外部插件、daycount模組）。

7. **多執行緒支援**：
	- 部分查詢操作在新執行緒中執行，避免阻塞主線程。


---
當玩家加入遊戲時向其發送歡迎訊息

需要填写配置文件 `config/joinMOTD.json`

如果配置文件中指定了 `start_day`（格式：`%Y-%m-%d`，如 `2018-11-09`），則將使用 `start_day` 計算開服時間，否則將嘗試導入 daycount 插件進行開服時間獲取

-----

A MCDReforged plugin, requires MCDR > 2.0

Send player a MOTD when he joins

Don't forget to fill configure file `config/joinMOTD.json`

If `start_day` (format: `%Y-%m-%d`, e.g. `2018-11-09`) is specified in the config file, `start_day` will be used to calculate the start time, otherwise it will try to import the daycount plugin to get the start time
