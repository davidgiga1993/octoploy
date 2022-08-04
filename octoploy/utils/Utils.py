def remove_prefix(text, prefix):
    """
    Removeprefix for python <3.9
    :param text: Text
    :param prefix: Prefix to be removed
    :return: Text
    """
    if text.startswith(prefix):
        return text[len(prefix):]
    return text
