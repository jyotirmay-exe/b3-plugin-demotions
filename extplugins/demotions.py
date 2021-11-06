import b3
import b3.plugin
from b3.clients import Group
from datetime import datetime
import urllib2
import json
import re

query="""
CREATE TABLE `demotions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL,
  `admin_id` int(11) NOT NULL,
  `count` int(11) NOT NULL DEFAULT '1',
  `inactive` tinyint(4) NOT NULL DEFAULT '0',
  `time_add` int(11) NOT NULL,
  `time_edit` int(11) NOT NULL DEFAULT '0',
  `reason` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`),
  UNIQUE KEY `client_id` (`client_id`)
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
"""
__author__=__version__=None

pluginInstance = None

class Webhook():
    def __init__(self,client,admin,sname,currLevel,reason,url):
        global pluginInstance
        self.webhook_url = url
        self.embed  = {
            "title": "B3 Demotion!",
            "description": '**%s [@%s]** was demoted for the **%s** time\nAdmin: **%s [@%s]**' % (client.name,client.id,self.ordinal(self.getCount(client.id)),admin.name,admin.id),
            "fields":[
                {
                    "name":"**Previous Level**",
                    "value":"%s"%currLevel,
                    "inline":True
                },
                {
                    "name":"**Server**",
                    "value":"%s"%sname,
                    "inline":True
                },
                {
                    "name":"**Reason**",
                    "value":"%s"%reason
                },
                {
                    "name":"**Time**",
                    "value":"%s"%datetime.now().strftime("%d/%m/%y %H:%M:%S")
                }
            ],
            "color": 36677
        }

    def getCount(self,cid):
        return int(pluginInstance.console.storage._query("select * from demotions where client_id=%s;"%(cid)).getRow()["count"])

    def ordinal(self,num):
        num = num
        n = int(num)
        if 4 <= n <= 20:
            suffix = 'th'
        elif n == 1 or (n % 10) == 1:
            suffix = 'st'
        elif n == 2 or (n % 10) == 2:
            suffix = 'nd'
        elif n == 3 or (n % 10) == 3:
            suffix = 'rd'
        elif n < 100:
            suffix = 'th'
        ord_num = str(n) + suffix
        return ord_num

    def push(self):
        global pluginInstance
        data = json.dumps({"embeds": [self.embed]})
        req = urllib2.Request(self.webhook_url, data, {
            'Content-Type': 'application/json',
            "User-Agent": "webhoooooooooooooooooooooook"
        })

        try:
            urllib2.urlopen(req)
            pluginInstance.debug("webhook pushed to discord")
        except urllib2.HTTPError as ex:
            pluginInstance.debug("error pushing embed to discord. may be invalid url or bad json data.")
            pluginInstance.debug("Data: %s\nCode: %s\nRead: %s" % (data, ex.code, ex.read()))

class DemotionsPlugin(b3.plugin.Plugin):

    requiresConfigFile = True

    def onLoadConfig(self):
        self.debug("loading config..")
        self.autoCreate = int(self.config.get("settings","autoCreate"))
        self.new_putgroup = int(self.config.get("settings","new_putgroup"))
        self.display_message = str(self.config.get("messages","display_message"))
        self.private_message = str(self.config.get("messages","private_message"))
        self.notAdmin_message = str(self.config.get("messages","notAdmin_message"))
        self.higherAdmin_message = str(self.config.get("messages","higherAdmin_message"))
        self.minLevelD = int(self.config.get("settings","minLevelD"))
        self.minLevelDT = int(self.config.get("settings","minLevelDT"))
        self.minLevelPG = int(self.config.get("settings","minLevelPG"))
        self.no_reason_level = int(self.config.get("settings","no_reason_level"))
        self.webhookURL = str(self.config.get("settings","webhookURL"))
        self.debug("config settings and messages loaded normal.")

    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.debug('Could not find admin plugin')
            return False
        else:
            self.debug('Plugin loaded normal')
        self._adminPlugin.registerCommand(self, "demote", self.minLevelD, self.cmd_demote,alias="d")
        self._adminPlugin.registerCommand(self, "putgroup", self.minLevelDT, self.cmd_putgroup, alias="pg")
        self._adminPlugin.registerCommand(self, "demotiontest", self.minLevelPG, self.cmd_demotiontest, alias="dt")
        global pluginInstance
        
        pluginInstance = self
        try:
            self.console.storage._query("select * from demotions;")
            self.debug("located demotions table.")
        except Exception as ex:
            self.debug("Error loading demotions table: %s"%ex)
            if self.autoCreate==1:
                global query
                self.console.storage._query(query)
                self.debug("create table demotions as it didn't exist")
      
    def updateTable(self,client_id,admin_id,reason):
        insQuery = "insert into demotions (client_id,admin_id,time_add,time_edit,reason) values (%s,%s,unix_timestamp(),unix_timestamp(),\"%s\");"
        updQuery = "update demotions set count=%s,admin_id=%s,inactive=0,time_edit=unix_timestamp(),reason=\"%s\" where client_id=%s";

        rows = self.console.storage._query("select * from demotions where client_id = %s;"%(client_id)).getRow()
        self.debug(rows)

        if rows == {}:
            self.console.storage._query(insQuery%(client_id,admin_id,reason))

        if rows != {}:
            count = rows["count"]+1
            self.console.storage._query(updQuery%(count,admin_id,reason,client_id))
  
    def demote(self,client,admin,client_id,admin_id,reason,cmd=None):
        client_row = self.console.storage._query("select * from clients where id = %s;"%client_id).getRow()
        admin_row = self.console.storage._query("select * from clients where id = %s"%admin_id).getRow()

        if client.maxLevel < 20:
            cmd.sayLoudOrPM(admin,self.notAdmin_message)
            return
        
        if admin.maxLevel < client.maxLevel:
            cmd.sayLoudOrPM(admin,self.higherAdmin_message.format(client=client_row["name"]))
            return
        # self.console.storage._query("update clients set group_bits=2 where id = %s;"%client_id).getRow()
        group = Group(keyword="reg")
        group = self.console.storage.getGroup(group)
        currLevel = client.maxLevel
        client.setGroup(group)
        client.save()
        self.debug("updated level of @%s to regular"%client_id)
        self.console.say(self.display_message.format(client=client.name,admin=admin.name))
        self.updateTable(client_id,admin_id,reason)
        self.debug("added/updated demotion entry for client_id @%s and admin_id @%s"%(client_id,admin_id))
        if not client.cid==None:
            client.message(self.private_message)
        else:
            self.debug("not sending pm cuz client is not online")
        #webhooooooooooooooook
        row = self.console.storage._query("select * from current_svars where name = \"sv_hostname\";").getRow()
        sname = self.console.stripColors(row["value"])
        webhook = Webhook(client,admin,sname,currLevel,reason,self.webhookURL)
        webhook.push()


    def cmd_demote(self,data,client,cmd=None):
        """\
        <player> - demote a player to ^2Regular ^7[^32^7]
        """
        if not data:
            client.message("Invalid Parameters")
            return
        cid, reason = self._adminPlugin.parseUserCmd(data)
        admin = client
        if not reason and admin.maxLevel < self.no_reason_level:
            admin.message("^1ERROR: ^7You must supply a reason")
            return
        if not reason:
            reason = "no reason given"
        client2 = self._adminPlugin.findClientPrompt(cid,client)
        if not client2:
            return
        if admin.id == client2.id:
            admin.message("Can't demote yourself.")
            return
        self.demote(client=client2,admin=admin,client_id=client2.id,admin_id=admin.id,reason=reason,cmd=cmd)

    def isDemoted(self,client):
        res = self.console.storage._query("select * from demotions where client_id = %s;"%client.id).getRow()
        if res == {}:
            return False
        else:
            if res["inactive"]==1:
                return False
            else:
                return True

    def cmd_putgroup(self,data,client,cmd=None):
        """\
        <client> <group> - add a client to a group
        """
        m = re.match('^(.{2,}) ([a-z0-9]+)$', data, re.I)
        if not m:
            client.message('^7Invalid parameters')
            return False

        cid, keyword = m.groups()

        try:
            group = Group(keyword=keyword)
            group = self.console.storage.getGroup(group)
        except:
            client.message('^7Group %s does not exist' % keyword)
            return False

        if group.level >= client.maxLevel and client.maxLevel < 100:
            client.message('^7Group %s is beyond your reach' % group.name)
            return False

        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if sclient:
            if sclient.inGroup(group):
                client.message("^7%s^7 is already in group %s"%(sclient.exactName,group.name))
                # client.message(self.getMessage('groups_already_in', sclient.exactName, group.name))
            else:
                if self.isDemoted(sclient):
                    self.console.storage._query("update demotions set inactive=1 where client_id=%s;"%sclient.id)
                sclient.setGroup(group)
                sclient.save()
                cmd.sayLoudOrPM(client,"^7%s ^7put in group %s"%(sclient.exactName,group.name))
                # cmd.sayLoudOrPM(client, self.getMessage('groups_put', sclient.exactName, group.name))
                return True
    def cmd_demotiontest(self,data,client,cmd=None):
        if not data:
            client.message("Incorrect command syntax")
            return
        inp = self._adminPlugin.parseUserCmd(data)
        client2 = self._adminPlugin.findClientPrompt(inp[0],client)
        if not client2:
            return
        res = self.console.storage._query("select * from demotions where client_id=%s;"%client2.id).getRow()
        if res=={}:
            cmd.sayLoudOrPM(client,"No demotion found for player %s"%client2.exactName)
        else:
            statuses = {1:"^2Inactive",0:"^1Active"}
            msg = "^3%s^7 was demoted by ^7%s^7 on ^0%s^7. Currently : %s"
            admin = str(self.console.storage._query("select * from clients where id=%s;"%res["admin_id"]).getRow()["name"])+" ^7[^3@%s^7]"%res["admin_id"]
            status = statuses[res["inactive"]]
            cmd.sayLoudOrPM(client,msg%(client2.exactName,admin,(datetime.fromtimestamp(int(res["time_edit"]))).strftime("%d/%m/%y %H:%M"),status))