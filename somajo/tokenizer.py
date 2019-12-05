#!/usr/bin/env python3

import unicodedata
import warnings

import regex as re

from somajo import doubly_linked_list
from somajo import utils
from somajo.token import Token


class Tokenizer(object):

    supported_languages = set(["de", "en"])
    default_language = "de"

    def __init__(self, split_camel_case=False, token_classes=False, extra_info=False, language="de"):
        """Create a Tokenizer object. If split_camel_case is set to True,
        tokens written in CamelCase will be split. If token_classes is
        set to true, the tokenizer will output the token class for
        each token (if it is a number, an XML tag, an abbreviation,
        etc.). If extra_info is set to True, the tokenizer will output
        information about the original spelling of the tokens.

        """
        self.split_camel_case = split_camel_case
        self.token_classes = token_classes
        self.extra_info = extra_info
        self.language = language if language in self.supported_languages else self.default_language
        self.unique_string_length = 7
        self.mapping = {}
        self.unique_prefix = None
        self.replacement_counter = 0

        self.spaces = re.compile(r"\s+")
        self.controls = re.compile(r"[\u0000-\u001F\u007F-\u009F]")
        self.stranded_variation_selector = re.compile(r" \uFE0F")
        # soft hyphen (00AD), zero-width space (200B), zero-width
        # non-joiner (200C), zero-width joiner (200D), Arabic letter
        # mark (061C), left-to-right mark (200E), right-to-left mark
        # (200F), word joiner (2060), left-to-right isolate (2066),
        # right-to-left isolate (2067), first strong isolate (2068),
        # pop directional isolate (2069), l-t-r/r-t-l embedding (202A,
        # 202B), l-t-r/r-t-l override (202D, 202E), pop directional
        # formatting (202C), zero-width no-break space (FEFF)
        self.other_nasties = re.compile(r"[\u00AD\u061C\u200B-\u200F\u202A-\u202E\u2060\u2066-\u2069\uFEFF]")
        # combination
        self.starts_with_junk = re.compile(r"^[\u0000-\u001F\u007F-\u009F\u00AD\u061C\u200B-\u200F\u202A-\u202E\u2060\u2066-\u2069\uFEFF]+")
        self.junk_next_to_space = re.compile(r"(?:^|\s)[\u0000-\u001F\u007F-\u009F\u00AD\u061C\u200B-\u200F\u202A-\u202E\u2060\u2066-\u2069\uFEFF]+|[\u0000-\u001F\u007F-\u009F\u00AD\u061C\u200B-\u200F\u202A-\u202E\u2060\u2066-\u2069\uFEFF]+(?:\s|$)")
        self.junk_between_spaces = re.compile(r"(?:^|\s+)[\s\u0000-\u001F\u007F-\u009F\u00AD\u061C\u200B-\u200F\u202A-\u202E\u2060\u2066-\u2069\uFEFF]+(?:\s+|$)")

        # TAGS, EMAILS, URLs
        self.xml_declaration = re.compile(r"""<\?xml
                                              (?:                #   This group permits zero or more attributes
                                                \s+              #   Whitespace to separate attributes
                                                [_:A-Z][-.:\w]*  #   Attribute name
                                                \s*=\s*          #   Attribute name-value delimiter
                                                (?: "[^"]*"      #   Double-quoted attribute value
                                                  | '[^']*'      #   Single-quoted attribute value
                                                )
                                              )*
                                              \s*                #   Permit trailing whitespace
                                              \?>""", re.VERBOSE | re.IGNORECASE)
        # self.tag = re.compile(r'<(?!-)(?:/[^> ]+|[^>]+/?)(?<!-)>')
        # taken from Regular Expressions Cookbook
        self.tag = re.compile(r"""
                                  <
                                  (?:                  # Branch for opening tags:
                                    ([_:A-Z][-.:\w]*)  #   Capture the opening tag name to backreference 1
                                    (?:                #   This group permits zero or more attributes
                                      \s+              #   Whitespace to separate attributes
                                      [_:A-Z][-.:\w]*  #   Attribute name
                                      \s*=\s*          #   Attribute name-value delimiter
                                      (?: "[^"]*"      #   Double-quoted attribute value
                                        | '[^']*'      #   Single-quoted attribute value
                                      )
                                    )*
                                    \s*                #   Permit trailing whitespace
                                    /?                 #   Permit self-closed tags
                                  |                    # Branch for closing tags:
                                    /
                                    ([_:A-Z][-.:\w]*)  #   Capture the closing tag name to backreference 2
                                    \s*                #   Permit trailing whitespace
                                  )
                                  >
        """, re.VERBOSE | re.IGNORECASE)
        # regex for email addresses taken from:
        # http://www.regular-expressions.info/email.html
        # self.email = re.compile(r"\b[\w.%+-]+@[\w.-]+\.\p{L}{2,}\b")
        self.email = re.compile(r"\b[\w.%+-]+(?:@| \[at\] )[\w.-]+(?:\.| \[?dot\]? )\p{L}{2,}\b")
        # simple regex for urls that start with http or www
        # TODO: schließende Klammer am Ende erlauben, wenn nach http etc. eine öffnende kam
        self.simple_url_with_brackets = re.compile(r'\b(?:(?:https?|ftp|svn)://|(?:https?://)?www\.)\S+?\(\S*?\)\S*(?=$|[\'. "!?,;])', re.IGNORECASE)
        self.simple_url = re.compile(r'\b(?:(?:https?|ftp|svn)://|(?:https?://)?www\.)\S+[^\'. "!?,;:)]', re.IGNORECASE)
        self.doi = re.compile(r'\bdoi:10\.\d+/\S+', re.IGNORECASE)
        self.doi_with_space = re.compile(r'(?<=\bdoi: )10\.\d+/\S+', re.IGNORECASE)
        # we also allow things like tagesschau.de-App
        self.url_without_protocol = re.compile(r'\b[\w./-]+\.(?:de|com|org|net|edu|info|gov|jpg|png|gif|log|txt|xlsx?|docx?|pptx?|pdf)(?:-\w+)?\b', re.IGNORECASE)
        self.reddit_links = re.compile(r'(?<!\w)/?[rlu](?:/\w+)+/?(?!\w)', re.IGNORECASE)

        # XML entities
        self.entity = re.compile(r"""&(?:
                                         quot|amp|apos|lt|gt  # named entities
                                         |
                                         \#\d+                # decimal entities
                                         |
                                         \#x[0-9a-f]+         # hexadecimal entities
                                      );""", re.VERBOSE | re.IGNORECASE)

        # EMOTICONS
        emoticon_set = set(["(-.-)", "(T_T)", "(♥_♥)", ")':", ")-:",
                            "(-:", ")=", ")o:", ")x", ":'C", ":/",
                            ":<", ":C", ":[", "=(", "=)", "=D", "=P",
                            ">:", "\\:", "]:", "x(", "^^", "o.O",
                            "\\O/", "\\m/", ":;))", "_))", "*_*", "._.",
                            ":wink:", ">_<", "*<:-)", ":!:", ":;-))"])
        emoticon_list = sorted(emoticon_set, key=len, reverse=True)
        self.emoticon = re.compile(r"""(?:(?:[:;]|(?<!\d)8)           # a variety of eyes, alt.: [:;8]
                                        [-'oO]?                       # optional nose or tear
                                        (?: \)+ | \(+ | [*] | ([DPp])\1*(?!\w)))   # a variety of mouths
                                    """ +
                                   r"|" +
                                   r"(?:\b[Xx]D+\b)" +
                                   r"|" +
                                   r"(?:\b(?:D'?:|oO)\b)" +
                                   r"|" +
                                   r"|".join([re.escape(_) for _ in emoticon_list]), re.VERBOSE)
        self.space_emoticon = re.compile(r'([:;])[ ]+([()])')
        # ^3 is an emoticon, unless it is preceded by a number (with
        # optional whitespace between number and ^3)
        # ^\^3    # beginning of line, no leading characters
        # ^\D^3   # beginning of line, one leading character
        # (?<=\D[ ])^3   # two leading characters, non-number + space
        # (?<=.[^\d ])^3   # two leading characters, x + non-space-non-number
        self.heart_emoticon = re.compile(r"(?:^|^\D|(?<=\D[ ])|(?<=.[^\d ]))\^3")
        # NEW1: self.heart_emoticon = re.compile(r"(?<=\D)\^3")
        # NEW2: self.heart_emoticon = re.compile(r"^\^3")  # plus previous token must end in \D
        # U+2600..U+26FF	Miscellaneous Symbols
        # U+2700..U+27BF	Dingbats
        # U+FE0E..U+FE0F        text and emoji variation selectors
        # U+1F300..U+1F5FF	Miscellaneous Symbols and Pictographs
        # -> U+1F3FB..U+1F3FF   Emoji modifiers (skin tones)
        # U+1F600..U+1F64F	Emoticons
        # U+1F680..U+1F6FF	Transport and Map Symbols
        # U+1F900..U+1F9FF	Supplemental Symbols and Pictographs
        # self.unicode_symbols = re.compile(r"[\u2600-\u27BF\uFE0E\uFE0F\U0001F300-\U0001f64f\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF]")
        self.unicode_flags = re.compile(r"\p{Regional_Indicator}{2}\uFE0F?")

        # special tokens containing + or &
        tokens_with_plus_or_ampersand = utils.read_abbreviation_file("tokens_with_plus_or_ampersand.txt")
        plus_amp_simple = [(pa, re.search(r"^\w+[&+]\w+$", pa)) for pa in tokens_with_plus_or_ampersand]
        self.simple_plus_ampersand = set([pa[0].lower() for pa in plus_amp_simple if pa[1]])
        self.simple_plus_ampersand_candidates = re.compile(r"\b\w+[&+]\w+\b")
        tokens_with_plus_or_ampersand = [pa[0] for pa in plus_amp_simple if not pa[1]]
        # self.token_with_plus_ampersand = re.compile(r"(?<!\w)(?:\L<patokens>)(?!\w)", re.IGNORECASE, patokens=tokens_with_plus_or_ampersand)
        self.token_with_plus_ampersand = re.compile(r"(?<!\w)(?:" + r"|".join([re.escape(_) for _ in tokens_with_plus_or_ampersand]) + r")(?!\w)", re.IGNORECASE)

        # camelCase
        self.emoji = re.compile(r'\bemojiQ\p{L}{3,}\b')
        camel_case_token_list = utils.read_abbreviation_file("camel_case_tokens.txt")
        cc_alnum = [(cc, re.search(r"^\w+$", cc)) for cc in camel_case_token_list]
        self.simple_camel_case_tokens = set([cc[0] for cc in cc_alnum if cc[1]])
        self.simple_camel_case_candidates = re.compile(r"\b\w*\p{Ll}\p{Lu}\w*\b")
        camel_case_token_list = [cc[0] for cc in cc_alnum if not cc[1]]
        # things like ImmobilienScout24.de are already covered by URL detection
        # self.camel_case_url = re.compile(r'\b(?:\p{Lu}[\p{Ll}\d]+){2,}\.(?:de|com|org|net|edu)\b')
        self.camel_case_token = re.compile(r"\b(?:" + r"|".join([re.escape(_) for _ in camel_case_token_list]) + r"|:Mac\p{Lu}\p{Ll}*)\b")
        # self.camel_case_token = re.compile(r"\b(?:\L<cctokens>|Mac\p{Lu}\p{Ll}*)\b", cctokens=camel_case_token_set)
        self.in_and_innen = re.compile(r'\b\p{L}+\p{Ll}In(?:nen)?\p{Ll}*\b')
        self.camel_case = re.compile(r'(?<=\p{Ll}{2})(\p{Lu})(?!\p{Lu}|\b)')

        # GENDER STAR
        self.gender_star = re.compile(r'\b\p{L}+\*in(?:nen)?\p{Ll}*\b', re.IGNORECASE)

        # ABBREVIATIONS
        self.single_letter_ellipsis = re.compile(r"(?<![\w.])(?P<a_letter>\p{L})(?P<b_ellipsis>\.{3})(?!\.)")
        self.and_cetera = re.compile(r"(?<![\w.&])&c\.(?!\p{L}{1,3}\.)")
        self.str_abbreviations = re.compile(r'(?<![\w.])([\p{L}-]+-Str\.)(?!\p{L})', re.IGNORECASE)
        self.nr_abbreviations = re.compile(r"(?<![\w.])(\w+\.-?Nr\.)(?!\p{L}{1,3}\.)", re.IGNORECASE)
        self.single_letter_abbreviation = re.compile(r"(?<![\w.])\p{L}\.(?!\p{L}{1,3}\.)")
        # abbreviations with multiple dots that constitute tokens
        single_token_abbreviation_list = utils.read_abbreviation_file("single_token_abbreviations_%s.txt" % self.language)
        self.single_token_abbreviation = re.compile(r"(?<![\w.])(?:" + r'|'.join([re.escape(_) for _ in single_token_abbreviation_list]) + r')(?!\p{L}{1,3}\.)', re.IGNORECASE)
        self.ps = re.compile(r"(?<!\d[ ])\bps\.", re.IGNORECASE)
        self.multipart_abbreviation = re.compile(r'(?:\p{L}+\.){2,}')
        # only abbreviations that are not matched by (?:\p{L}\.)+
        abbreviation_list = utils.read_abbreviation_file("abbreviations_%s.txt" % self.language)
        # abbrev_simple = [(a, re.search(r"^\p{L}{2,}\.$", a)) for a in abbreviation_list]
        # self.simple_abbreviations = set([a[0].lower() for a in abbrev_simple if a[1]])
        # self.simple_abbreviation_candidates = re.compile(r"(?<![\w.])\p{L}{2,}\.(?!\p{L}{1,3}\.)")
        # abbreviation_list = [a[0] for a in abbrev_simple if not a[1]]
        self.abbreviation = re.compile(r"(?<![\p{L}.])(?:" +
                                       r"(?:(?:\p{L}\.){2,})" +
                                       r"|" +
                                       # r"(?i:" +    # this part should be case insensitive
                                       r'|'.join([re.escape(_) for _ in abbreviation_list]) +
                                       # r"))+(?!\p{L}{1,3}\.)", re.V1)
                                       r")+(?!\p{L}{1,3}\.)", re.IGNORECASE)

        # MENTIONS, HASHTAGS, ACTION WORDS, UNDERLINE
        self.mention = re.compile(r'[@]\w+(?!\w)')
        self.hashtag = re.compile(r'(?<!\w)[#]\w+(?!\w)')
        self.action_word = re.compile(r'(?<!\w)(?P<a_open>[*+])(?P<b_middle>[^\s*]+)(?P<c_close>[*])(?!\w)')
        # a pair of underscores can be used to "underline" some text
        self.underline = re.compile(r"(?<!\w)(?P<open_ul>_)(?P<text_ul>\w[^_]+\w)(?P<close_ul>_)(?!\w)")

        # DATE, TIME, NUMBERS
        self.three_part_date_year_first = re.compile(r'(?<![\d.]) (?P<a_year>\d{4}) (?P<b_month_or_day>([/-])\d{1,2}) (?P<c_day_or_month>\3\d{1,2}) (?![\d.])', re.VERBOSE)
        self.three_part_date_dmy = re.compile(r'(?<![\d.]) (?P<a_day>(?:0?[1-9]|1[0-9]|2[0-9]|3[01])([./-])) (?P<b_month>(?:0?[1-9]|1[0-2])\2) (?P<c_year>(?:\d\d){1,2}) (?![\d.])', re.VERBOSE)
        self.three_part_date_mdy = re.compile(r'(?<![\d.]) (?P<a_month>(?:0?[1-9]|1[0-2])([./-])) (?P<b_day>(?:0?[1-9]|1[0-9]|2[0-9]|3[01])\2) (?P<c_year>(?:\d\d){1,2}) (?![\d.])', re.VERBOSE)
        self.two_part_date = re.compile(r'(?<![\d.]) (?P<a_day_or_month>\d{1,2}([./-])) (?P<b_day_or_month>\d{1,2}\2) (?![\d.])', re.VERBOSE)
        self.time = re.compile(r'(?<!\w)\d{1,2}(?:(?::\d{2}){1,2}){1,2}(?![\d:])')
        self.en_time = re.compile(r'(?<![\w])(?P<a_time>\d{1,2}(?:(?:[.:]\d{2})){0,2}) ?(?P<b_am_pm>(?:[ap]m\b|[ap]\.m\.(?!\w)))', re.IGNORECASE)
        self.en_us_phone_number = re.compile(r"(?<![\d-])(?:[2-9]\d{2}[/-])?\d{3}-\d{4}(?![\d-])")
        self.en_numerical_identifiers = re.compile(r"(?<![\d-])\d+-(?:\d+-)+\d+(?![\d-])|(?<![\d/])\d+/(?:\d+/)+\d+(?![\d/])")
        self.en_us_zip_code = re.compile(r"(?<![\d-])\d{5}-\d{4}(?![\d-])")
        self.ordinal = re.compile(r'(?<![\w.])(?:\d{1,3}|\d{5,}|[3-9]\d{3})\.(?!\d)')
        self.english_ordinal = re.compile(r'\b(?:\d+(?:,\d+)*)?(?:1st|2nd|3rd|\dth)\b')
        self.english_decades = re.compile(r"\b(?:[12]\d)?\d0['’]?s\b")
        self.fraction = re.compile(r'(?<!\w)\d+/\d+(?![\d/])')
        self.amount = re.compile(r'(?<!\w)(?:\d+[\d,.]*-)(?!\w)')
        self.semester = re.compile(r'(?<!\w)(?P<a_semester>[WS]S|SoSe|WiSe)(?P<b_jahr>\d\d(?:/\d\d)?)(?!\w)', re.IGNORECASE)
        self.measurement = re.compile(r'(?<!\w)(?P<a_amount>[−+-]?\d*[,.]?\d+) ?(?P<b_unit>(?:mm|cm|dm|m|km)(?:\^?[23])?|bit|cent|eur|f|ft|g|ghz|h|hz|kg|l|lb|min|ml|qm|s|sek)(?!\w)', re.IGNORECASE)
        # auch Web2.0
        self.number_compound = re.compile(r'(?<!\w) (?:\d+-?[\p{L}@][\p{L}@-]* | [\p{L}@][\p{L}@-]*-?\d+(?:\.\d)?) (?!\w)', re.VERBOSE)
        self.number = re.compile(r"""(?<!\w|\d[.,]?)
                                     (?:[−+-]?              # optional sign
                                       (?:\d*               # optional digits before decimal point
                                       [.,])?               # optional decimal point
                                       \d+                  # digits
                                       (?:[eE][−+-]?\d+)?   # optional exponent
                                       |
                                       \d{1,3}(?:[.]\d{3})+(?:,\d+)?  # dot for thousands, comma for decimals: 1.999,95
                                       |
                                       \d{1,3}(?:,\d{3})+(?:[.]\d+)?  # comma for thousands, dot for decimals: 1,999.95
                                       )
                                     (?![.,]?\d)""", re.VERBOSE)
        self.ipv4 = re.compile(r"(?<!\w|\d[.,]?)(?:\d{1,3}[.]){3}\d{1,3}(?![.,]?\d)")
        self.section_number = re.compile(r"(?<!\w|\d[.,]?)(?:\d+[.])+\d+[.]?(?![.,]?\d)")

        # PUNCTUATION
        self.quest_exclam = re.compile(r"([!?]+)")
        # arrows
        self.space_right_arrow = re.compile(r'(-+)\s+(>)')
        self.space_left_arrow = re.compile(r'(<)\s+(-+)')
        self.arrow = re.compile(r'(-+>|<-+|[\u2190-\u21ff])')
        # parens
        self.paired_paren = re.compile(r'([(])(?!inn)([^()]*)([)])')
        self.paired_bracket = re.compile(r'(\[)([^][]*)(\])')
        self.paren = re.compile(r"""((?:(?<!\w)   # no alphanumeric character
                                       [[{(]      # opening paren
                                       (?=\w)) |  # alphanumeric character
                                     (?:(?<=\w)   # alphanumeric character
                                       []})]      # closing paren
                                       (?!\w)) |  # no alphanumeric character
                                     (?:^         # beginning of string
                                       []})]      # closing paren
                                       (?=\w)) |  # alphanumeric character
                                     (?:(?<=\w-)  # hyphen
                                       [)]        # closing paren
                                       (?=\w)))   # alphanumeric character
                                 """, re.VERBOSE)
        self.all_paren = re.compile(r"(?<=\s)[][(){}](?=\s)")
        self.de_slash = re.compile(r'(/+)(?!in(?:nen)?|en)')
        # English possessive and contracted forms
        self.en_trailing_apos = re.compile(r"(?<!..in|')(['’])(?!\w)")
        self.en_dms = re.compile(r"(?<=\w)(['’][dms])\b", re.IGNORECASE)
        self.en_llreve = re.compile(r"(?<=\w)(['’](?:ll|re|ve))\b", re.IGNORECASE)
        self.en_not = re.compile(r"(?<=\w)(n['’]t)\b", re.IGNORECASE)
        en_twopart_contractions = [r"\b(?P<p1>a)(?P<p2>lot)\b", r"\b(?P<p1>gon)(?P<p2>na)\b", r"\b(?P<p1>got)(?P<p2>ta)\b", r"\b(?P<p1>lem)(?P<p2>me)\b",
                                   r"\b(?P<p1>out)(?P<p2>ta)\b", r"\b(?P<p1>wan)(?P<p2>na)\b", r"\b(?P<p1>c'm)(?P<p2>on)\b",
                                   r"\b(?P<p1>more)(?P<p2>['’]n)\b", r"\b(?P<p1>d['’])(?P<p2>ye)\b", r"(?<!\w)(?P<p1>['’]t)(?P<p2>is)\b",
                                   r"(?<!\w)(?P<p1>['’]t)(?P<p2>was)\b", r"\b(?P<p1>there)(?P<p2>s)\b", r"\b(?P<p1>i)(?P<p2>m)\b",
                                   r"\b(?P<p1>you)(?P<p2>re)\b", r"\b(?P<p1>he)(?P<p2>s)\b", r"\b(?P<p1>she)(?P<p2>s)\b",
                                   r"\b(?P<p1>ai)(?P<p2>nt)\b", r"\b(?P<p1>are)(?P<p2>nt)\b", r"\b(?P<p1>is)(?P<p2>nt)\b",
                                   r"\b(?P<p1>do)(?P<p2>nt)\b", r"\b(?P<p1>does)(?P<p2>nt)\b", r"\b(?P<p1>did)(?P<p2>nt)\b",
                                   r"\b(?P<p1>i)(?P<p2>ve)\b", r"\b(?P<p1>you)(?P<p2>ve)\b", r"\b(?P<p1>they)(?P<p2>ve)\b",
                                   r"\b(?P<p1>have)(?P<p2>nt)\b", r"\b(?P<p1>has)(?P<p2>nt)\b", r"\b(?P<p1>can)(?P<p2>not)\b",
                                   r"\b(?P<p1>ca)(?P<p2>nt)\b", r"\b(?P<p1>could)(?P<p2>nt)\b", r"\b(?P<p1>wo)(?P<p2>nt)\b",
                                   r"\b(?P<p1>would)(?P<p2>nt)\b", r"\b(?P<p1>you)(?P<p2>ll)\b", r"\b(?P<p1>let)(?P<p2>s)\b"]
        en_threepart_contractions = [r"\b(?P<p1>du)(?P<p2>n)(?P<p3>no)\b", r"\b(?P<p1>wha)(?P<p2>dd)(?P<p3>ya)\b", r"\b(?P<p1>wha)(?P<p2>t)(?P<p3>cha)\b", r"\b(?P<p1>i)(?P<p2>'m)(?P<p3>a)\b"]
        # w/o, w/out, b/c, b/t, l/c, w/, d/c, u/s
        self.en_slash_words = re.compile(r"\b(?:w/o|w/out|b/t|l/c|b/c|d/c|u/s)\b|\bw/(?!\w)", re.IGNORECASE)
        # word--word
        self.en_twopart_contractions = [re.compile(contr, re.IGNORECASE) for contr in en_twopart_contractions]
        self.en_threepart_contractions = [re.compile(contr, re.IGNORECASE) for contr in en_threepart_contractions]
        # English hyphenated words
        if self.language == "en":
            nonbreaking_prefixes = utils.read_abbreviation_file("non-breaking_prefixes_%s.txt" % self.language)
            nonbreaking_suffixes = utils.read_abbreviation_file("non-breaking_suffixes_%s.txt" % self.language)
            nonbreaking_words = utils.read_abbreviation_file("non-breaking_hyphenated_words_%s.txt" % self.language)
            self.en_nonbreaking_prefixes = re.compile(r"(?<![\w-])(?:" + r'|'.join([re.escape(_) for _ in nonbreaking_prefixes]) + r")-[\w-]+", re.IGNORECASE)
            self.en_nonbreaking_suffixes = re.compile(r"\b[\w-]+-(?:" + r'|'.join([re.escape(_) for _ in nonbreaking_suffixes]) + r")(?![\w-])", re.IGNORECASE)
            self.en_nonbreaking_words = re.compile(r"\b(?:" + r'|'.join([re.escape(_) for _ in nonbreaking_words]) + r")\b", re.IGNORECASE)
        self.en_hyphen = re.compile(r"(?<=\w)-+(?=\w)")
        self.en_no = re.compile(r"\b(no\.)\s*(?=\d)", re.IGNORECASE)
        self.en_degree = re.compile(r"(?<=\d ?)°(?:F|C|Oe)\b", re.IGNORECASE)
        # quotation marks
        # L'Enfer, d'accord, O'Connor
        self.letter_apostrophe_word = re.compile(r"\b([dlo]['’]\p{L}+)\b", re.IGNORECASE)
        self.paired_double_latex_quote = re.compile(r"(?<!`)(``)([^`']+)('')(?!')")
        self.paired_single_latex_quote = re.compile(r"(?<!`)(`)([^`']+)(')(?!')")
        self.paired_single_quot_mark = re.compile(r"(['‚‘’])([^']+)(['‘’])")
        self.all_quote = re.compile(r"(?<=\s)(?:``|''|`|['‚‘’])(?=\s)")
        self.other_punctuation = re.compile(r'([#<>%‰€$£₤¥°@~*„“”‚‘"»«›‹,;:+×÷±≤≥=&–—])')
        self.en_quotation_marks = re.compile(r'([„“”‚‘’"»«›‹])')
        self.en_other_punctuation = re.compile(r'([#<>%‰€$£₤¥°@~*,;:+×÷±≤≥=&/–—-]+)')
        self.ellipsis = re.compile(r'\.{2,}|…+(?:\.{2,})?')
        self.dot_without_space = re.compile(r'(?<=\p{Ll}{2})(\.)(?=\p{Lu}\p{Ll}{2})')
        # self.dot = re.compile(r'(?<=[\w)])(\.)(?![\w])')
        self.dot = re.compile(r'(\.)')
        # Soft hyphen ­ „“

    def _split_on_boundaries(self, node, boundaries, token_class, lock_match=True):
        """"""
        n = len(boundaries)
        if n == 0:
            return
        token_dll = node.list
        prev_end = 0
        for i, (start, end, replacement) in enumerate(boundaries):
            original_spelling = None
            left_space_after, match_space_after = False, False
            left = node.value.text[prev_end:start]
            match = node.value.text[start:end]
            if replacement is not None:
                if match != replacement:
                    original_spelling = match
                    match = replacement
            right = node.value.text[end:]
            prev_end = end
            if left.endswith(" ") or match.startswith(" "):
                left_space_after = True
            if match.endswith(" ") or right.startswith(" "):
                match_space_after = True
            elif right == "":
                match_space_after = node.value.space_after
            left = left.strip()
            match = match.strip()
            right = right.strip()
            first_in_sentence, match_last_in_sentence, right_last_in_sentence = False, False, False
            if i == 0:
                first_in_sentence = node.value.first_in_sentence
            if i == n - 1:
                match_last_in_sentence = node.value.last_in_sentence
                if right != "":
                    match_last_in_sentence = False
                    right_last_in_sentence = node.value.last_in_sentence
            if left != "":
                token_dll.insert_left(Token(left, space_after=left_space_after, first_in_sentence=first_in_sentence), node)
                first_in_sentence = False
            token_dll.insert_left(Token(match, locked=lock_match,
                                        token_class=token_class,
                                        space_after=match_space_after,
                                        original_spelling=original_spelling,
                                        first_in_sentence=first_in_sentence,
                                        last_in_sentence=match_last_in_sentence),
                                  node)
            if i == n - 1 and right != "":
                token_dll.insert_left(Token(right, space_after=node.value.space_after, last_in_sentence=right_last_in_sentence), node)
        token_dll.remove(node)

    def _split_matches(self, regex, node, token_class="regular", repl=None, split_named_subgroups=True):
        boundaries = []
        split_groups = split_named_subgroups and len(regex.groupindex) > 0
        group_numbers = sorted(regex.groupindex.values())
        for m in regex.finditer(node.value.text):
            if split_groups:
                for g in group_numbers:
                    boundaries.append((m.start(g), m.end(g), None))
            else:
                if repl is None:
                    boundaries.append((m.start(), m.end(), None))
                else:
                    boundaries.append((m.start(), m.end(), m.expand(repl)))
        self._split_on_boundaries(node, boundaries, token_class)

    def _split_emojis(self, node, token_class="emoticon"):
        boundaries = []
        for m in re.finditer(r"\X", node.value.text):
            if m.end() - m.start() > 1:
                if re.search(r"[\p{Extended_Pictographic}\p{Emoji_Presentation}\uFE0F]", m.group()):
                    boundaries.append((m.start(), m.end(), None))
            else:
                if re.search(r"[\p{Extended_Pictographic}\p{Emoji_Presentation}]", m.group()):
                    boundaries.append((m.start(), m.end(), None))
        self._split_on_boundaries(node, boundaries, token_class)

    def _split_set(self, regex, node, items, token_class="regular", ignore_case=False):
        boundaries = []
        for m in regex.finditer(node.value.text):
            instance = m.group(0)
            if ignore_case:
                instance = instance.lower()
            if instance in items:
                boundaries.append((m.start(), m.end(), None))
        self._split_on_boundaries(node, boundaries, token_class)

    def _split_all_matches(self, regex, token_dll, token_class="regular", split_named_subgroups=True):
        """Turn matches for the regex into tokens."""
        for t in token_dll:
            if t.value.markup or t.value.locked:
                continue
            self._split_matches(regex, t, token_class, split_named_subgroups)

    def _split_all_emojis(self, token_dll, token_class="emoticon"):
        """Replace all emoji sequences"""
        for t in token_dll:
            if t.value.markup or t.value.locked:
                continue
            self._split_emojis(t, token_class)

    def _split_all_set(self, token_dll, regex, items, token_class="regular", ignore_case=False):
        """Turn all elements from items into separate tokens. (All elements
        need to be matched by regex.)"""
        for t in token_dll:
            if t.value.markup or t.value.locked:
                continue
            self._split_set(regex, t, items, token_class, ignore_case)

    def _split_abbreviations(self, token_dll, split_multipart_abbrevs=True):
        """Turn instances of abbreviations into tokens."""
        self._split_all_matches(self.single_letter_ellipsis, token_dll, "abbreviation")
        self._split_all_matches(self.and_cetera, token_dll, "abbreviation")
        self._split_all_matches(self.str_abbreviations, token_dll, "abbreviation")
        self._split_all_matches(self.nr_abbreviations, token_dll, "abbreviation")
        self._split_all_matches(self.single_token_abbreviation, token_dll, "abbreviation")
        self._split_all_matches(self.single_letter_abbreviation, token_dll, "abbreviation")
        # TODO: lookbehind
        # text = self._replace_regex(text, self.ps, "abbreviation")

        for t in token_dll:
            if t.value.markup or t.value.locked:
                continue
            boundaries = []
            for m in self.abbreviation.finditer(t.value.text):
                instance = m.group(0)
                if split_multipart_abbrevs and self.multipart_abbreviation.fullmatch(instance):
                    start, end = m.span(0)
                    s = start
                    for i, c in enumerate(instance, start=1):
                        if c == ".":
                            boundaries.append((s, start + i, None))
                            s = start + i
                else:
                    boundaries.append((m.start(), m.end(), None))
            self._split_on_boundaries(t, boundaries, "abbreviation")

    def _check_spaces(self, tokens, original_text):
        """Compare the tokens with the original text to see which tokens had
        trailing whitespace (to be able to annotate SpaceAfter=No) and
        which tokens contained internal whitespace (to be able to
        annotate OriginalSpelling="...").

        """
        extra_info = ["" for _ in tokens]
        normalized = self.junk_between_spaces.sub(" ", original_text)
        normalized = self.spaces.sub(" ", normalized)
        normalized = normalized.strip()
        for token_index, t in enumerate(tokens):
            original_spelling = None
            token = t.token
            token_length = len(token)
            if normalized.startswith(token):
                normalized = normalized[token_length:]
            else:
                orig = []
                for char in token:
                    first_char = None
                    while first_char != char:
                        try:
                            first_char = normalized[0]
                            normalized = normalized[1:]
                            orig.append(first_char)
                        except IndexError:
                            warnings.warn("Error aligning tokens with original text!\nOriginal text: '%s'\nToken: '%s'\nRemaining normalized text: '%s'\nValue of orig: '%s'" % (original_text, token, normalized, "".join(orig)))
                            break
                original_spelling = "".join(orig)
            m = self.starts_with_junk.search(normalized)
            if m:
                if original_spelling is None:
                    original_spelling = token
                original_spelling += normalized[:m.end()]
                normalized = normalized[m.end():]
            if original_spelling is not None:
                extra_info[token_index] = 'OriginalSpelling="%s"' % original_spelling
            if len(normalized) > 0:
                if normalized.startswith(" "):
                    normalized = normalized[1:]
                else:
                    if len(extra_info[token_index]) > 0:
                        extra_info[token_index] = ", " + extra_info[token_index]
                    extra_info[token_index] = "SpaceAfter=No" + extra_info[token_index]
        try:
            assert len(normalized) == 0
        except AssertionError:
            warnings.warn("AssertionError in this paragraph: '%s'\nTokens: %s\nRemaining normalized text: '%s'" % (original_text, tokens, normalized))
        return extra_info

    def _match_xml(self, tokens, elements):
        """"""
        agenda = list(reversed(tokens))
        for element in elements:
            original_text = unicodedata.normalize("NFC", element.text)
            normalized = self.junk_between_spaces.sub(" ", original_text)
            normalized = self.spaces.sub(" ", normalized)
            normalized = normalized.strip()
            output = []
            while len(normalized) > 0:
                t = agenda.pop()
                original_spelling = None
                extra_info = ""
                token = t.token
                if normalized.startswith(token):
                    normalized = normalized[len(token):]
                elif token.startswith(normalized):
                    agenda.append(Token(token[len(normalized):].lstrip(), t.token_class))
                    token = normalized
                    normalized = ""
                else:
                    orig = []
                    processed = []
                    for char in token:
                        first_char = None
                        while first_char != char:
                            try:
                                first_char = normalized[0]
                                normalized = normalized[1:]
                                orig.append(first_char)
                            except IndexError:
                                warnings.warn("Error aligning tokens with original text!\nOriginal text: '%s'\nToken: '%s'\nRemaining normalized text: '%s'\nValue of orig: '%s'" % (original_text, token, normalized, "".join(orig)))
                                break
                        else:
                            processed.append(char)
                    if len(processed) != len(token):
                        agenda.append(Token(token[len(processed):].lstrip(), t.token_class))
                        token = token[:len(processed)]
                    original_spelling = "".join(orig)
                m = self.starts_with_junk.search(normalized)
                if m:
                    if original_spelling is None:
                        original_spelling = token
                    original_spelling += normalized[:m.end()]
                    normalized = normalized[m.end():]
                if original_spelling is not None:
                    extra_info = 'OriginalSpelling="%s"' % original_spelling
                if len(normalized) > 0:
                    if normalized.startswith(" "):
                        normalized = normalized[1:]
                    else:
                        if len(extra_info) > 0:
                            extra_info = ", " + extra_info
                        extra_info = "SpaceAfter=No" + extra_info
                output.append("\t".join((token, t.token_class, extra_info)))
            if len(output) > 0:
                tokenized_text = "\n" + "\n".join(output) + "\n"
            else:
                tokenized_text = "\n"
            if element.type == "text":
                element.element.text = tokenized_text
            elif element.type == "tail":
                element.element.tail = tokenized_text
        try:
            assert len(agenda) == 0
        except AssertionError:
            warnings.warn("AssertionError: %d tokens left over" % len(agenda))
        return elements

    def _tokenize(self, token_dll):
        """Tokenize paragraph (may contain newlines) according to the
        guidelines of the EmpiriST 2015 shared task on automatic
        linguistic annotation of computer-mediated communication /
        social media.

        """
        for t in token_dll:
            if t.value.markup or t.value.locked:
                continue
            # convert to Unicode normal form C (NFC)
            t.value.text = unicodedata.normalize("NFC", t.value.text)
            # normalize whitespace
            t.value.text = self.spaces.sub(" ", t.value.text)
            # get rid of control characters
            t.value.text = self.controls.sub("", t.value.text)
            # get rid of isolated variation selectors
            t.value.text = self.stranded_variation_selector.sub("", t.value.text)
            # normalize whitespace
            t.value.text = self.spaces.sub(" ", t.value.text)

        # Some tokens are allowed to contain whitespace. Get those out
        # of the way first.
        # - XML tags
        self._split_all_matches(self.xml_declaration, token_dll, "XML_tag")
        self._split_all_matches(self.tag, token_dll, "XML_tag")
        # - email address obfuscation may involve spaces
        self._split_all_matches(self.email, token_dll, "email_address")

        # Emoji sequences can contain zero-width joiners. Get them out
        # of the way next
        self._split_all_matches(self.unicode_flags, token_dll, "emoticon")
        self._split_all_emojis(token_dll, "emoticon")

        for t in token_dll:
            if t.value.markup or t.value.locked:
                continue
            # get rid of other junk characters
            t.value.text = self.other_nasties.sub("", t.value.text)
            # normalize whitespace
            t.value.text = self.spaces.sub(" ", t.value.text)
            # Some emoticons contain erroneous spaces. We fix this.
            # TODO: original_spelling
            t.value.text = self.space_emoticon.sub(r'\1\2', t.value.text)
            # Split on whitespace
            wt = t.value.text.split()
            n_wt = len(wt)
            for i, tok in enumerate(wt):
                if i == n_wt - 1:
                    token_dll.insert_left(Token(tok, space_after=t.value.space_after), t)
                else:
                    token_dll.insert_left(Token(tok, space_after=True), t)
            token_dll.remove(t)

        # urls
        self._split_all_matches(self.simple_url_with_brackets, token_dll, "URL")
        self._split_all_matches(self.simple_url, token_dll, "URL")
        self._split_all_matches(self.doi, token_dll, "URL")
        # TODO: lookbehind
        self._split_all_matches(self.doi_with_space, token_dll, "URL")
        self._split_all_matches(self.url_without_protocol, token_dll, "URL")
        self._split_all_matches(self.reddit_links, token_dll, "URL")

        # XML entities
        self._split_all_matches(self.entity, token_dll, "XML_entity")

        # emoticons
        # TODO: lookbehind
        self._split_all_matches(self.heart_emoticon, token_dll, "emoticon")
        self._split_all_matches(self.emoticon, token_dll, "emoticon")

        # mentions, hashtags
        self._split_all_matches(self.mention, token_dll, "mention")
        self._split_all_matches(self.hashtag, token_dll, "hashtag")
        # action words
        self._split_all_matches(self.action_word, token_dll, "action_word")
        # underline
        # TODO: match across multiple tokens
        self._split_all_matches(self.underline, token_dll)
        # textual representations of emoji
        self._split_all_matches(self.emoji, token_dll, "emoticon")

        # tokens with + or &
        self._split_all_matches(self.token_with_plus_ampersand, token_dll)
        self._split_all_set(token_dll, self.simple_plus_ampersand_candidates, self.simple_plus_ampersand, ignore_case=True)

        # camelCase
        if self.split_camel_case:
            self._split_all_matches(self.camel_case_token, token_dll)
            self._split_all_set(token_dll, self.simple_camel_case_candidates, self.simple_camel_case_tokens)
            self._split_all_matches(self.in_and_innen, token_dll)
            # TODO: split to the left of match
            # paragraph = self.camel_case.sub(r' \1', paragraph)

        # gender star
        self._split_all_matches(self.gender_star, token_dll)

        # English possessive and contracted forms
        if self.language == "en":
            self._split_all_matches(self.english_decades, token_dll, "number_compound")
            self._split_all_matches(self.en_dms, token_dll)
            self._split_all_matches(self.en_llreve, token_dll)
            self._split_all_matches(self.en_not, token_dll)
            # TODO: split to the left of match
            # paragraph = self.en_trailing_apos.sub(r' \1', paragraph)
            for contraction in self.en_twopart_contractions:
                self._split_all_matches(contraction, token_dll)
            for contraction in self.en_threepart_contractions:
                self._split_all_matches(contraction, token_dll)
            # TODO: lookahead
            # paragraph = self._replace_regex(paragraph, self.en_no, "regular")
            # TODO: lookbehind
            # paragraph = self._replace_regex(paragraph, self.en_degree, "regular")
            self._split_all_matches(self.en_nonbreaking_words, token_dll)
            self._split_all_matches(self.en_nonbreaking_prefixes, token_dll)
            self._split_all_matches(self.en_nonbreaking_suffixes, token_dll)

        # remove known abbreviations
        split_abbreviations = False if self.language == "en" else True
        self._split_abbreviations(token_dll, split_multipart_abbrevs=split_abbreviations)

        # DATES AND NUMBERS
        # dates
        split_dates = False if self.language == "en" else True
        self._split_all_matches(self.three_part_date_year_first, token_dll, "date", split_named_subgroups=split_dates)
        self._split_all_matches(self.three_part_date_dmy, token_dll, "date", split_named_subgroups=split_dates)
        self._split_all_matches(self.three_part_date_mdy, token_dll, "date", split_named_subgroups=split_dates)
        self._split_all_matches(self.two_part_date, token_dll, "date", split_named_subgroups=split_dates)
        # time
        if self.language == "en":
            self._split_all_matches(self.en_time, token_dll, "time")
        self._split_all_matches(self.time, token_dll, "time")
        # US phone numbers and ZIP codes
        if self.language == "en":
            self._split_all_matches(self.en_us_phone_number, token_dll, "number")
            self._split_all_matches(self.en_us_zip_code, token_dll, "number")
            self._split_all_matches(self.en_numerical_identifiers, token_dll, "number")
        # ordinals
        if self.language == "de":
            self._split_all_matches(self.ordinal, token_dll, "ordinal")
        elif self.language == "en":
            self._split_all_matches(self.english_ordinal, token_dll, "ordinal")
        # fractions
        self._split_all_matches(self.fraction, token_dll, "number")
        # amounts (1.000,-)
        self._split_all_matches(self.amount, token_dll, "amount")
        # semesters
        self._split_all_matches(self.semester, token_dll, "semester")
        # measurements
        self._split_all_matches(self.measurement, token_dll, "measurement")
        # number compounds
        self._split_all_matches(self.number_compound, token_dll, "number_compound")
        # numbers
        self._split_all_matches(self.number, token_dll, "number")
        self._split_all_matches(self.ipv4, token_dll, "number")
        self._split_all_matches(self.section_number, token_dll, "number")

        # (clusters of) question marks and exclamation marks
        self._split_all_matches(self.quest_exclam, token_dll, "symbol")
        # arrows
        # TODO:
        # paragraph = self.space_right_arrow.sub(r'\1\2', paragraph)
        # paragraph = self.space_left_arrow.sub(r'\1\2', paragraph)
        self._split_all_matches(self.arrow, token_dll, "symbol")
        # parens
        # TODO:
        # paragraph = self.paired_paren.sub(r' \1 \2 \3 ', paragraph)
        # paragraph = self.paired_bracket.sub(r' \1 \2 \3 ', paragraph)
        self._split_all_matches(self.paren, token_dll, "symbol")
        # paragraph = self._replace_regex(paragraph, self.all_paren, "symbol")
        # slash
        if self.language == "en":
            self._split_all_matches(self.en_slash_words, token_dll, "regular")
        if self.language == "de":
            self._split_all_matches(self.de_slash, token_dll, "symbol")
        # O'Connor and French omitted vocals: L'Enfer, d'accord
        self._split_all_matches(self.letter_apostrophe_word, token_dll)
        # LaTeX-style quotation marks
        # TODO:
        # paragraph = self.paired_double_latex_quote.sub(r' \1 \2 \3 ', paragraph)
        # paragraph = self.paired_single_latex_quote.sub(r' \1 \2 \3 ', paragraph)
        # single quotation marks, apostrophes
        # TODO:
        # paragraph = self.paired_single_quot_mark.sub(r' \1 \2 \3 ', paragraph)
        # paragraph = self._replace_regex(paragraph, self.all_quote, "symbol")
        # other punctuation symbols
        # paragraph = self._replace_regex(paragraph, self.dividing_line, "symbol")
        if self.language == "en":
            self._split_all_matches(self.en_hyphen, token_dll, "symbol")
            self._split_all_matches(self.en_quotation_marks, token_dll, "symbol")
            self._split_all_matches(self.en_other_punctuation, token_dll, "symbol")
        else:
            self._split_all_matches(self.other_punctuation, token_dll, "symbol")
        # ellipsis
        self._split_all_matches(self.ellipsis, token_dll, "symbol")
        # dots
        # paragraph = self.dot_without_space.sub(r' \1 ', paragraph)
        self._split_all_matches(self.dot_without_space, token_dll, "symbol")
        # paragraph = self.dot.sub(r' \1 ', paragraph)
        self._split_all_matches(self.dot, token_dll, "symbol")

        return token_dll

    def tokenize(self, paragraph):
        """An alias for tokenize_paragraph"""
        return self.tokenize_paragraph(paragraph)

    def tokenize_file(self, filename, parsep_empty_lines=True):
        """Tokenize file and yield tokenized paragraphs."""
        with open(filename) as f:
            if parsep_empty_lines:
                paragraphs = utils.get_paragraphs(f)
            else:
                paragraphs = (line for line in f if line.strip() != "")
            tokenized_paragraphs = map(self.tokenize_paragraph, paragraphs)
            for tp in tokenized_paragraphs:
                if tp:
                    yield tp

    def tokenize_paragraph(self, paragraph):
        """Tokenize paragraph (may contain newlines) according to the
        guidelines of the EmpiriST 2015 shared task on automatic
        linguistic annotation of computer-mediated communication /
        social media.

        """
        token_dll = doubly_linked_list.DLL([Token(paragraph, first_in_sentence=True, last_in_sentence=True)])
        token_dll = self._tokenize(token_dll)
        return [t.text for t in token_dll.to_list()]
        # # convert paragraph to Unicode normal form C (NFC)
        # paragraph = unicodedata.normalize("NFC", paragraph)

        # tokens = self._tokenize(paragraph)

        # if len(tokens) == 0:
        #     return []

        # if self.extra_info:
        #     extra_info = self._check_spaces(tokens, paragraph)

        # tokens, token_classes = zip(*tokens)
        # if self.token_classes:
        #     if self.extra_info:
        #         return list(zip(tokens, token_classes, extra_info))
        #     else:
        #         return list(zip(tokens, token_classes))
        # else:
        #     if self.extra_info:
        #         return list(zip(tokens, extra_info))
        #     else:
        #         return list(tokens)

    def tokenize_xml(self, xml, is_file=True):
        """Tokenize XML file or XML string according to the guidelines of the
        EmpiriST 2015 shared task on automatic linguistic annotation
        of computer-mediated communication / social media.

        """
        token_dll = utils.parse_xml_to_token_dll(xml, is_file)
        self._tokenize(token_dll)
        return [t.text for t in token_dll.to_list()]
        # whole_text = " ".join((e.text for e in elements))

        # # convert paragraph to Unicode normal form C (NFC)
        # whole_text = unicodedata.normalize("NFC", whole_text)

        # tokens = self._tokenize(whole_text)

        # tokenized_elements = self._match_xml(tokens, elements)
        # xml = ET.tostring(tokenized_elements[0].element, encoding="unicode").rstrip()

        # tokens = [l.split("\t") for l in xml.split("\n")]
        # if self.token_classes:
        #     if self.extra_info:
        #         return [t if len(t) == 3 else (t[0], None, None) for t in tokens]
        #     else:
        #         return [(t[0], t[1]) if len(t) == 3 else (t[0], None) for t in tokens]
        # else:
        #     if self.extra_info:
        #         return [(t[0], t[2]) if len(t) == 3 else (t[0], None) for t in tokens]
        #     else:
        #         return [t[0] for t in tokens]
