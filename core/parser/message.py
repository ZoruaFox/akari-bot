import re
import traceback
from datetime import datetime

from core.elements import MessageSession, Command, Option, Schedule, StartUp, command_prefix
from core.loader import ModulesManager
from core.logger import Logger
from core.parser.command import CommandParser, InvalidCommandFormatError, InvalidHelpDocTypeError
from core.utils import remove_ineffective_text, RemoveDuplicateSpace
from core.tos import warn_target
from core.exceptions import AbuseWarning
from database import BotDBUtil

Modules = ModulesManager.return_modules_list_as_dict()
ModulesAliases = ModulesManager.return_modules_alias_map()
ModulesRegex = ModulesManager.return_regex_modules()

counter_same = {}  # 命令使用次数计数（重复使用单一命令）
counter_all = {}  # 命令使用次数计数（使用所有命令）

temp_ban_counter = {}  # 临时封禁计数


async def msg_counter(msg: MessageSession, command: str):
    same = counter_same.get(msg.target.senderId)
    if same is None or datetime.now().timestamp() - same['ts'] > 300 or same[
            'command'] != command:  # 检查是否滥用（重复使用同一命令）
        counter_same[msg.target.senderId] = {'command': command, 'count': 1,
                                             'ts': datetime.now().timestamp()}
    else:
        same['count'] += 1
        if same['count'] > 10:
            raise AbuseWarning('一段时间内使用相同命令的次数过多')
    all_ = counter_all.get(msg.target.senderId)
    if all_ is None or datetime.now().timestamp() - all_['ts'] > 300:  # 检查是否滥用（重复使用同一命令）
        counter_all[msg.target.senderId] = {'count': 1,
                                            'ts': datetime.now().timestamp()}
    else:
        all_['count'] += 1
        if all_['count'] > 30:
            raise AbuseWarning('一段时间内使用命令的次数过多')


async def parser(msg: MessageSession):
    """
    接收消息必经的预处理器
    :param msg: 从监听器接收到的dict，该dict将会经过此预处理器传入下游
    :return: 无返回
    """
    global Modules
    global ModulesAliases
    global ModulesRegex
    if Modules == {}:
        Modules = ModulesManager.return_modules_list_as_dict()
        ModulesAliases = ModulesManager.return_modules_alias_map()
        ModulesRegex = ModulesManager.return_regex_modules()
    display = RemoveDuplicateSpace(msg.asDisplay())  # 将消息转换为一般显示形式
    msg.trigger_msg = display
    msg.target.senderInfo = senderInfo = BotDBUtil.SenderInfo(msg.target.senderId)
    enabled_modules_list = BotDBUtil.Module(msg).check_target_enabled_module_list()
    if senderInfo.query.isInBlackList and not senderInfo.query.isInWhiteList or len(display) == 0:
        return
    if display[0] in command_prefix:  # 检查消息前缀
        if len(display) <= 1:
            return
        Logger.info(
            f'[{msg.target.senderId}{f" ({msg.target.targetId})" if msg.target.targetFrom != msg.target.senderFrom else ""}] -> [Bot]: {display}')
        command = display[1:]
        command_list = remove_ineffective_text(command_prefix, command.split('&&'))  # 并行命令处理
        if len(command_list) > 5 and not senderInfo.query.isSuperUser:
            await msg.sendMessage('你不是本机器人的超级管理员，最多只能并排执行5个命令。')
            return
        for command in command_list:
            command_spilt = command.split(' ')  # 切割消息
            msg.trigger_msg = command  # 触发该命令的消息，去除消息前缀
            command_first_word = command_spilt[0].lower()
            if command_first_word in ModulesAliases:
                command_spilt[0] = ModulesAliases[command_first_word]
                command = ' '.join(command_spilt)
                command_spilt = command.split(' ')
                command_first_word = command_spilt[0]
                msg.trigger_msg = command
            if command_first_word in Modules:  # 检查触发命令是否在模块列表中
                try:
                    is_temp_banned = temp_ban_counter.get(msg.target.senderId)
                    if is_temp_banned is not None:
                        ban_time = datetime.now().timestamp() - is_temp_banned['ts']
                        if ban_time < 300:
                            if is_temp_banned['count'] < 2:
                                is_temp_banned['count'] += 1
                                return await msg.sendMessage('提示：\n'
                                                             '由于你的行为触发了警告，我们已对你进行临时封禁。\n'
                                                             f'距离解封时间还有{str(int(300 - ban_time))}秒。')
                            elif is_temp_banned['count'] <= 5:
                                is_temp_banned['count'] += 1
                                return await msg.sendMessage('即使是触发了临时封禁，继续使用命令还是可能会导致你被再次警告。\n'
                                                             f'距离解封时间还有{str(int(300 - ban_time))}秒。')
                            else:
                                return await warn_target(msg)
                    await msg_counter(msg, command)
                    module = Modules[command_first_word]
                    if isinstance(module, (Option, Schedule, StartUp)):
                        if module.desc is not None:
                            return await msg.sendMessage(module.desc)
                        return
                    if isinstance(module, Command):
                        if module.need_superuser:
                            if not msg.checkSuperUser():
                                return await msg.sendMessage('你没有使用该命令的权限。')
                        elif not module.is_base_function:
                            if command_first_word not in enabled_modules_list:  # 若未开启
                                return await msg.sendMessage(f'此模块未启用，请发送~enable {command_first_word}启用本模块。')
                        if module.need_admin:
                            if not await msg.checkPermission():
                                return await msg.sendMessage('此命令仅能被该群组的管理员所使用，请联系管理员执行此命令。')
                        if module.help_doc is not None:
                            try:
                                command_parser = CommandParser(module)
                                try:
                                    msg.parsed_msg = command_parser.parse(command)
                                    if msg.parsed_msg is None and not Modules[command_first_word].allowed_none:
                                        return await msg.sendMessage(command_parser.return_formatted_help_doc())
                                except InvalidCommandFormatError:
                                    return await msg.sendMessage('语法错误。\n' + command_parser.return_formatted_help_doc())
                            except InvalidHelpDocTypeError:
                                return await msg.sendMessage(
                                    '此模块的帮助信息有误，请联系开发者处理。\n错误汇报地址：https://github.com/Teahouse-Studios/bot/issues/new?assignees=OasisAkari&labels=bug&template=5678.md&title=')
                        async with msg.Typing(msg):
                            await Modules[command_first_word].function(msg)  # 将msg传入下游模块
                except AbuseWarning as e:
                    await warn_target(msg, str(e))
                    temp_ban_counter[msg.target.senderId] = {'count': 1,
                                                             'ts': datetime.now().timestamp()}
                    return
                except Exception as e:
                    Logger.error(traceback.format_exc())
                    await msg.sendMessage('执行命令时发生错误，请报告机器人开发者：\n' + str(
                        e) + '\n错误汇报地址：https://github.com/Teahouse-Studios/bot/issues/new?assignees=OasisAkari&labels=bug&template=5678.md&title=')
    for regex in ModulesRegex:  # 遍历正则模块列表
        try:
            if regex in enabled_modules_list:
                regex_module = ModulesRegex[regex]
                msg.matched_msg = False
                if regex_module.mode.upper() in ['M', 'MATCH']:
                    msg.matched_msg = re.match(regex_module.pattern, display, flags=regex_module.flags)
                    if msg.matched_msg is not None:
                        async with msg.Typing(msg):
                            await regex_module.function(msg)  # 将msg传入下游模块
                elif regex_module.mode.upper() in ['A', 'FINDALL']:
                    msg.matched_msg = re.findall(regex_module.pattern, display, flags=regex_module.flags)
                    if msg.matched_msg:
                        async with msg.Typing(msg):
                            await regex_module.function(msg)  # 将msg传入下游模块
        except AbuseWarning as e:
            await warn_target(msg, str(e))
            temp_ban_counter[msg.target.senderId] = {'count': 1,
                                                     'ts': datetime.now().timestamp()}
        except Exception:
            Logger.error(traceback.format_exc())
