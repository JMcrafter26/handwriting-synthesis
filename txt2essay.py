import sys
import textwrap
import re
import xml.etree.ElementTree as ET

from hand import Hand


def parse_markup(text, wrap_width):
    """Parse markup and return list of (text, metadata) tuples.
    
    Markup formats:
    - # Heading (centered)
    - ## Heading (uncentered)
    - \n\n for line breaks (empty lines)
    - List items: -, *, 1., 1), etc.
    """
    lines_with_meta = []
    
    # Split by paragraphs first (double newline)
    paragraphs = text.split('\n\n')
    
    for para_idx, para in enumerate(paragraphs):
        if not para.strip():
            continue
            
        # Check if it's a heading
        heading_match = re.match(r'^(#{1,2})\s+(.+)$', para.strip())
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            
            lines_with_meta.append({
                'text': heading_text,
                'type': 'heading',
                'centered': level == 1,  # # is centered, ## is not
                'bold': False
            })
        else:
            # Check if this paragraph is a list (split by single newlines)
            lines_in_para = para.split('\n')
            is_list = False
            
            # Check if first line is a list item
            if lines_in_para:
                first_line = lines_in_para[0].strip()
                # Match unordered (-, *, +) or ordered (1., 1), a., a), etc.)
                if re.match(r'^[-*+]\s+|^\d+[.)]\s+|^[a-z][.)]\s+', first_line):
                    is_list = True
            
            if is_list:
                # Process each list item separately (no wrapping within items)
                for line in lines_in_para:
                    line = line.strip()
                    if line:
                        lines_with_meta.append({
                            'text': line,
                            'type': 'list_item',
                            'centered': False,
                            'bold': False
                        })
            else:
                # Regular paragraph - wrap and remove bold markers
                # Note: Per-word styling isn't supported by the handwriting API
                wrapped = textwrap.wrap(para, width=wrap_width)
                for line in wrapped:
                    # Remove bold markers from text (can't apply per-word styling)
                    clean_line = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
                    clean_line = re.sub(r'__(.+?)__', r'\1', clean_line)
                    
                    lines_with_meta.append({
                        'text': clean_line,
                        'type': 'text',
                        'centered': False,
                        'bold': False
                    })
        
        # Add empty line between paragraphs (except after last one)
        if para_idx < len(paragraphs) - 1:
            lines_with_meta.append({
                'text': '',
                'type': 'empty',
                'centered': False,
                'bold': False
            })
    
    return lines_with_meta


def main():
    if len(sys.argv) != 2:
        print("Usage: python txt2essay.py input.txt")
        sys.exit(1)

    txt_file = sys.argv[1]
    base_output = txt_file.replace('.txt', '.svg')

    with open(txt_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # A4 dimensions at 96dpi (standard SVG resolution).
    A4_WIDTH_MM = 210
    A4_HEIGHT_MM = 297
    DPI = 96
    A4_WIDTH_PX = int(A4_WIDTH_MM * DPI / 25.4)  # 794
    A4_HEIGHT_PX = int(A4_HEIGHT_MM * DPI / 25.4)  # 1123

    # === CONFIGURABLE PARAMETERS FOR TESTING ===
    FONT_SCALE = 1.0          # Scale factor for handwriting size (adjust for testing)
    LINE_HEIGHT = 38          # Vertical spacing between baselines (adjust for testing)
    STROKE_WIDTH = 1.0        # Stroke width for handwriting (adjust for testing)
    TOP_MARGIN = 40           # Vertical offset to align text with ruled lines (adjust for testing)
    LEFT_MARGIN = 0          # Horizontal left margin in pixels
    RIGHT_MARGIN = 40         # Horizontal right margin in pixels
    TEXT_WRAP_WIDTH = 48      # Character wrap width (reduce if text overflows right edge)
    RULED_LINES_COUNT = 29    # Fixed number of ruled lines per page
    ADD_RULED_LINES = True    # Enable/disable ruled lines
    
    # Markup styling
    HEADING_BIAS = 0.7        # Lower bias for neater heading text
    TEXT_BIAS = 0.85          # Default bias for body text
    TEXT_STYLE = 7          # Default style index for body text (1-9)
    # ===========================================

    # Parse markup and get lines with metadata
    lines_with_meta = parse_markup(text, TEXT_WRAP_WIDTH)

    if not lines_with_meta:
        print("No text to process.")
        sys.exit(1)

    # replace ä, ö, ü, ß with simple equivalents for now
    for line_meta in lines_with_meta:
        line_meta['text'] = line_meta['text'].replace('ä', 'a').replace('ö', 'o').replace('ü', 'u').replace('ß', 'ss')
        line_meta['text'] = line_meta['text'].replace('Ä', 'A').replace('Ö', 'O').replace('Ü', 'U').replace('Z', 'z')
    
    # {'R', '(', 'f', 'Y', 'b', 't', 'D', '8', 'I', 'p', 'g', 'm', 'x', '5', '4', '7', '1', '0', 'k', 'z', ')', 'C', 'G', '?', 'j', 'V', '#', 'h', '3', 'u', 'N', 'y', '\x00', 'o', 'a', 'U', 'H', 'n', 'q', 'B', 'M', '-', '6', '"', 'F', 'P', 'd', "'", 'S', '.', ':', 'A', 'w', ';', '9', '!', 'E', 'K', 'e', 's', ' ', 'L', 'O', 'c', ',', 'T', 'i', 'J', 'l', 'r', 'v', 'W', '2'}
    validate_char_set = {'R', '(', 'f', 'Y', 'b', 't', 'D', '8', 'I', 'p', 'g', 'm', 'x', '5', '4', '7', '1', '0', 'k', 'z', ')', 'C', 'G', '?', 'j', 'V', '#', 'h', '3', 'u', 'N', 'y', '\x00', 'o', 'a', 'U', 'H', 'n', 'q', 'B', 'M', '-', '6', '"', 'F', 'P', 'd', "'", 'S', '.', ':', 'A', 'w', ';', '9', '!', 'E', 'K', 'e', 's', ' ', 'L', 'O', 'c', ',', 'T', 'i', 'J', 'l', 'r', 'v', 'W', '2'}
    for line_meta in lines_with_meta:
        for ch in line_meta['text']:
            if ch not in validate_char_set:
                print(f"Warning: Character '{ch}' in line '{line_meta['text']}' may not be supported by the handwriting model.")

    print('\n\n\n')
    
    # Calculate lines per page based on ruled lines count.
    top_margin_lines = 1  # Empty line for top margin
    lines_per_page = RULED_LINES_COUNT - top_margin_lines - 1

    # Pagination with metadata.
    def chunk_lines(all_lines_meta, lpp):
        chunks = []
        i = 0
        # Add top margin line
        margin_meta = {'text': '', 'type': 'empty', 'centered': False, 'bold': False}
        while i < len(all_lines_meta):
            chunk = [margin_meta] + all_lines_meta[i:i + lpp]
            chunks.append(chunk)
            i += lpp
        return chunks

    chunks = chunk_lines(lines_with_meta, lines_per_page)

    # Render each page and fix the viewbox to A4.
    def render_page(chunk_meta, idx, total):
        output_svg = base_output if total == 1 else base_output.replace('.svg', f'_page{idx+1}.svg')
        
        # Extract lines and build per-line parameters
        lines = []
        biases = []
        styles = []
        stroke_colors = []
        stroke_widths = []
        line_centers = []
        line_font_scales = []
        
        for idx, meta in enumerate(chunk_meta):
            lines.append(meta['text'])
            
            # Determine parameters based on metadata
            if meta['type'] == 'heading':
                biases.append(HEADING_BIAS)
            else:
                biases.append(TEXT_BIAS)
            
            stroke_widths.append(STROKE_WIDTH)
            line_font_scales.append(FONT_SCALE)
            styles.append(TEXT_STYLE)
            stroke_colors.append('black')
            line_centers.append(meta['centered'])

        hand = Hand()
        hand.write(
            filename=output_svg,
            lines=lines,
            biases=biases,
            styles=styles,
            stroke_colors=stroke_colors,
            stroke_widths=stroke_widths,
            line_height=LINE_HEIGHT,
            view_width=A4_WIDTH_PX,
            align_center=False,
            font_scale=FONT_SCALE,
            top_margin=TOP_MARGIN,
            left_margin=LEFT_MARGIN,
            per_line_font_scales=line_font_scales,
            per_line_centers=line_centers
        )

        # Post-process: fix viewbox to exact A4 dimensions, extend white background, and add ruled lines.
        tree = ET.parse(output_svg)
        root = tree.getroot()
        
        # Update root dimensions
        root.attrib['viewBox'] = f'0 0 {A4_WIDTH_PX} {A4_HEIGHT_PX}'
        root.attrib['width'] = f'{A4_WIDTH_MM}mm'
        root.attrib['height'] = f'{A4_HEIGHT_MM}mm'
        
        # Find and update the white background rectangle to cover full A4 page
        bg_elem = None
        for elem in root:
            if elem.tag.endswith('rect') and elem.attrib.get('fill') == 'white':
                elem.attrib['width'] = str(A4_WIDTH_PX)
                elem.attrib['height'] = str(A4_HEIGHT_PX)
                bg_elem = elem
                break
        
        # Add ruled lines at fixed positions if enabled
        if ADD_RULED_LINES and bg_elem is not None:
            # Insert lines right after the background
            insert_idx = list(root).index(bg_elem) + 1
            top_margin_calc = LINE_HEIGHT * 0.75  # Same offset as Hand._draw uses
            
            for i in range(RULED_LINES_COUNT):
                y_pos = top_margin_calc + (i * LINE_HEIGHT)
                line_elem = ET.Element('{http://www.w3.org/2000/svg}line')
                line_elem.attrib['x1'] = str(LEFT_MARGIN)
                line_elem.attrib['y1'] = str(y_pos)
                line_elem.attrib['x2'] = str(A4_WIDTH_PX - RIGHT_MARGIN)
                line_elem.attrib['y2'] = str(y_pos)
                line_elem.attrib['stroke'] = '#d0d0d0'
                line_elem.attrib['stroke-width'] = '0.5'
                root.insert(insert_idx, line_elem)
                insert_idx += 1
        
        tree.write(output_svg, encoding='utf-8', xml_declaration=True)

        return output_svg

    outputs = [render_page(chunk, idx, len(chunks)) for idx, chunk in enumerate(chunks)]

    if len(outputs) == 1:
        print(f"Generated {outputs[0]}")
    else:
        print("Generated pages:")
        for name in outputs:
            print(f" - {name}")


if __name__ == "__main__":
    main()
