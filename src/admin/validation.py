"""Strict input validation shared by the HTTP API and backup import."""
from urllib.parse import urlsplit
from ..keyword_filter import validate_rule

ENUMS = {
    'state': {0, 1}, 'notify': {-100, 0, 1}, 'send_mode': {-100, -1, 0, 1, 2},
    'link_preview': {-100, 0, 1}, 'display_author': {-100, -1, 0, 1},
    'display_via': {-100, -2, -1, 0, 1}, 'display_title': {-100, -1, 0, 1},
    'display_entry_tags': {-100, -1, 0, 1}, 'style': {-100, 0, 1},
    'display_media': {-100, -1, 0},
}
SUB_FIELDS = set(ENUMS) | {'title', 'tags', 'interval', 'length_limit', 'keyword_filter'}


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'数值必须是 {low} 到 {high} 之间的整数')
    return value


def url(value):
    if not isinstance(value, str) or len(value) > 4096:
        raise ValueError('订阅地址无效')
    parsed = urlsplit(value)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('订阅地址必须是 HTTP 或 HTTPS 链接，且不能包含登录凭据')
    return value


def options(data, user=False):
    allowed = SUB_FIELDS - {'keyword_filter', 'title', 'tags', 'state'} if user else SUB_FIELDS
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError('包含不支持的配置字段')
    result = {}
    for key, value in data.items():
        if key == 'keyword_filter':
            value = validate_rule(value)
        elif key in ('title', 'tags'):
            if value is not None and (not isinstance(value, str) or len(value) > (1024 if key == 'title' else 255)):
                raise ValueError('标题或标签过长')
            value = value or None
        elif key == 'interval':
            if value is not None:
                integer(value, 1, 32767)
        elif key == 'length_limit':
            integer(value, 0 if user else -100, 32767)
            if value < 0 and value != -100:
                raise ValueError('长度限制无效')
        else:
            if type(value) is not int or value not in ENUMS[key] or (user and value == -100):
                raise ValueError(f'{key} 的选项无效')
        result[key] = value
    return result


def global_options(data):
    allowed = {'default_interval', 'minimal_interval', 'user_sub_limit', 'channel_or_group_sub_limit',
               'sub_limit_reached_message'}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError('全局配置字段无效')
    for key, value in data.items():
        if key == 'sub_limit_reached_message':
            if not isinstance(value, str) or len(value) > 4096:
                raise ValueError('订阅限制提示最多 4096 个字符')
        else:
            integer(value, 1 if key.endswith('interval') else -1, 32767)
    return data
