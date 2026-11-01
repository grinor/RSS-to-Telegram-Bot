"""Per-subscription literal keyword matching, independent of message formatting."""
import unicodedata
from html import unescape
from html.parser import HTMLParser


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif tag in ('p', 'div', 'br', 'li'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ('p', 'div', 'li'):
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def normalize(value):
    return unicodedata.normalize('NFKC', unescape(value)).casefold()


def validate_rule(rule):
    if rule is None:
        return None
    if not isinstance(rule, dict) or set(rule) - {'include', 'exclude', 'mode', 'scope'}:
        raise ValueError('过滤规则格式错误')
    result = {'mode': rule.get('mode', 'any'), 'scope': rule.get('scope', 'all')}
    if result['mode'] not in ('any', 'all') or result['scope'] not in ('title', 'all'):
        raise ValueError('过滤模式或范围无效')
    for key in ('include', 'exclude'):
        words = rule.get(key, [])
        if not isinstance(words, list) or len(words) > 100:
            raise ValueError('每组关键词最多 100 个')
        if any(not isinstance(w, str) or not w.strip() or len(w) > 200 for w in words):
            raise ValueError('关键词不能为空，且最多 200 个字符')
        result[key] = list(dict.fromkeys(w.strip() for w in words))
    return result


def matches_entry(entry, rule):
    if not rule:
        return True
    parts = [entry.get('title', '')]
    if rule.get('scope', 'all') == 'all':
        parts += [entry.get('summary', ''), entry.get('description', '')]
        parts += [c.get('value', '') for c in entry.get('content', []) if isinstance(c, dict)]
    parser = _Text()
    parser.feed(' '.join(str(p or '') for p in parts))
    text = normalize(''.join(parser.parts))
    if any(normalize(w) in text for w in rule.get('exclude', [])):
        return False
    include = rule.get('include', [])
    if not include:
        return True
    check = all if rule.get('mode') == 'all' else any
    return check(normalize(w) in text for w in include)
