import ujson as json

from core.builtins import ErrorMessage
from core.utils.http import get_url, post_url
from datetime import datetime


async def get_alias(input, get_music=False):
    url = "https://download.fanyu.site/maimai/alias.json"
    data = await get_url(url, 200, fmt='json')

    result = []
    if get_music:
        if input in data:
            result = data[input]
    else:
        for alias, ids in data.items():
            if input in ids:
                result.append(alias)

    return result


async def get_rank(msg, payload):
    try:
        userdata = await post_url('https://www.diving-fish.com/api/maimaidxprober/query/player',
                                  data=json.dumps(payload),
                                  status_code=200,
                                  headers={'Content-Type': 'application/json', 'accept': '*/*'}, fmt='json')
        username = userdata['username']
        rating = userdata['rating']
    except ValueError as e:
        if str(e).startswith('400'):
            await msg.finish(msg.locale.t("maimai.message.user_not_found"))
        if str(e).startswith('403'):
            await msg.finish(msg.locale.t("maimai.message.forbidden"))
        else:
            await msg.finish(ErrorMessage(str(e)))

    rank_data = await get_url('https://www.diving-fish.com/api/maimaidxprober/rating_ranking', 200, fmt='json')
    sorted_data = sorted(rank_data, key=lambda x: x['ra'], reverse=True)

    rank = None
    total_rating = 0
    total_rank = len(sorted_data)

    for i, scoreboard in enumerate(sorted_data):
        if scoreboard['username'] == username:
            rank = i + 1
        total_rating += scoreboard['ra']

    if rank is None:
        rank = total_rank

    average_rating = total_rating / total_rank
    surpassing_rate = (total_rank - rank) / total_rank * 100
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return time, total_rank, average_rating, username, rating, rank, surpassing_rate
