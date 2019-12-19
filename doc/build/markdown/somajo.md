# somajo package

## Subpackages


* somajo.test package


    * Submodules


    * somajo.test.test_sentence_splitter module


    * somajo.test.test_somajo module


    * somajo.test.test_tokenizer module


    * Module contents


## Submodules

## somajo.cli module


#### somajo.cli.arguments()

#### somajo.cli.main()
## somajo.doubly_linked_list module


#### class somajo.doubly_linked_list.DLL(iterable=None)
Bases: `object`


### append(item)

### extend(iterable)

### insert_left(item, ref_element)

### next_matching(item, attrgetter, value, ignore_attrgetter=None, ignore_value=None)

### previous_matching(item, attrgetter, value, ignore_attrgetter=None, ignore_value=None)

### remove(element)

### to_list()

#### class somajo.doubly_linked_list.DLLElement(val=None, prv=None, nxt=None, lst=None)
Bases: `object`

## somajo.sentence_splitter module


#### class somajo.sentence_splitter.SentenceSplitter(is_tuple=False, language='de_CMC')
Bases: `object`


### split(tokenized_paragraph)
Split tokenized_paragraph into sentences.


### split_xml(tokenized_xml, eos_tags={})
Split tokenized XML into sentences.

## somajo.somajo module


#### class somajo.somajo.SoMaJo(language, \*, split_camel_case=False, split_sentences=True)
Bases: `object`

Tokenization and sentence splitting.


* **Parameters**

    
    * **language** (*{'de_CMC'**, **'en_PTB'}*) – Language-specific tokenization rules.


    * **split_camel_case** (*bool**, **(**default=False**)*) – Split words written in camelCase (excluding established names and terms).


    * **split_sentences** (*bool**, **(**default=True**)*) – Perform sentence splitting in addition to tokenization.



### paragraph_separators( = {'empty_lines', 'single_newlines'})

### supported_languages( = {'de_CMC', 'en_PTB'})

### tokenize_text(paragraphs, \*, parallel=1)
Split paragraphs of text into sequences of tokens.


* **Parameters**

    **paragraphs** (*iterable*) – An iterable of single paragraphs of text.



* **Yields**

    *list* – The `Token` objects in a single sentence or paragraph
    (depending on the value of `split_sentences`).


### Examples

Tokenization and sentence splitting; print one sentence per
line:

```python
>>> paragraphs = ["Heyi:)", "Was machst du morgen Abend?! Lust auf Film?;-)"]
>>> tokenizer = SoMaJo("de_CMC")
>>> sentences = tokenizer.tokenize_text(paragraphs)
>>> for sentence in sentences:
...     print(" ".join([token.text for token in sentence]))
...
Heyi :)
Was machst du morgen Abend ?!
Lust auf Film ? ;-)
```

Only tokenization; print one paragraph per line:

```python
>>> tokenizer = SoMaJo("de_CMC", split_sentences=False)
>>> tokenized_paragraphs = tokenizer.tokenize_text(paragraphs)
>>> for paragraph in tokenized_paragraphs:
...     print(" ".join([token.text for token in paragraph]))
...
Heyi :)
Was machst du morgen Abend ?! Lust auf Film ? ;-)
```

Tokenization and sentence splitting; print one token per line
with token classes and extra information; print an empty line
after each sentence:

```python
>>> sentences = tokenizer.tokenize_text(paragraphs)
>>> for sentence in sentences:
...     for token in sentence:
...         print("{}   {}      {}".format(token.text, token.token_class, token.extra_info))
...     print()
...
>>> for sentence in sentences:
...     for token in sentence:
...         print("{}   {}      {}".format(token.text, token.token_class, token.extra_info))
...     print()
...
Heyi    regular SpaceAfter=No
:)      emoticon
​
Was     regular
machst  regular
du      regular
morgen  regular
Abend   regular SpaceAfter=No
?!      symbol
​
Lust    regular
auf     regular
Film    regular SpaceAfter=No
?       symbol  SpaceAfter=No
;-)     emoticon
​
```


### tokenize_text_file(text_file, paragraph_separator, \*, parallel=1)
Split the contents of a text file into sequences of tokens.


* **Parameters**

    
    * **text_file** (*str** or **file-like object*) – Either a filename or a file-like object containing text.


    * **paragraph_separator** (*{'single_newlines'**, **'empty_lines'}*) – How are paragraphs separated in the input? Is there one
    paragraph per line (‘single_newlines’) or do paragraphs
    span several lines and are separated by ‘empty_lines’?


    * **parallel** (*int**, **(**default=1**)*) – Number of processes to use.



* **Yields**

    *list* – The `Token` objects in a single sentence or paragraph
    (depending on the value of `split_sentences`).


### Examples

Tokenization and sentence splitting; input file with
paragraphs separated by empty lines; print one token per line
with token classes and extra information; print an empty line
after each sentence:

```python
>>> with open("example_empty_lines.txt") as f:
...     print(f.read())
...
Heyi:)
​
Was machst du morgen Abend?! Lust auf Film?;-)
>>> sentences = tokenizer.tokenize_text_file("example_empty_lines.txt", paragraph_separator="single_newlines")
>>> for sentence in sentences:
...     for token in sentence:
...         print("{}   {}      {}".format(token.text, token.token_class, token.extra_info))
...     print()
...
Heyi    regular SpaceAfter=No
:)      emoticon
​
Was     regular
machst  regular
du      regular
morgen  regular
Abend   regular SpaceAfter=No
?!      symbol
​
Lust    regular
auf     regular
Film    regular SpaceAfter=No
?       symbol  SpaceAfter=No
;-)     emoticon
​
```

Tokenization and sentence splitting; input file with
paragraphs separated by single newlines; print one sentence
per line:

```python
>>> with open("example_single_newlines.txt", encoding="utf-8") as f:
...     print(f.read())
...
Heyi:)
Was machst du morgen Abend?! Lust auf Film?;-)
>>> tokenizer = SoMaJo("de_CMC")
>>> with open("example_empty_lines.txt", encoding="utf-8") as f:
...     sentences = tokenizer.tokenize_text_file(f, paragraph_separator="empty_lines")
...     for sentence in sentences:
...         print(" ".join([token.text for token in sentence]))
...
Heyi :)
Was machst du morgen Abend ?!
Lust auf Film ? ;-)
```


### tokenize_xml(xml_data, eos_tags, \*, strip_tags=False, parallel=1)
Split a string of XML data into sequences of tokens.


* **Parameters**

    
    * **xml_data** (*str*) – A string containing XML data.


    * **eos_tags** (*iterable*) – XML tags that constitute sentence breaks, i.e. tags that
    do not occur in the middle of a sentence. For HTML input,
    you might use the following list of tags: `['title',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
    'div', 'ol', 'ul', 'dl', 'table']`


    * **strip_tags** (*bool**, **(**default=False**)*) – Remove the XML tags from the output.


    * **parallel** (*int**, **(**default=1**)*) – Number of processes to use.



* **Yields**

    *list* – The `Token` objects in a single sentence or stretch of
    XML delimited by `eos_tags` (depending on the value of
    `split_sentences`).


### Examples

Tokenization and sentence splitting; print one token per line
and an empty line after each sentence:

```python
>>> xml = "<html><body><p>Heyi:)</p><p>Was machst du morgen Abend?! Lust auf Film?;-)</p></body></html>"
>>> eos_tags = "title h1 h2 h3 h4 h5 h6 p br hr div ol ul dl table".split()
>>> tokenizer = SoMaJo("de_CMC")
>>> sentences = tokenizer.tokenize_xml(xml, eos_tags)
>>> for sentence in sentences:
...     for token in sentence:
...         print(token.text)
...     print()
...
<html>
<body>
<p>
Heyi
:)
</p>
​
<p>
Was
machst
du
morgen
Abend
?!
​
Lust
auf
Film
?
;-)
</p>
</body>
</html>
​
```

Tokenization and sentence splitting; strip XML tags from the
output and print one sentence per line

```python
>>> sentences = tokenizer.tokenize_xml(xml, eos_tags, strip_tags=True)
>>> for sentence in sentences:
...     print(" ".join([token.text for token in sentence]))
...
Heyi :)
Was machst du morgen Abend ?!
Lust auf Film ? ;-)
```

Only tokenization; print one chunk of XML (delimited by
`eos_tags`) per line:

```python
>>> tokenizer = SoMaJo("de_CMC", split_sentences=False)
>>> chunks = tokenizer.tokenize_xml(xml, eos_tags)
>>> for chunk in chunks:
...     print(" ".join([token.text for token in chunk]))
...
<html> <body> <p> Heyi :) </p>
<p> Was machst du morgen Abend ?! Lust auf Film ? ;-) </p> </body> </html>
```


### tokenize_xml_file(xml_file, eos_tags, \*, strip_tags=False, parallel=1)
Split the contents of an xml file into sequences of tokens.


* **Parameters**

    
    * **xml_file** (*str** or **file-like object*) – A file containing XML data. Either a filename or a
    file-like object.


    * **eos_tags** (*iterable*) – XML tags that constitute sentence breaks, i.e. tags that
    do not occur in the middle of a sentence. For HTML input,
    you might use the following list of tags: `['title',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
    'div', 'ol', 'ul', 'dl', 'table']`


    * **strip_tags** (*bool**, **(**default=False**)*) – Remove the XML tags from the output.


    * **parallel** (*int**, **(**default=1**)*) – Number of processes to use.



* **Yields**

    *list* – The `Token` objects in a single sentence or stretch of
    XML delimited by `eos_tags` (depending on the value of
    `split_sentences`).


### Examples

Tokenization and sentence splitting; print one token per line
and an empty line after each sentence:

```python
>>> with open("example.xml") as f:
...     print(f.read())
...
<html>
  <body>
    <p>Heyi:)</p>
    <p>Was machst du morgen Abend?! Lust auf Film?;-)</p>
  </body>
</html>
>>> eos_tags = "title h1 h2 h3 h4 h5 h6 p br hr div ol ul dl table".split()
>>> tokenizer = SoMaJo("de_CMC")
>>> sentences = tokenizer.tokenize_xml_file("example.xml", eos_tags)
>>> for sentence in sentences:
...     for token in sentence:
...         print(token)
...     print()
...
<html>
<body>
<p>
Heyi
:)
</p>
​
<p>
Was
machst
du
morgen
Abend
?!
​
Lust
auf
Film
?
;-)
</p>
</body>
</html>
​
```

Tokenization and sentence splitting; strip XML tags from the
output and print one sentence per line:

```python
>>> with open("example.xml") as f:
...     sentences = tokenizer.tokenize_xml_file(f, eos_tags, strip_tags=True)
...     for sentence in sentences:
...         print(" ".join(token.text for token in sentence))
...
Heyi :)
Was machst du morgen Abend ?!
Lust auf Film ? ;-)
```

Only tokenization; print one token per line

```python
>>> tokenizer = SoMaJo("de_CMC", split_sentences=False)
>>> chunks = tokenizer.tokenize_xml_file("example.xml", eos_tags)
>>> for chunk in chunks:
...     for token in chunk:
...         print(token.text)
...
<html>
<body>
<p>
Heyi
:)
</p>
<p>
Was
machst
du
morgen
Abend
?!
Lust
auf
Film
?
;-)
</p>
</body>
</html>
```

## somajo.token module


#### class somajo.token.Token(text, \*, markup=False, markup_class=None, markup_eos=None, locked=False, token_class=None, space_after=True, original_spelling=None, first_in_sentence=False, last_in_sentence=False)
Bases: `object`

Token objects store a piece of text (in the end a single token) with additional information.


* **Parameters**

    
    * **text** (*str*) – The text that makes up the token object


    * **markup** (*bool**, **(**default=False**)*) – Is the token a markup token?


    * **markup_class** (*{'start'**, **'end'}**, **optional** (**default=None**)*) – If markup=True, then markup_class must be either “start” or “end”.


    * **markup_eos** (*bool**, **optional** (**default=None**)*) – Is the markup token a sentence boundary?


    * **locked** (*bool**, **(**default=False**)*) – Mark the token as locked.


    * **token_class** (*str**, **optional** (**default=None**)*) – The class of the token, e.g. “regular”, “emoticon”, “url”, etc.


    * **space_after** (*bool**, **(**default=True**)*) – Was there a space after the token in the original data?


    * **original_spelling** (*str**, **optional** (**default=None**)*) – The original spelling of the token, if it is different from the one in text.


    * **first_in_sentence** (*bool**, **(**default=False**)*) – Is it the first token of a sentence?


    * **last_in_sentence** (*bool**, **(**default=False**)*) – Is it the last token of a sentence?



### property extra_info()
String representation of extra information.


* **Returns**

    A string representation of the space_after and original_spelling attributes.



* **Return type**

    str


## somajo.tokenizer module


#### class somajo.tokenizer.Tokenizer(split_camel_case=False, token_classes=False, extra_info=False, language='de_CMC')
Bases: `object`


### tokenize(paragraph)
An alias for tokenize_paragraph


### tokenize_file(filename, parsep_empty_lines=True)
Tokenize utf-8-encoded text file and yield tokenized paragraphs.


### tokenize_paragraph(paragraph)
Tokenize paragraph (may contain newlines) according to the
guidelines of the EmpiriST 2015 shared task on automatic
linguistic annotation of computer-mediated communication /
social media.


### tokenize_xml(xml, is_file=True, eos_tags=None)
Tokenize XML file or XML string according to the guidelines of the
EmpiriST 2015 shared task on automatic linguistic annotation
of computer-mediated communication / social media.

## somajo.utils module


#### class somajo.utils.SaxTokenHandler(eos_tags=None)
Bases: `xml.sax.handler.ContentHandler`


### characters(data)
Receive notification of character data.

The Parser will call this method to report each chunk of
character data. SAX parsers may return all contiguous
character data in a single chunk, or they may split it into
several chunks; however, all of the characters in any single
event must come from the same external entity so that the
Locator provides useful information.


### endElement(name)
Signals the end of an element in non-namespace mode.

The name parameter contains the name of the element type, just
as with the startElement event.


### startElement(name, attrs)
Signals the start of an element in non-namespace mode.

The name parameter contains the raw XML 1.0 name of the
element type as a string and the attrs parameter holds an
instance of the Attributes class containing the attributes of
the element.


#### somajo.utils.escape_xml(string)
Escape “&”, “<” and “>” in string.


#### somajo.utils.escape_xml_tokens(tokens)

#### somajo.utils.get_paragraphs_dll(text_file, paragraph_separator='empty_lines')
Generator for the paragraphs in the file.


#### somajo.utils.get_paragraphs_str(fh, paragraph_separator='empty_lines')
Generator for the paragraphs in the file.


#### somajo.utils.incremental_xml_parser(f, eos_tags=None)

#### somajo.utils.parse_xml(xml, is_file=True)
Return a list of XML elements and their text/tail as well as the
whole text of the document.


#### somajo.utils.read_abbreviation_file(filename)
Return the abbreviations from the given filename.


#### somajo.utils.xml_chunk_generator(data, is_file=True, eos_tags=None)
Parse the XML data and yield doubly linked lists of Token objects
that are delimited by eos_tags.

## somajo.version module

## Module contents
