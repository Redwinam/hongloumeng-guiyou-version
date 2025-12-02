import os
import re
import shutil
import zipfile
import uuid
from datetime import datetime

# Configuration
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(PROJECT_DIR, 'raw_data')
SRC_DIR = os.path.join(PROJECT_DIR, 'src')
BUILD_DIR = os.path.join(PROJECT_DIR, 'build')
DIST_DIR = os.path.join(PROJECT_DIR, 'dist')
EPUB_NAME = 'Guiyou_Hongloumeng.epub'

# Metadata
TITLE = '癸酉本《红楼梦》'
AUTHOR = '吴氏石头记'
LANGUAGE = 'zh-CN'
UUID = str(uuid.uuid4())
DATE = datetime.now().strftime('%Y-%m-%d')

def ensure_dirs():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)
    os.makedirs(os.path.join(BUILD_DIR, 'META-INF'))
    os.makedirs(os.path.join(BUILD_DIR, 'OEBPS'))
    if not os.path.exists(DIST_DIR):
        os.makedirs(DIST_DIR)

def create_mimetype():
    with open(os.path.join(BUILD_DIR, 'mimetype'), 'w') as f:
        f.write('application/epub+zip')

def create_container_xml():
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
    with open(os.path.join(BUILD_DIR, 'META-INF', 'container.xml'), 'w') as f:
        f.write(content)

def parse_full_text():
    full_path = os.path.join(RAW_DATA_DIR, 'full.txt')
    if not os.path.exists(full_path):
        print("Error: full.txt not found.")
        return [], []

    with open(full_path, 'r') as f:
        content = f.read()

    # Split into TOC and Body
    # We assume "扉页题诗：" marks the start of the content preamble
    split_marker = "扉页题诗："
    if split_marker in content:
        parts = content.split(split_marker, 1)
        toc_text = parts[0]
        body_text = split_marker + parts[1] # Keep the marker in the body
    else:
        # Fallback: try to find the first chapter
        print("Warning: '扉页题诗：' marker not found. Trying to split by first chapter.")
        match = re.search(r'(^|\n)第\s*一\s*回', content)
        if match:
            toc_text = content[:match.start()]
            body_text = content[match.start():]
        else:
            print("Error: Could not split TOC and Body.")
            return [], []

    # Parse TOC
    chapters = []
    # Regex for TOC lines: "第 X 回 Title PageNum"
    # Note: The spaces in "第  一  回" might vary.
    toc_pattern = re.compile(r'(第\s*[一二三四五六七八九十百]+\s*回)\s+(.*?)\s*(\d+)?$')
    
    for line in toc_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        match = toc_pattern.match(line)
        if match:
            chap_num_str = match.group(1).replace(' ', '') # Normalize "第  一  回" to "第一回"
            title = match.group(2).strip()
            chapters.append({
                'id': f'chap{len(chapters) + 1}',
                'num_str': chap_num_str,
                'title': title,
                'filename': f'chapter{len(chapters) + 1}.html'
            })
    
    # Parse Body
    # We need to split body_text into sections.
    # 1. Intro (from "扉页题诗：" to "第一回")
    # 2. Chapters
    
    # We'll use a regex to find all chapter headers in the body
    # The header in body usually looks like "第一回  甄士隐..."
    # It should match the start of a line.
    
    # Regex to find chapter starts. 
    # We use capturing group to keep the delimiter (the header itself)
    # Pattern: newline + "第" + spaces + chinese numbers + spaces + "回" + spaces + title
    # But title might be complex. Let's just match "第...回"
    
    # Note: body_text might start with "扉页题诗：..."
    
    # Let's find all occurrences of chapter headers
    chapter_starts = []
    # Pattern: Start of line, "第", optional spaces, number, optional spaces, "回"
    chap_header_pattern = re.compile(r'(^|\n)(第\s*[一二三四五六七八九十百]+\s*回\s+.*?)(\n|$)')
    
    # We will iterate through the text and split manually to be safe
    # Or better: use re.split but keep delimiters?
    # re.split with capturing group keeps the delimiter.
    
    # Let's try to find the positions of all chapter headers
    matches = list(chap_header_pattern.finditer(body_text))
    
    parsed_body = []
    
    # If there are matches, the text before the first match is the Intro
    if matches:
        intro_text = body_text[:matches[0].start()].strip()
        if intro_text:
            parsed_body.append({
                'type': 'intro',
                'title': '扉页',
                'content': intro_text,
                'filename': 'intro.html'
            })
            
        for i, match in enumerate(matches):
            start = match.start()
            # The content of this chapter goes until the start of the next match
            if i < len(matches) - 1:
                end = matches[i+1].start()
            else:
                end = len(body_text)
            
            # The match includes the newline before "第", so we need to be careful
            # match.group(2) is the actual header "第一回 ..."
            
            full_chunk = body_text[start:end]
            # Remove the leading newline if present in the chunk (it is part of the match group 1)
            full_chunk = full_chunk.strip()
            
            # Extract title from the first line
            lines = full_chunk.split('\n')
            header = lines[0].strip()
            content = '\n'.join(lines[1:]).strip()
            
            # Try to match the chapter info from TOC
            # We assume the order is the same
            # But let's be robust.
            
            # Normalize header to find number
            # "第一回  Title"
            header_match = re.match(r'(第\s*[一二三四五六七八九十百]+\s*回)\s+(.*)', header)
            if header_match:
                num_str = header_match.group(1).replace(' ', '')
                title = header_match.group(2).strip()
            else:
                num_str = header[:4] # Fallback
                title = header
            
            parsed_body.append({
                'type': 'chapter',
                'num_str': num_str,
                'title': title,
                'content': content,
                'original_header': header
            })
            
    else:
        # No chapters found? Treat whole body as one?
        print("Warning: No chapter headers found in body.")
        parsed_body.append({
            'type': 'intro',
            'title': '全文',
            'content': body_text,
            'filename': 'full.html'
        })

    return chapters, parsed_body

def process_text(text):
    # Escape HTML
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Wrap comments
    text = re.sub(r'(【.*?】)', r'<span class="comment">\1</span>', text)
    
    lines = text.split('\n')
    html_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('诗曰') or line.endswith('云：') or line.endswith('道是：') or line.endswith('曰：'):
             html_lines.append(f'<p class="poem-intro">{line}</p>')
        elif len(line) < 40 and (line.endswith('。') or line.endswith('，') or line.endswith('？') or line.endswith('！')):
             # Heuristic for poem lines or short verses
             # Check if it looks like a poem (often centered or distinct)
             # For now, just a class
             html_lines.append(f'<p class="poem-line" style="text-align:center;">{line}</p>')
        else:
             html_lines.append(f'<p>{line}</p>')
             
    return '\n'.join(html_lines)

def create_html_file(filename, title, content):
    html_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <h1>{title}</h1>
    {content}
</body>
</html>'''
    
    with open(os.path.join(BUILD_DIR, 'OEBPS', filename), 'w') as f:
        f.write(html_content)

def create_toc_html(toc_items):
    items_html = []
    for item in toc_items:
        items_html.append(f'<li><a href="{item["href"]}">{item["label"]}</a></li>')
             
    content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>目录</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <h1>目录</h1>
    <nav id="toc">
        <ol>
            {chr(10).join(items_html)}
        </ol>
    </nav>
</body>
</html>'''
    with open(os.path.join(BUILD_DIR, 'OEBPS', 'toc.html'), 'w') as f:
        f.write(content)

def create_cover_html():
    content = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Cover</title>
    <style type="text/css">
        body { margin: 0; padding: 0; text-align: center; }
        img { max-width: 100%; max-height: 100%; }
    </style>
</head>
<body>
    <div style="text-align: center; padding: 0pt; margin: 0pt;">
        <img src="images/cover.png" alt="Cover"/>
    </div>
</body>
</html>'''
    with open(os.path.join(BUILD_DIR, 'OEBPS', 'cover.html'), 'w') as f:
        f.write(content)

def create_content_opf(manifest_items, spine_items):
    # manifest_items and spine_items are lists of strings
    
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>{TITLE}</dc:title>
        <dc:creator opf:role="aut">{AUTHOR}</dc:creator>
        <dc:language>{LANGUAGE}</dc:language>
        <dc:identifier id="BookId" opf:scheme="UUID">{UUID}</dc:identifier>
        <dc:date>{DATE}</dc:date>
        <meta name="cover" content="cover-image"/>
    </metadata>
    <manifest>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
        <item id="style" href="style.css" media-type="text/css"/>
        <item id="cover" href="cover.html" media-type="application/xhtml+xml"/>
        <item id="cover-image" href="images/cover.png" media-type="image/png"/>
        <item id="toc" href="toc.html" media-type="application/xhtml+xml"/>
        {chr(10).join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        <itemref idref="cover" linear="yes"/>
        <itemref idref="toc"/>
        {chr(10).join(spine_items)}
    </spine>
</package>'''
    
    with open(os.path.join(BUILD_DIR, 'OEBPS', 'content.opf'), 'w') as f:
        f.write(content)

def create_toc_ncx(nav_points):
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="{UUID}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{TITLE}</text></docTitle>
    <navMap>
        <navPoint id="navPoint-cover" playOrder="0">
            <navLabel><text>封面</text></navLabel>
            <content src="cover.html"/>
        </navPoint>
        <navPoint id="navPoint-toc" playOrder="1">
            <navLabel><text>目录</text></navLabel>
            <content src="toc.html"/>
        </navPoint>
        {chr(10).join(nav_points)}
    </navMap>
</ncx>'''
    
    with open(os.path.join(BUILD_DIR, 'OEBPS', 'toc.ncx'), 'w') as f:
        f.write(content)

def zip_epub():
    epub_path = os.path.join(DIST_DIR, EPUB_NAME)
    if os.path.exists(epub_path):
        os.remove(epub_path)
        
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(BUILD_DIR, 'mimetype'), 'mimetype', compress_type=zipfile.ZIP_STORED)
        for root, dirs, files in os.walk(BUILD_DIR):
            for file in files:
                if file == 'mimetype':
                    continue
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, BUILD_DIR)
                zf.write(abs_path, rel_path)
    
    print(f"EPUB generated at: {epub_path}")

def main():
    ensure_dirs()
    # Create images dir
    os.makedirs(os.path.join(BUILD_DIR, 'OEBPS', 'images'), exist_ok=True)
    
    create_mimetype()
    create_container_xml()
    shutil.copy(os.path.join(SRC_DIR, 'style.css'), os.path.join(BUILD_DIR, 'OEBPS', 'style.css'))
    
    # Copy cover image
    cover_src = os.path.join(SRC_DIR, 'cover.png')
    if os.path.exists(cover_src):
        shutil.copy(cover_src, os.path.join(BUILD_DIR, 'OEBPS', 'images', 'cover.png'))
        create_cover_html()
    else:
        print("Warning: Cover image not found at src/cover.png")
    
    toc_list, parsed_body = parse_full_text()
    
    manifest_items = []
    spine_items = []
    nav_points = []
    toc_html_items = []
    
    # Process parsed body items
    # We need to link them to the TOC list if possible, or just generate them
    
    # If we have an intro, add it first
    play_order = 2 # Start after cover (0) and TOC (1)
    chapter_index = 0
    
    for item in parsed_body:
        if item['type'] == 'intro':
            html_content = process_text(item['content'])
            create_html_file(item['filename'], item['title'], html_content)
            
            manifest_items.append(f'<item id="intro" href="{item["filename"]}" media-type="application/xhtml+xml"/>')
            spine_items.append('<itemref idref="intro"/>')
            
            nav_points.append(f'''<navPoint id="navPoint-{play_order}" playOrder="{play_order}">
                <navLabel><text>{item["title"]}</text></navLabel>
                <content src="{item["filename"]}"/>
            </navPoint>''')
            toc_html_items.append({'href': item['filename'], 'label': item['title']})
            play_order += 1
            
        elif item['type'] == 'chapter':
            chapter_index += 1
            filename = f"chapter_{chapter_index}.html"
            html_content = process_text(item['content'])
            
            # Full title
            full_title = f"{item['num_str']} {item['title']}"
            
            create_html_file(filename, full_title, html_content)
            
            chap_id = f"chap_{chapter_index}"
            manifest_items.append(f'<item id="{chap_id}" href="{filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{chap_id}"/>')
            
            nav_points.append(f'''<navPoint id="navPoint-{play_order}" playOrder="{play_order}">
                <navLabel><text>{full_title}</text></navLabel>
                <content src="{filename}"/>
            </navPoint>''')
            toc_html_items.append({'href': filename, 'label': full_title})
            play_order += 1

    create_toc_html(toc_html_items)
    create_content_opf(manifest_items, spine_items)
    create_toc_ncx(nav_points)
    
    zip_epub()

if __name__ == '__main__':
    main()
