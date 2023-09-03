import mimetypes
import os
import re
import traceback
from typing import List, Union

import nio

from bots.matrix.client import bot, homeserver_host
from bots.matrix.info import client_name
from config import Config
from core.builtins import Bot, Plain, Image, Voice, MessageSession as MS, ErrorMessage
from core.builtins.message.chain import MessageChain
from core.logger import Logger
from core.types import FetchTarget as FT, \
    FinishedSession as FinS
from core.utils.image import image_split
from database import BotDBUtil

enable_analytics = Config('enable_analytics')


class FinishedSession(FinS):
    async def delete(self):
        """
        用于删除这条消息。
        """
        try:
            for x in self.message_id:
                await bot.room_redact(str(self.result), x)
        except Exception:
            Logger.error(traceback.format_exc())


class MessageSession(MS):
    class Feature:
        image = True
        voice = True
        embed = False
        forward = False
        delete = True
        quote = True
        wait = True

    async def send_message(self, message_chain, quote=True, disable_secret_check=False,
                           allow_split_image=True) -> FinishedSession:
        message_chain = MessageChain(message_chain)
        if not message_chain.is_safe and not disable_secret_check:
            return await self.send_message(Plain(ErrorMessage(self.locale.t("error.message.chain.unsafe"))))
        self.sent.append(message_chain)
        send: list[nio.RoomSendResponse] = []
        for x in message_chain.as_sendable(embed=False):
            replyTo = None
            if quote and len(send) == 0:
                replyTo = self.target.message_id

            if isinstance(x, Plain):
                content = {
                    'msgtype': 'm.notice',
                    'body': x.text
                }
                if replyTo:
                    # https://spec.matrix.org/v1.7/client-server-api/#fallbacks-for-rich-replies
                    # todo: standardize fallback for m.image, m.video, m.audio, and m.file
                    replyToType = self.session.message['content']['msgtype']
                    content[
                        'body'] = f">{' *' if replyToType == 'm.emote' else ''} <{self.session.sender}> {self.session.message['content']['body']}\n\n{x.text}"
                    content['format'] = 'org.matrix.custom.html'
                    htmlText = x.text.replace('\n', '<br />')
                    content[
                        'formatted_body'] = f"<mx-reply><blockquote><a href=\"https://matrix.to/#/{self.session.target}/{replyTo}?via={homeserver_host}\">In reply to</a>{' *' if replyToType == 'm.emote' else ''} <a href=\"https://matrix.to/#/{self.session.sender}\">{self.session.sender}</a><br/>{self.session.message['content']['body']}</blockquote></mx-reply>{htmlText}"
                Logger.info(f'[Bot] -> [{self.target.target_id}]: {x.text}')
            elif isinstance(x, Image):
                split = [x]
                if allow_split_image:
                    split = await image_split(x)
                for xs in split:
                    path = await xs.get()
                    with open(path, 'rb') as image:
                        filename = os.path.basename(path)
                        filesize = os.path.getsize(path)
                        (contentType, contentEncoding) = mimetypes.guess_type(path)
                        if contentType is None or contentEncoding is None:
                            contentType = 'image'
                            contentEncoding = 'png'
                        mimetype = f"{contentType}/{contentEncoding}"

                        (upload, upload_encryption) = await bot.upload(
                            image,
                            content_type=mimetype,
                            filename=filename,
                            encrypt=False,
                            filesize=filesize)
                        Logger.info(
                            f"Uploaded image {filename} to media repo, uri: {upload.content_uri}, mime: {mimetype}")
                        # todo: provide more image info
                        content = {
                            'msgtype': 'm.image',
                            'url': upload.content_uri,
                            'body': filename,
                            'info': {
                                'size': filesize,
                                'mimetype': mimetype,
                            }
                        }
                        Logger.info(f'[Bot] -> [{self.target.target_id}]: Image: {str(xs.__dict__)}')
            elif isinstance(x, Voice):
                path = x.path
                filename = os.path.basename(path)
                filesize = os.path.getsize(path)
                (contentType, contentEncoding) = mimetypes.guess_type(path)
                if contentType is None or contentEncoding is None:
                    contentType = 'audio'
                    contentEncoding = 'ogg'
                mimetype = f"{contentType}/{contentEncoding}"

                with open(path, 'rb') as audio:
                    (upload, upload_encryption) = await bot.upload(
                        audio,
                        content_type=mimetype,
                        filename=filename,
                        encrypt=False,
                        filesize=filesize)
                Logger.info(
                    f"Uploaded audio {filename} to media repo, uri: {upload.content_uri}, mime: {mimetype}")
                # todo: provide audio duration info
                content = {
                    'msgtype': 'm.audio',
                    'url': upload.content_uri,
                    'body': filename,
                    'info': {
                        'size': filesize,
                        'mimetype': mimetype,
                    }
                }
                Logger.info(f'[Bot] -> [{self.target.target_id}]: Voice: {str(x.__dict__)}')

            if replyTo:
                # rich reply
                content['m.relates_to'] = {
                    'm.in_reply_to': {
                        'event_id': replyTo
                    }
                }

            resp = await bot.room_send(self.session.target, 'm.room.message', content)
            if 'status_code' in resp.__dict__:
                Logger.error(f"Error in sending message: {str(resp)}")
            else:
                send.append(resp)

        return FinishedSession(self, [resp.event_id for resp in send], self.session.target)

    async def check_native_permission(self):
        if self.session.target.startswith('@') or self.session.sender.startswith('!'):
            return True
        # https://spec.matrix.org/v1.7/client-server-api/#permissions
        powerLevels = await bot.room_get_state_event(self.session.target, 'm.room.power_levels')
        level = powerLevels.content['users'][self.session.sender]
        if level is not None and level >= 50:
            return True
        return False

    def as_display(self, text_only=False):
        if not text_only or self.session.message['content']['msgtype'] == 'm.text':
            return str(self.session.message['content']['body'])
        if not text_only and 'format' in self.session.message['content']:
            return str(self.session.message['content']['formatted_body'])
        return ''

    async def to_message_chain(self):
        content = self.session.message['content']
        msgtype = content['msgtype']
        if msgtype == 'm.emote':
            msgtype = 'm.text'
        if msgtype == 'm.text':  # compatible with py38
            text = str(content['body'])
            if self.target.reply_id is not None:
                # redact the fallback line for rich reply
                # https://spec.matrix.org/v1.7/client-server-api/#fallbacks-for-rich-replies
                while text.startswith('> '):
                    text = ''.join(text.splitlines(keepends=True)[1:])
            return MessageChain(Plain(text.strip()))
        elif msgtype == 'm.image':
            url = str(content['url'])
            return MessageChain(Image(await bot.mxc_to_http(url)))
        elif msgtype == 'm.audio':
            url = str(content['url'])
            return MessageChain(Voice(await bot.mxc_to_http(url)))
            pass
        Logger.error(f"Got unknown msgtype: {msgtype}")
        return MessageChain([])

    async def delete(self):
        try:
            await bot.room_redact(self.session.target, self.session.message['event_id'])
        except Exception:
            Logger.error(traceback.format_exc())

    # https://spec.matrix.org/v1.7/client-server-api/#typing-notifications
    class Typing:
        def __init__(self, msg: MS):
            self.msg = msg

        async def __aenter__(self):
            await bot.room_typing(self.msg.session.target, True)
            pass

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await bot.room_typing(self.msg.session.target, False)
            pass


class FetchedSession(Bot.FetchedSession):

    async def _resolve_matrix_room_(self):
        target_id: str = self.session.target
        if target_id.startswith('@'):
            # find private messaging room
            for room in bot.rooms:
                room = bot.rooms[room]
                if room.join_rule == 'invite' and ((room.member_count == 2 and target_id in room.users)
                                                   or (room.member_count == 1 and target_id in room.invited_users)):
                    resp = await bot.room_get_state_event(room.room_id, 'm.room.member', target_id)
                    if resp is nio.ErrorResponse:
                        pass
                    elif resp.content['membership'] == 'join' or resp.content['membership'] == 'leave':
                        self.session.target = room.room_id
                        return
            Logger.info(f"Could not find any exist private room for {target_id}, trying to create one")
            resp = await bot.room_create(visibility=nio.RoomVisibility.private,
                                         is_direct=True,
                                         preset=nio.RoomPreset.trusted_private_chat,
                                         invite=[target_id], )
            if resp is nio.ErrorResponse:
                pass
            room = resp.room_id
            Logger.info(f"Created private messaging room for {target_id}: {room}")
            self.session.target = room


Bot.FetchedSession = FetchedSession


class FetchTarget(FT):
    name = client_name

    @staticmethod
    async def fetch_target(target_id, sender_id=None) -> Union[FetchedSession]:
        matchChannel = re.match(r'^(Matrix)\|(.*)', target_id)
        if matchChannel:
            targetFrom = senderFrom = matchChannel.group(1)
            target_id = matchChannel.group(2)
            if sender_id:
                matchSender = re.match(r'^(Matrix)\|(.*)', sender_id)
                if matchSender:
                    senderFrom = matchSender.group(1)
                    sender_id = matchSender.group(2)
            else:
                sender_id = target_id
            session = Bot.FetchedSession(targetFrom, target_id, senderFrom, sender_id)
            await session._resolve_matrix_room_()
            return session

    @staticmethod
    async def fetch_target_list(target_list: list) -> List[FetchedSession]:
        lst = []
        for x in target_list:
            fet = await FetchTarget.fetch_target(x)
            if fet:
                lst.append(fet)
        return lst

    @staticmethod
    async def post_message(module_name, message, user_list: List[FetchedSession] = None, i18n=False, **kwargs):
        if user_list is not None:
            for x in user_list:
                try:
                    if i18n:
                        await x.send_direct_message(x.parent.locale.t(message, **kwargs))

                    else:
                        await x.send_direct_message(message)
                    if enable_analytics:
                        BotDBUtil.Analytics(x).add('', module_name, 'schedule')
                except Exception:
                    Logger.error(traceback.format_exc())
        else:
            get_target_id = BotDBUtil.TargetInfo.get_enabled_this(module_name, "Matrix")
            for x in get_target_id:
                fetch = await FetchTarget.fetch_target(x.target_id)
                if fetch:
                    try:
                        if i18n:
                            await fetch.send_direct_message(fetch.parent.locale.t(message, **kwargs))
                        else:
                            await fetch.send_direct_message(message)
                        if enable_analytics:
                            BotDBUtil.Analytics(fetch).add('', module_name, 'schedule')
                    except Exception:
                        Logger.error(traceback.format_exc())


Bot.MessageSession = MessageSession
Bot.FetchTarget = FetchTarget
