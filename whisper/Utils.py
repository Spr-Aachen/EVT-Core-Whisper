import os
import sys
import zlib
from typing import Callable, TextIO


system_encoding = sys.getdefaultencoding()

if system_encoding != "utf-8":
    def make_safe(string):
        # replaces any character not representable using the system default encoding with an '?',
        # avoiding UnicodeEncodeError (https://github.com/openai/whisper/discussions/729).
        return string.encode(system_encoding, errors="replace").decode(system_encoding)
else:
    def make_safe(string):
        # utf-8 can encode any Unicode code point, so no need to do the round-trip encoding
        return string


def exact_div(x, y):
    assert x % y == 0
    return x // y


def str2bool(string):
    str2val = {"True": True, "False": False}
    if string in str2val:
        return str2val[string]
    else:
        raise ValueError(f"Expected one of {set(str2val.keys())}, got {string}")


def optional_int(string):
    return None if string == "None" else int(string)


def optional_float(string):
    return None if string == "None" else float(string)


def compression_ratio(text) -> float:
    text_bytes = text.encode("utf-8")
    return len(text_bytes) / len(zlib.compress(text_bytes))


def format_timestamp(seconds: float, always_include_hours: bool = False, decimal_marker: str = '.'):
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000

    hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
    return f"{hours_marker}{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"


class ResultWriter:
    extension: str

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def __call__(self, result: dict, audio_path: str, add_languageinfo: bool):
        audio_basename = os.path.basename(audio_path).rsplit('.', 1)[0]   #audio_basename = os.path.basename(audio_path)
        output_path = os.path.join(self.output_dir, audio_basename + "." + self.extension)

        with open(output_path, 'w', encoding = 'utf-8') as f:
            self.write_result(result, file = f, add_languageinfo = add_languageinfo)

    def write_result(self, result: dict, file: TextIO, add_languageinfo: bool):
        raise NotImplementedError


class WriteSRT(ResultWriter):
    extension: str = "srt"

    def write_result(self, result: dict, file: TextIO, add_languageinfo: bool):
        for i, segment in enumerate(result["segments"], start=1):
            # get language
            LANGUAGES = {
                "zh": "ZH",
                "en": "EN",
                "ja": "JA"
            }
            language = LANGUAGES[result['language']] if result['language'] in LANGUAGES else result['language'].upper()
            # write srt lines
            print(
                f"{i}\n"
                f"{format_timestamp(segment['start'], always_include_hours=True, decimal_marker=',')} --> "
                f"{format_timestamp(segment['end'], always_include_hours=True, decimal_marker=',')}\n"
                f"{f'[{language}]'if add_languageinfo else ''}{segment['text'].strip().replace('-->', '->')}\n",
                file=file,
                flush=True,
            )


def get_writer(output_format: str, output_dir: str) -> Callable[[dict, TextIO, bool], None]:
    writers = {"srt": WriteSRT}
    '''
    if output_format == "all":
        all_writers = [writer(output_dir) for writer in writers.values()]

        def write_all(result: dict, file: TextIO):
            for writer in all_writers:
                writer(result, file)

        return write_all
    '''
    return writers[output_format](output_dir)