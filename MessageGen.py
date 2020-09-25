import asyncio
import os
import random
import re
from os.path import abspath

import graia.application.interrupt as inter
from graia.application.message.chain import MessageChain
from graia.application.message.elements.internal import Plain, Image, Source, At

from CommandGen import command
from modules.camr import camr
from modules.dfile import dfile
from modules.findimage import findimage

import traceback
async def gen(bcc, app, message, target1, target2='0', msgtype='None'):
    im = inter.InterruptControl(bcc)
    if msgtype == 'Group':
        run = await command(message.asDisplay(), target1.id)
    else:
        run = await command(message.asDisplay())
    #    print(run)
    if run != None:
        print(run)
        msgchain = await makemsgchain(run, msgtype)
        send = await sendmessage(app, msgchain, target1, target2, msgtype,
                                 message[Source][0] if msgtype == 'Group' else 0)
        if msgtype == 'Group':
            voice = re.findall(r'https?://.*?/File:.*?\.(?:ogg|m4a|mp3|flac|wav)', run, re.I)
            for voicelink in voice:
                try:
                    findvoicename = re.match(r'(https?://.*?/)File:(.*?\.(?:ogg|m4a|mp3|flac|wav))', voicelink, re.I)
                    downloadfile = await dfile(findvoicename.group(1), findvoicename.group(2))
                    print(downloadfile)
                    conventamr = await camr(downloadfile)
                    print(conventamr)
                    readfile = open(conventamr, 'rb+')
                    uploadvoice = await app.uploadVoice(readfile.read())
                    voicemsgchain = MessageChain.create([uploadvoice])
                    await app.sendGroupMessage(target1, voicemsgchain)
                    readfile.close()
                    os.remove(downloadfile)
                    os.remove(conventamr)
                except Exception:
                    traceback.print_exc()
        if run.find('[一分钟后撤回本消息]') != -1:
            await asyncio.sleep(60)
            await app.revokeMessage(send)
        if run.find('[30秒后撤回本消息]') != -1:
            await asyncio.sleep(30)
            await app.revokeMessage(send)
        if run.find('[wait]') != -1:
            ranint = random.randint(1, 3)
            if ranint == 2:
                waitmsg = await makemsgchain('提示：你可以发送“是”字来将所有无效结果再次查询。（考虑到实现复杂性，恕不提供选择性查询）', msgtype)
                await sendmessage(app, waitmsg, target1, target2, msgtype)
            if ranint == 3:
                try:
                    mgroup = [657876815, 676942198]
                    if msgtype == 'Group' and target1.id in mgroup:
                        waitmsg = MessageChain.create([At(2854196310)])
                        await sendmessage(app, waitmsg, target1, target2, msgtype)
                except Exception:
                    traceback.print_exc()
            MessageEventImport = __import__('graia.application', fromlist=[f'{msgtype}Message'])
            MessageEvent = getattr(MessageEventImport, f'{msgtype}Message')
            InterruptImport = __import__('graia.application.interrupt.interrupts',
                                         fromlist=[f'{msgtype}MessageInterrupt'])
            Interrupt = getattr(InterruptImport, f'{msgtype}MessageInterrupt')
            if msgtype == 'Friend':
                event: MessageEvent = await im.wait(Interrupt(target1.id))
            else:
                event: MessageEvent = await im.wait(Interrupt(target1, target2))
            print(event)
            if event.messageChain.asDisplay() == '是':
                msg2 = await command(run)
                msgchain = await makemsgchain(msg2, msgtype)
                await sendmessage(app, msgchain, target1, target2, msgtype)
            else:
                pass


async def makemsgchain(msg, msgtype):
    msg = re.sub('\[wait\]', '', msg)
    exec('from graia.application.message.elements.internal import UploadMethods')
    mth = eval(f'UploadMethods.{msgtype}')
    fuimg = re.match(r'.*\[\[uimg:(.*)\]\]', msg)
    if fuimg:
        msg = re.sub(r'\[\[uimg:.*\]\]','',msg)
        try:
            msgchain = MessageChain.create(
                [Plain(msg)])
            msgchain = msgchain.plusWith(
                [Image.fromLocalFile(filepath=abspath(fuimg.group(1)), method=mth)])
        except Exception:
            traceback.print_exc()
    else:
        msgchain = MessageChain.create(
            [Plain(msg)])
    r = re.findall(r'(https?://.*?/File:.*?\.(?:png|gif|jpg|jpeg|webp|bmp|ico))', msg, re.I)
    for d in r:
        try:
            d1 = await findimage(d)
            print(d1)
            msgchain = msgchain.plusWith([Image.fromNetworkAddress(url=d1, method=mth)])
        except Exception:
            traceback.print_exc()
    return msgchain


async def sendmessage(app, msgchain, target1, target2, msgtype, quoteid=0):
    if msgtype == 'Friend':
        friend = target1
        send = await app.sendFriendMessage(friend, msgchain.asSendable())
    if msgtype == 'Group':
        group = target1
        send = await app.sendGroupMessage(group, msgchain.asSendable(), quote=quoteid if quoteid != 0 else None)
    if msgtype == 'Temp':
        group = target1
        member = target2
        send = await app.sendTempMessage(group=group, target=member, message=msgchain.asSendable())
    return send
