import traceback

import discord
from core.elements import Plain, Image, MessageSession, MsgInfo, Session
from core.bots.discord.client import client


class Template(MessageSession):
    all_func = ("sendMessage", "waitConfirm", "asDisplay", "delete", "checkPermission", "Typing")

    async def sendMessage(self, msgchain, Quote=True):
        if isinstance(msgchain, str):
            if msgchain == '':
                msgchain = '发生错误：机器人尝试发送空文本消息，请联系机器人开发者解决问题。'
            send = await self.session.message.channel.send(msgchain, reference=self.session.message if Quote else None)
            return MessageSession(target=MsgInfo(targetId=0, senderId=0, senderName='', targetFrom='Discord|Bot', senderFrom='Discord|Bot'),
                                  session=Session(message=send, target=send.channel, sender=send.author))
        if isinstance(msgchain, list):
            count = 0
            send_list = []
            for x in msgchain:
                if isinstance(x, Plain):
                    send = await self.session.message.channel.send(x.text, reference=self.session.message if Quote and count == 0 else None)
                if isinstance(x, Image):
                    send = await self.session.message.channel.send(file=discord.File(x.image), reference=self.session.message if Quote and count == 0 else None)
                send_list.append(send)
                count += 1
            return MessageSession(target=MsgInfo(targetId=0, senderId=0, senderName='', targetFrom='Discord|Bot', senderFrom='Discord|Bot'),
                                  session=Session(message=send_list, target=send.channel, sender=send.author))

    async def waitConfirm(self):
        confirm_command = ["是", "对", '确定', '是吧', '大概是',
                           '也许', '可能', '对的', '是呢', '对呢', '嗯', '嗯呢',
                           '吼啊', '资瓷', '是呗', '也许吧', '对呗', '应该',
                           'yes', 'y', 'yeah', 'yep', 'ok', 'okay', '⭐', '√']

        def check(m):
            return m.channel == self.session.message.channel and m.author == self.session.message.author

        msg = await client.wait_for('message', check=check)
        return True if msg.content in confirm_command else False

    def checkPermission(self):
        if self.session.message.channel.permissions_for(self.session.message.author).administrator\
                or isinstance(self.session.message.channel, discord.DMChannel)\
                or self.target.senderInfo.query.isSuperUser \
                or self.target.senderInfo.check_TargetAdmin(self.target.targetId):
            return True
        return False

    def asDisplay(self):
        return self.session.message.content

    async def delete(self):
        try:
            if isinstance(self.session.message, list):
                for x in self.session.message:
                    await x.delete()
            else:
                await self.session.message.delete()
        except:
            traceback.print_exc()

    class Typing:
        def __init__(self, msg: MessageSession):
            self.msg = msg

        async def __aenter__(self):
            async with self.msg.session.message.channel.typing() as typing:
                return typing

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass