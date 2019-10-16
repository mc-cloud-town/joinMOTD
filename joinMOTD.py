# -*- coding: utf-8 -*-

from daycount import getday
import json

subserverNameListPath = 'plugins/joinMOTD/setting.json'

def tellMessage(server, player, msg):
  for line in msg.splitlines():
    server.tell(player, line)

def getJumpCommand(subserverName):
  return '{"text":"[' + subserverName + ']",\
"clickEvent":{"action":"run_command",\
"value":"/server ' + subserverName + '"}}'

def onPlayerJoin(server, player):
  cmd = 'tellraw ' + player + ' {"text":"","extra":['
  with open(subserverNameListPath, 'r') as f:
    js = json.load(f)
    servername = str(js["serverName"])
    lines = js["serverList"]
    
    for i in range(len(lines)):
      name = lines[i].replace('\n', '').replace('\r', '')
      cmd = cmd + getJumpCommand(name)
      if i != len(lines) - 1:
        cmd = cmd + ',{"text":" "},'

# print all stuffs
  cmd = cmd + ']}'
  msg = '''§7==========§r Welcome back to §e''' + servername + ''' §7==========§r
今天是§e''' + servername + '''§r开服的第§e''' + getday() + '''§r天
§7----------§r Server List §7----------§r'''
  tellMessage(server, player, msg)
  server.execute(cmd)
  
def onServerInfo(server, info):
  if info.content == '!!joinMOTD' and info.isPlayer:
    onPlayerJoin(server, info.player)
