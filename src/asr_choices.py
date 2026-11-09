"""Conservative scene hints; never reinterpret negations or unrelated speech."""
import re


def prediction_grammar():
    phrases = ['[unk]', '不 知道', '不是 狐狸', '不是 老虎']
    for animal in ['狐狸', '老虎']:
        for prefix in ['', '我 猜 ', '我 选 ', '我 猜 是 ', '怕 的 是 ',
                       '我 猜 它 怕 的 是 ', '我 猜 她 怕 的 是 ']:
            phrases.append(prefix + animal)
    return phrases


def corrected_prediction(raw, contextual, confidence):
    """Only recover the fox confusions actually observed at this demo."""
    raw = re.sub(r'[\s，。！？、,.!?]', '', raw)
    candidate = re.sub(r'\s', '', contextual)
    if '[unk]' in candidate or confidence < .8:
        return None
    prefixes = ['', '我猜', '我选', '我猜是', '我猜它怕的是', '我猜她怕的是']
    observed = {prefix + word for prefix in prefixes for word in ['苦力', '和利益']}
    fox = {prefix + '狐狸' for prefix in prefixes}
    return candidate if raw in observed and candidate in fox else None
