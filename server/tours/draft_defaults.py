"""Deterministic draft copy from the creator's own words, without image analysis."""
import re


_OLD_TITLES = {'untitled tour', 'my space', 'không gian của tôi'}


def draft_defaults(data):
    # Source language belongs to the creator's explicit choice. Keep the API's
    # existing default for callers which omit it, including idempotent retries.
    locale = data.locale
    title = data.title
    if 'title' not in data.model_fields_set or title.casefold() in _OLD_TITLES:
        first_line = next((line.strip() for line in data.text.splitlines() if line.strip()), '')
        title = re.split(r'[,;]|[.!?]\s', first_line, maxsplit=1)[0].strip()
        title = title[:150].rstrip() or ('Tour ảnh của bạn' if locale == 'vi' else 'Your photo tour')
    return title, locale


def scene_defaults(index, text, locale):
    if index == 0:
        return ('Tổng quan' if locale == 'vi' else 'Overview'), text or ('Ảnh do người đăng cung cấp.' if locale == 'vi' else 'Photos supplied by the creator.')
    # The upload order is known; room identity, adjacency and image contents are
    # not. Never invent "bedroom" or apply a whole-property claim to each photo.
    if locale == 'vi':
        return f'Góc nhìn {index + 1}', 'Góc nhìn trong bộ ảnh do người đăng cung cấp.'
    return f'Viewpoint {index + 1}', 'A viewpoint from the photos supplied by the creator.'
