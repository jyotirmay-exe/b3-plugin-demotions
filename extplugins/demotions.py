import b3
import b3.plugin
from b3.clients import Group
from datetime import datetime
import urllib2
import json

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
    def __init__(self,client,admin,sname,currLevel,url):
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
        self.display_message = str(self.config.get("messages","display_message"))
        self.private_message = str(self.config.get("messages","private_message"))
        self.notAdmin_message = str(self.config.get("messages","notAdmin_message"))
        self.higherAdmin_message = str(self.config.get("messages","higherAdmin_message"))
        self.minLevel = int(self.config.get("settings","minLevel"))
        self.webhookURL = str(self.config.get("settings","webhookURL"))
        self.debug("config settings and messages loaded normal.")

    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.debug('Could not find admin plugin')
            return False
        else:
            self.debug('Plugin loaded normal')
        self._adminPlugin.registerCommand(self, "demote", self.minLevel, self.cmd_demote,alias="d")
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
      
    def updateTable(self,client_id,admin_id):
        try:
            insQuery = "insert into demotions (client_id,admin_id,time_add,time_edit) values (%s,%s,unix_timestamp(),unix_timestamp());"
            updQuery = "update demotions set count=%s,admin_id=%s,time_edit=unix_timestamp() where client_id=%s";

            rows = self.console.storage._query("select * from demotions where client_id = %s;"%(client_id)).getRow()
            self.debug(rows)

            if rows == {}:
                self.console.storage._query(insQuery%(client_id,admin_id))

            if rows != {}:
                count = rows["count"]+1
                self.console.storage._query(updQuery%(count,admin_id,client_id))
        except Exception as ex:
            self.debug(ex)
  
    def demote(self,client,admin,client_id,admin_id,cmd=None):
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
        self.updateTable(client_id,admin_id)
        self.debug("added/updated demotion entry for client_id @%s and admin_id @%s"%(client_id,admin_id))
        if not client.cid==None:
            client.message(self.private_message)
        else:
            self.debug("not sending pm cuz client is not online")
        #webhooooooooooooooook
        row = self.console.storage._query("select * from current_svars where name = \"sv_hostname\";").getRow()
        sname = self.console.stripColors(row["value"])
        webhook = Webhook(client,admin,sname,currLevel,self.webhookURL)
        webhook.push()


    def cmd_demote(self,data,client,cmd=None):
        """\
        <player> - demote a player to ^2Regular ^7[^32^7]
        """
        if not data:
            client.message("Invalid Parameters")
            return
        inp = self._adminPlugin.parseUserCmd(data)
        admin = client
        client2 = self._adminPlugin.findClientPrompt(inp[0],client)
        if not client2:
            return
        if admin.id == client2.id:
            admin.message("Can't demote yourself.")
            return
        self.demote(client=client2,admin=admin,client_id=client2.id,admin_id=admin.id,cmd=cmd)