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

def parse_toc():
    chapters = []
    toc_path = os.path.join(RAW_DATA_DIR, 'toc.txt')
    if not os.path.exists(toc_path):
        print("Warning: TOC file not found.")
        return chapters
    
    with open(toc_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Match "第 X 回 Title PageNum"
            # Example: 第  一  回  甄士隐梦幻识通灵　贾雨村风尘怀闺秀	1
            match = re.match(r'(第\s*[一二三四五六七八九十百]+\s*回)\s+(.*?)(\d+)?$', line)
            if match:
                chap_num_str = match.group(1).replace(' ', '')
                title = match.group(2).strip()
                chapters.append({
                    'id': f'chap{len(chapters) + 1}',
                    'num_str': chap_num_str,
                    'title': title,
                    'filename': f'chapter{len(chapters) + 1}.html'
                })
    return chapters

def process_text(text):
    # Escape HTML
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Wrap comments
    text = re.sub(r'(【.*?】)', r'<span class="comment">\1</span>', text)
    
    # Simple poem detection (lines starting with spaces or short lines after "诗曰")
    # This is a heuristic. For now, we just wrap paragraphs.
    
    lines = text.split('\n')
    html_lines = []
    
    in_poem = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('诗曰') or line.endswith('云：') or line.endswith('道是：'):
             html_lines.append(f'<p>{line}</p>')
             # Could start a poem block here if we want strict structure, 
             # but for now simple paragraphs are safer.
        elif len(line) < 20 and (line.endswith('。') or line.endswith('，')):
             # Possible poem line
             html_lines.append(f'<p class="poem-line" style="text-align:center;">{line}</p>')
        else:
             html_lines.append(f'<p>{line}</p>')
             
    return '\n'.join(html_lines)

def create_chapter_html(chapter_info, content):
    html_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{chapter_info['title']}</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <h1>{chapter_info['num_str']} {chapter_info['title']}</h1>
    {content}
</body>
</html>'''
    
    with open(os.path.join(BUILD_DIR, 'OEBPS', chapter_info['filename']), 'w') as f:
        f.write(html_content)

def create_toc_html(chapters):
    items = []
    for chap in chapters:
        # Only link if file exists (we might only have text for first few chapters)
        if os.path.exists(os.path.join(BUILD_DIR, 'OEBPS', chap['filename'])):
             items.append(f'<li><a href="{chap["filename"]}">{chap["num_str"]} {chap["title"]}</a></li>')
        else:
             items.append(f'<li>{chap["num_str"]} {chap["title"]} (待补)</li>')
             
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
            {chr(10).join(items)}
        </ol>
    </nav>
</body>
</html>'''
    with open(os.path.join(BUILD_DIR, 'OEBPS', 'toc.html'), 'w') as f:
        f.write(content)

def create_content_opf(chapters):
    manifest_items = []
    spine_items = []
    
    # Add style
    manifest_items.append('<item id="style" href="style.css" media-type="text/css"/>')
    # Add TOC html
    manifest_items.append('<item id="toc" href="toc.html" media-type="application/xhtml+xml"/>')
    spine_items.append('<itemref idref="toc"/>')
    
    # Add chapters
    for chap in chapters:
        if os.path.exists(os.path.join(BUILD_DIR, 'OEBPS', chap['filename'])):
            manifest_items.append(f'<item id="{chap["id"]}" href="{chap["filename"]}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{chap["id"]}"/>')
    
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>{TITLE}</dc:title>
        <dc:creator opf:role="aut">{AUTHOR}</dc:creator>
        <dc:language>{LANGUAGE}</dc:language>
        <dc:identifier id="BookId" opf:scheme="UUID">{UUID}</dc:identifier>
        <dc:date>{DATE}</dc:date>
    </metadata>
    <manifest>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
        {chr(10).join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {chr(10).join(spine_items)}
    </spine>
</package>'''
    
    with open(os.path.join(BUILD_DIR, 'OEBPS', 'content.opf'), 'w') as f:
        f.write(content)

def create_toc_ncx(chapters):
    nav_points = []
    play_order = 1
    
    # TOC
    nav_points.append(f'''<navPoint id="navPoint-{play_order}" playOrder="{play_order}">
        <navLabel><text>目录</text></navLabel>
        <content src="toc.html"/>
    </navPoint>''')
    play_order += 1
    
    for chap in chapters:
        if os.path.exists(os.path.join(BUILD_DIR, 'OEBPS', chap['filename'])):
            nav_points.append(f'''<navPoint id="navPoint-{play_order}" playOrder="{play_order}">
                <navLabel><text>{chap["num_str"]} {chap["title"]}</text></navLabel>
                <content src="{chap["filename"]}"/>
            </navPoint>''')
            play_order += 1
            
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
        # Mimetype must be first and uncompressed
        zf.write(os.path.join(BUILD_DIR, 'mimetype'), 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add other files
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
    create_mimetype()
    create_container_xml()
    
    # Copy style
    shutil.copy(os.path.join(SRC_DIR, 'style.css'), os.path.join(BUILD_DIR, 'OEBPS', 'style.css'))
    
    # Parse TOC
    chapters = parse_toc()
    
    # Process Chapters (Hardcoded for 1 and 2 for now, or loop through available files)
    # We have chapter1.txt and chapter2.txt
    for i in [1, 2]:
        txt_path = os.path.join(RAW_DATA_DIR, f'chapter{i}.txt')
        if os.path.exists(txt_path):
            with open(txt_path, 'r') as f:
                content = f.read()
            
            # The raw text includes title at top, we might want to strip it if we add it in HTML
            # But our process_text just converts lines to <p>, so it's fine.
            # Ideally we remove the first few lines if they match the title.
            
            html_content = process_text(content)
            
            # Find the chapter info from TOC
            # Assuming order matches.
            if i <= len(chapters):
                chap_info = chapters[i-1]
                create_chapter_html(chap_info, html_content)
    
    create_toc_html(chapters)
    create_content_opf(chapters)
    create_toc_ncx(chapters)
    
    zip_epub()

if __name__ == '__main__':
    main()
