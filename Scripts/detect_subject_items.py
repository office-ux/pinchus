import json
import math
import os
import re
from collections import defaultdict

import fitz


class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"
    RED = "\033[31m"


def color_text(text, color):
    return f"{color}{text}{Ansi.RESET}"


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r") as f:
        return json.load(f)


def select_pdf(folder_path):
    pdfs = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f"No PDF files found in {folder_path}")
        return None

    print(f"\nPDF files found in {folder_path}:")
    for i, pdf in enumerate(pdfs, 1):
        print(f"{i}. {pdf}")

    while True:
        choice = input(f"\nEnter the number of the file to scan (1-{len(pdfs)}): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(pdfs):
                return os.path.join(folder_path, pdfs[idx])
        print("Invalid selection. Please try again.")


def norm_text(value):
    return (value or "").strip().casefold()


def format_color(color):
    if not color:
        return "None"
    return "(" + ", ".join(f"{c:.3g}" for c in color) + ")"


def format_styles(styles):
    parts = []
    for line_weight, stroke_color, line_count, lengths, segments in styles:
        parts.append(
            f"{color_text(f'{line_weight:.2f} pt', Ansi.YELLOW)} / "
            f"{color_text(format_color(stroke_color), Ansi.MAGENTA)} / "
            f"{color_text(f'{line_count} lines', Ansi.GREEN)} / "
            f"lengths: {color_text(format_lengths(lengths), Ansi.CYAN)}"
        )
    return "; ".join(parts) if parts else "None"


def format_lengths(lengths):
    if not lengths:
        return "None"
    return ", ".join(f"{length:.2f}pt" for length in lengths)


def format_point(point):
    return f"({point[0]:.2f}, {point[1]:.2f})"


def format_segments(segments):
    if not segments:
        return "None"

    parts = []
    for i, segment in enumerate(segments, 1):
        length = f"{segment['length']:.2f}pt"
        line_weight = f"{segment['line_weight']:.2f}pt"
        parts.append(
            f"{color_text(f'L{i}', Ansi.BLUE)}: "
            f"{color_text(format_point(segment['start']), Ansi.CYAN)} -> "
            f"{color_text(format_point(segment['end']), Ansi.CYAN)}"
        )
    return "; ".join(parts)


def get_line_weight(annot):
    border = annot.border or {}
    width = border.get("width")
    if width is None:
        return 0.0
    return float(width)


def get_line_count(annot):
    annot_type = annot.type[1]
    vertices = getattr(annot, "vertices", None) or []

    if annot_type == "Ink":
        return sum(max(1, len(stroke) - 1) for stroke in vertices)

    if annot_type == "Line":
        return 1

    if annot_type == "PolyLine":
        return max(0, len(vertices) - 1)

    if annot_type == "Polygon":
        return len(vertices)

    if annot_type == "Square":
        return 4

    return 0


def get_stamp_appearance_xrefs(doc, annot_xref):
    obj = doc.xref_object(annot_xref, compressed=False)
    normal_ap = re.search(r"/AP\s*<<.*?/N\s+(\d+)\s+0\s+R", obj, re.S)
    return [int(normal_ap.group(1))] if normal_ap else []


def get_form_xobject_xrefs(doc, xref):
    xrefs = []
    obj = doc.xref_object(xref, compressed=False)
    resources = re.search(r"/XObject\s*<<(.*?)>>", obj, re.S)
    if not resources:
        return xrefs

    for child in re.finditer(r"/[A-Za-z0-9_.#-]+\s+(\d+)\s+0\s+R", resources.group(1)):
        child_xref = int(child.group(1))
        if child_xref not in xrefs:
            xrefs.append(child_xref)
    return xrefs


def parse_appearance_stream(stream):
    if not stream:
        return []

    text = stream.decode("latin1", errors="ignore")
    tokens = re.findall(r"/[^\s<>\[\]()]+|[-+]?(?:\d+\.\d+|\.\d+|\d+)|[A-Za-z*]+", text)
    stack = []
    line_weight = 1.0
    stroke_color = None
    path_lines = 0
    path_lengths = []
    path_segments = []
    path_open = False
    current_point = None
    start_point = None
    ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    style_counts = defaultdict(lambda: {"count": 0, "lengths": [], "segments": []})

    def pop_number(default=0.0):
        if not stack:
            return default
        try:
            return float(stack.pop())
        except ValueError:
            return default

    def save_stroke():
        nonlocal path_lines, path_lengths, path_segments, path_open, current_point, start_point
        if path_lines:
            key = (line_weight, tuple(stroke_color or ()))
            style_counts[key]["count"] += path_lines
            style_counts[key]["lengths"].extend(path_lengths)
            style_counts[key]["segments"].extend(path_segments)
        path_lines = 0
        path_lengths = []
        path_segments = []
        path_open = False
        current_point = None
        start_point = None

    def concat_matrix(current, new):
        a1, b1, c1, d1, e1, f1 = current
        a2, b2, c2, d2, e2, f2 = new
        return (
            a1 * a2 + c1 * b2,
            b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2,
            b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1,
            b1 * e2 + d1 * f2 + f1,
        )

    def transform_point(x, y):
        a, b, c, d, e, f = ctm
        return (a * x + c * y + e, b * x + d * y + f)

    def effective_line_weight():
        a, b, c, d, _, _ = ctm
        x_scale = math.hypot(a, b)
        y_scale = math.hypot(c, d)
        scale = (x_scale + y_scale) / 2
        if scale == 0:
            scale = 1.0
        return line_weight * scale

    for token in tokens:
        if token in {"q", "Q", "w", "G", "RG", "cm", "m", "l", "h", "re", "S", "s", "B", "B*", "b", "b*", "n"}:
            if token in {"q", "Q"}:
                stack.clear()
            elif token == "w":
                line_weight = pop_number(line_weight)
            elif token == "G":
                gray = pop_number(0.0)
                stroke_color = (gray, gray, gray)
            elif token == "RG":
                b = pop_number(0.0)
                g = pop_number(0.0)
                r = pop_number(0.0)
                stroke_color = (r, g, b)
            elif token == "cm":
                f = pop_number()
                e = pop_number()
                d = pop_number()
                c = pop_number()
                b = pop_number()
                a = pop_number()
                ctm = concat_matrix(ctm, (a, b, c, d, e, f))
                stack.clear()
            elif token == "m":
                y = pop_number()
                x = pop_number()
                stack.clear()
                path_open = True
                current_point = transform_point(x, y)
                start_point = current_point
            elif token == "l":
                y = pop_number()
                x = pop_number()
                stack.clear()
                next_point = transform_point(x, y)
                if current_point is not None:
                    length = math.hypot(next_point[0] - current_point[0], next_point[1] - current_point[1])
                    path_lengths.append(length)
                    path_segments.append({
                        "start": current_point,
                        "end": next_point,
                        "length": length,
                        "line_weight": line_weight,
                        "effective_line_weight": effective_line_weight(),
                        "stroke_color": stroke_color,
                    })
                path_lines += 1
                current_point = next_point
            elif token == "h":
                stack.clear()
                if path_open and current_point is not None and start_point is not None:
                    length = math.hypot(start_point[0] - current_point[0], start_point[1] - current_point[1])
                    path_lengths.append(length)
                    path_segments.append({
                        "start": current_point,
                        "end": start_point,
                        "length": length,
                        "line_weight": line_weight,
                        "effective_line_weight": effective_line_weight(),
                        "stroke_color": stroke_color,
                    })
                    path_lines += 1
                    current_point = start_point
            elif token == "re":
                height = pop_number()
                width = pop_number()
                y = pop_number()
                x = pop_number()
                stack.clear()
                p0 = transform_point(x, y)
                p1 = transform_point(x + width, y)
                p2 = transform_point(x + width, y + height)
                p3 = transform_point(x, y + height)
                rect_points = [(p0, p1), (p1, p2), (p2, p3), (p3, p0)]
                path_lines += 4
                for start, end in rect_points:
                    length = math.hypot(end[0] - start[0], end[1] - start[1])
                    path_lengths.append(length)
                    path_segments.append({
                        "start": start,
                        "end": end,
                        "length": length,
                        "line_weight": line_weight,
                        "effective_line_weight": effective_line_weight(),
                        "stroke_color": stroke_color,
                    })
                path_open = True
                current_point = p0
                start_point = p0
            elif token in {"S", "s", "B", "B*", "b", "b*"}:
                save_stroke()
                stack.clear()
            elif token == "n":
                path_lines = 0
                path_lengths = []
                path_segments = []
                path_open = False
                current_point = None
                start_point = None
                stack.clear()
        else:
            stack.append(token)

    return [
        (weight, color, data["count"], data["lengths"], data["segments"])
        for (weight, color), data in sorted(style_counts.items())
    ]


def get_stamp_styles(doc, annot):
    styles = []
    seen = set()
    pending = get_stamp_appearance_xrefs(doc, annot.xref)

    while pending:
        xref = pending.pop(0)
        if xref in seen:
            continue
        seen.add(xref)

        stream = doc.xref_stream(xref)
        styles.extend(parse_appearance_stream(stream))

        for child_xref in get_form_xobject_xrefs(doc, xref):
            if child_xref not in seen:
                pending.append(child_xref)

    combined = defaultdict(lambda: {"count": 0, "lengths": [], "segments": []})
    for line_weight, stroke_color, line_count, lengths, segments in styles:
        key = (line_weight, tuple(stroke_color or ()))
        combined[key]["count"] += line_count
        combined[key]["lengths"].extend(lengths)
        combined[key]["segments"].extend(segments)

    return [
        (line_weight, stroke_color, data["count"], data["lengths"], data["segments"])
        for (line_weight, stroke_color), data in sorted(combined.items())
    ]


def scan_pdf(pdf_path, targets):
    target_lookup = {norm_text(t): t for t in targets}
    summary = defaultdict(lambda: defaultdict(lambda: {"items": 0, "lines": 0}))
    matches = []

    doc = fitz.open(pdf_path)
    for page_index, page in enumerate(doc, 1):
        for annot in page.annots() or []:
            subject = annot.info.get("subject") or ""
            target_name = target_lookup.get(norm_text(subject))
            if not target_name:
                continue

            annot_type = annot.type[1]
            if annot_type == "Stamp":
                styles = get_stamp_styles(doc, annot)
                line_weight = styles[0][0] if styles else get_line_weight(annot)
                stroke_color = styles[0][1] if styles else annot.colors.get("stroke")
                line_count = sum(style[2] for style in styles)
                lengths = [length for style in styles for length in style[3]]
                segments = [segment for style in styles for segment in style[4]]
            else:
                styles = []
                line_weight = get_line_weight(annot)
                stroke_color = annot.colors.get("stroke")
                line_count = get_line_count(annot)
                lengths = []
                segments = []

            matches.append({
                "target": target_name,
                "page": page_index,
                "type": annot_type,
                "line_weight": line_weight,
                "stroke_color": stroke_color,
                "line_count": line_count,
                "lengths": lengths,
                "segments": segments,
                "styles": styles,
                "rect": annot.rect,
            })

            if styles:
                for style_weight, style_color, style_line_count, style_lengths, style_segments in styles:
                    key = (style_weight, tuple(style_color or ()), annot_type)
                    summary[target_name][key]["items"] += 1
                    summary[target_name][key]["lines"] += style_line_count
                    summary[target_name][key].setdefault("lengths", []).extend(style_lengths)
                    summary[target_name][key].setdefault("segments", []).extend(style_segments)
            else:
                key = (line_weight, tuple(stroke_color or ()), annot_type)
                summary[target_name][key]["items"] += 1
                summary[target_name][key]["lines"] += line_count
                summary[target_name][key].setdefault("lengths", []).extend(lengths)
                summary[target_name][key].setdefault("segments", []).extend(segments)

    return matches, summary


def main():
    cfg = load_config()
    folder_path = cfg["paths"]["input_folder"]
    targets = cfg.get("targets", [])

    if not targets:
        print("No targets found in Scripts/config.json.")
        return

    pdf_path = select_pdf(folder_path)
    if not pdf_path:
        return

    print(color_text("\nSubjects from config:", Ansi.BOLD))
    for target in targets:
        print(f"  - {color_text(target, Ansi.CYAN)}")

    matches, summary = scan_pdf(pdf_path, targets)

    if not matches:
        print("\nNo matching subject annotations found.")
        return

    print(color_text("\nMatched items:", Ansi.BOLD))
    for item in matches:
        page_label = f"Page {item['page']:>2}"
        line_weight_label = f"{item['line_weight']:.2f} pt"
        print(
            f"  {color_text(page_label, Ansi.BLUE)} | "
            f"Subject: {color_text(item['target'], Ansi.CYAN)} | "
            f"Type: {color_text(item['type'], Ansi.GREEN)} | "
            f"Line weight: {color_text(line_weight_label, Ansi.YELLOW)} | "
            f"Color: {color_text(format_color(item['stroke_color']), Ansi.MAGENTA)} | "
            f"Lines: {color_text(str(item['line_count']), Ansi.GREEN)}"
        )
        if item["lengths"]:
            print(f"           {color_text('Stamp line lengths:', Ansi.BOLD)} {color_text(format_lengths(item['lengths']), Ansi.CYAN)}")
        if item["segments"]:
            print(f"           {color_text('Stamp line coordinates:', Ansi.BOLD)} {format_segments(item['segments'])}")
        if item["styles"]:
            print(f"           {color_text('Stamp internal styles:', Ansi.BOLD)} {format_styles(item['styles'])}")

    print(color_text("\nSummary by subject:", Ansi.BOLD))
    for target in targets:
        print(f"\n{color_text(target + ':', Ansi.CYAN)}")
        if target not in summary:
            print(color_text("  No matches", Ansi.RED))
            continue

        total_items = 0
        total_lines = 0
        for (line_weight, stroke_color, annot_type), counts in sorted(summary[target].items()):
            total_items += counts["items"]
            total_lines += counts["lines"]
            line_weight_label = f"{line_weight:.2f} pt"
            print(
                f"  Type: {color_text(annot_type, Ansi.GREEN)} | "
                f"Line weight: {color_text(line_weight_label, Ansi.YELLOW)} | "
                f"Color: {color_text(format_color(stroke_color), Ansi.MAGENTA)} | "
                f"Items: {color_text(str(counts['items']), Ansi.BLUE)} | "
                f"Line count: {color_text(str(counts['lines']), Ansi.GREEN)}"
            )
            if counts.get("lengths"):
                print(f"    {color_text('Line lengths:', Ansi.BOLD)} {color_text(format_lengths(counts['lengths']), Ansi.CYAN)}")
            if counts.get("segments"):
                print(f"    {color_text('Line coordinates:', Ansi.BOLD)} {format_segments(counts['segments'])}")
        print(f"  Total items: {color_text(str(total_items), Ansi.BLUE)}")
        print(f"  Total lines: {color_text(str(total_lines), Ansi.GREEN)}")

    import detect_matching_lines

    detect_matching_lines.report_matching_lines(pdf_path, matches, cfg)


if __name__ == "__main__":
    main()
