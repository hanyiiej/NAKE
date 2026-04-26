import mistune
import re

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def render_markdown(content: str) -> str:
    md = mistune.create_markdown(plugins=[
        'mistune.plugins.table.table',
        'mistune.plugins.formatting.strikethrough',
        'mistune.plugins.formatting.mark',
        'mistune.plugins.footnotes.footnotes',
    ])
    return md(content)
