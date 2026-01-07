import re
from io import StringIO
from markdown import Markdown


def remove_emote_text(text: str):
    """Removes emotes from text responses, which LLMs tend to place between *.

    Args:
        text (str): The response text passed, which may contain emotes.

    Returns:
        text: The response string with any strings between * removed.
    """
    while True:
        start = text.find("*")
        if start == -1:
            break
        end = text.find("*", start + 1)
        if end == -1:
            break
        text = text[:start] + text[end + 1 :]
    return text


def remove_emojis(text: str) -> str:
    """Removes emoji characters from text.

    Emojis don't work well with TTS - they either get skipped, read as
    "emoji" or produce weird sounds depending on the provider.

    Args:
        text (str): The text that may contain emojis.

    Returns:
        str: The text with emojis removed.
    """
    # Comprehensive emoji pattern covering most Unicode emoji ranges
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U00002702-\U000027b0"  # dingbats
        "\U000024c2-\U0001f251"  # enclosed characters
        "\U0001f900-\U0001f9ff"  # supplemental symbols & pictographs
        "\U0001fa00-\U0001fa6f"  # chess symbols
        "\U0001fa70-\U0001faff"  # symbols & pictographs extended-A
        "\U00002600-\U000026ff"  # misc symbols
        "\U00002700-\U000027bf"  # dingbats
        "\U0001f000-\U0001f02f"  # mahjong tiles
        "\U0001f0a0-\U0001f0ff"  # playing cards
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def extract_markdown_link_text(text: str) -> str:
    """Extracts link text from Markdown links, removing the URL.

    Converts [link text](url) to just "link text" so TTS reads the
    descriptive text instead of the URL.

    Args:
        text (str): Text that may contain Markdown links.

    Returns:
        str: Text with Markdown links converted to just the link text.
    """
    # Pattern matches [link text](url) and captures just the link text
    markdown_link_pattern = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    return markdown_link_pattern.sub(r"\1", text)


def remove_links(text: str):
    """Removes standalone URLs from text.

    Note: Call extract_markdown_link_text() first to preserve link text
    from Markdown links before this strips remaining raw URLs.

    Args:
        text (str): Text that may contain URLs.

    Returns:
        tuple: (cleaned_text, contains_links)
    """
    # Regular expression pattern to match URLs
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )

    # Find all URLs in the text
    urls = url_pattern.findall(text)
    contains_links = bool(urls)

    # Replace all URLs with an empty string
    cleaned_text = url_pattern.sub("", text)

    return cleaned_text, contains_links


def remove_code_blocks(text: str):
    # Regular expression pattern to match code blocks enclosed in triple backticks
    code_block_pattern = re.compile(r"```.*?```", re.DOTALL)

    # Find all code blocks in the text
    code_blocks = code_block_pattern.findall(text)
    contains_code_blocks = bool(code_blocks)

    # Replace all code blocks with an empty string
    cleaned_text = code_block_pattern.sub("", text)

    return cleaned_text, contains_code_blocks


def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# patching Markdown
Markdown.output_formats["plain"] = unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False


def remove_markdown(text: str):
    return __md.convert(text)


def cleanup_text(text: str):
    """Cleans up text for TTS playback.

    Removes/transforms elements that don't work well with text-to-speech:
    - Extracts link text from Markdown links [text](url) → text
    - Removes standalone URLs
    - Removes code blocks
    - Removes Markdown formatting
    - Removes emote text (*action*)
    - Removes emojis

    Args:
        text (str): The raw text from LLM response.

    Returns:
        tuple: (cleaned_text, contains_links, contains_code_blocks)
    """
    # First extract link text from Markdown links before removing markdown
    text = extract_markdown_link_text(text)
    # Then remove remaining markdown formatting
    text = remove_markdown(text)
    # Remove standalone URLs (Markdown link URLs already handled above)
    text, contains_links = remove_links(text)
    # Remove code blocks
    text, contains_code_blocks = remove_code_blocks(text)
    # Remove emote text between asterisks
    text = remove_emote_text(text)
    # Remove emojis
    text = remove_emojis(text)
    # Clean up extra whitespace that may result from removals
    text = re.sub(r"\s+", " ", text).strip()

    return text, contains_links, contains_code_blocks
