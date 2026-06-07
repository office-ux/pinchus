import math
import os

import fitz

import detect_subject_items as subject_items


DEFAULT_LENGTH_TOLERANCE = 0.25
DEFAULT_LINE_WEIGHT_TOLERANCE = 0.25
DEFAULT_COLOR_TOLERANCE = 0.02
DEFAULT_POSITION_TOLERANCE = 2.0
DEFAULT_MATCH_THRESHOLD = 0.85
DEFAULT_DEDUPE_DISTANCE = 10.0
DEFAULT_OUTPUT_LINE_WIDTH = 4.0

TARGET_COLORS = [
    (1.0, 0.0, 0.0),
    (0.0, 0.55, 1.0),
    (0.0, 0.75, 0.25),
    (1.0, 0.55, 0.0),
    (0.65, 0.0, 1.0),
    (1.0, 0.0, 0.75),
    (0.0, 0.75, 0.75),
]


def dist(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def get_scan_config(cfg):
    scan_cfg = cfg.get("line_scan", {})
    pattern_cfg = cfg.get("pattern_detection", {})
    return {
        "length_tolerance": scan_cfg.get(
            "length_tolerance",
            pattern_cfg.get("length_tolerance", DEFAULT_LENGTH_TOLERANCE),
        ),
        "line_weight_tolerance": scan_cfg.get(
            "line_weight_tolerance",
            pattern_cfg.get("line_weight_tolerance", DEFAULT_LINE_WEIGHT_TOLERANCE),
        ),
        "color_tolerance": scan_cfg.get(
            "color_tolerance",
            pattern_cfg.get("color_tolerance", DEFAULT_COLOR_TOLERANCE),
        ),
        "position_tolerance": pattern_cfg.get("position_tolerance", DEFAULT_POSITION_TOLERANCE),
        "match_threshold": pattern_cfg.get("match_threshold", DEFAULT_MATCH_THRESHOLD),
        "dedupe_distance": pattern_cfg.get("dedupe_distance", DEFAULT_DEDUPE_DISTANCE),
        "output_line_width": scan_cfg.get("output_line_width", DEFAULT_OUTPUT_LINE_WIDTH),
    }


def normalize_color(color):
    if not color:
        return (0.0, 0.0, 0.0)
    c_tuple = tuple(float(c) for c in color)
    if all(x <= 0.001 for x in c_tuple):
        return (0.0, 0.0, 0.0)
    return c_tuple


def colors_match(a, b, tolerance):
    a = normalize_color(a)
    b = normalize_color(b)
    if a is None or b is None:
        return a == b
    if len(a) != len(b):
        return False
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


def line_matches_signature(line, signature, cfg):
    if abs(line["line_weight"] - signature["match_line_weight"]) > cfg["line_weight_tolerance"]:
        return False
    if not colors_match(line["stroke_color"], signature["stroke_color"], cfg["color_tolerance"]):
        return False
    return any(
        abs(line["length"] - length) <= cfg["length_tolerance"]
        for length in signature["lengths"]
    )


def make_signatures(subject_matches):
    signatures = []
    for item in subject_matches:
        for style_weight, style_color, _, style_lengths, style_segments in item.get("styles", []):
            if not style_lengths:
                continue
            effective_weights = [
                segment.get("effective_line_weight", segment["line_weight"])
                for segment in style_segments
            ]
            if effective_weights:
                match_weight = sum(effective_weights) / len(effective_weights)
            else:
                match_weight = style_weight
            signatures.append({
                "target": item["target"],
                "line_weight": style_weight,
                "match_line_weight": match_weight,
                "stroke_color": style_color,
                "lengths": style_lengths,
            })
    return signatures


def iter_page_lines(page):
    for drawing_index, drawing in enumerate(page.get_drawings()):
        line_weight = drawing.get("width")
        if line_weight is None:
            line_weight = 1.0

        stroke_color = drawing.get("color")
        if stroke_color is None:
            stroke_color = (0, 0, 0)

        for item_index, item in enumerate(drawing["items"]):
            if item[0] == "l":
                start = item[1]
                end = item[2]
                yield {
                    "source": f"drawing {drawing_index}, item {item_index}",
                    "start": (start[0], start[1]),
                    "end": (end[0], end[1]),
                    "length": dist(start, end),
                    "line_weight": float(line_weight),
                    "stroke_color": stroke_color,
                }
            elif item[0] == "re":
                rect = item[1]
                points = [
                    ((rect.x0, rect.y0), (rect.x1, rect.y0)),
                    ((rect.x1, rect.y0), (rect.x1, rect.y1)),
                    ((rect.x1, rect.y1), (rect.x0, rect.y1)),
                    ((rect.x0, rect.y1), (rect.x0, rect.y0)),
                ]
                for rect_index, (start, end) in enumerate(points, 1):
                    yield {
                        "source": f"drawing {drawing_index}, item {item_index}, rect side {rect_index}",
                        "start": start,
                        "end": end,
                        "length": dist(start, end),
                        "line_weight": float(line_weight),
                        "stroke_color": stroke_color,
                    }


def format_line(line, matched_targets):
    targets = ", ".join(sorted(set(matched_targets)))
    length = f"{line['length']:.2f}pt"
    line_weight = f"{line['line_weight']:.2f}pt"
    return (
        f"    {subject_items.color_text(targets, subject_items.Ansi.CYAN)} | "
        f"{subject_items.color_text(line['source'], subject_items.Ansi.BOLD)} | "
        f"{subject_items.color_text(subject_items.format_point(line['start']), subject_items.Ansi.BLUE)} -> "
        f"{subject_items.color_text(subject_items.format_point(line['end']), subject_items.Ansi.BLUE)} | "
        f"length {subject_items.color_text(length, subject_items.Ansi.GREEN)} | "
        f"weight {subject_items.color_text(line_weight, subject_items.Ansi.YELLOW)} | "
        f"color {subject_items.color_text(subject_items.format_color(line['stroke_color']), subject_items.Ansi.MAGENTA)}"
    )


def find_matching_lines(pdf_path, subject_matches, cfg):
    scan_cfg = get_scan_config(cfg)
    signatures = make_signatures(subject_matches)
    page_matches = []

    if not signatures:
        return page_matches

    doc = fitz.open(pdf_path)
    for page_index, page in enumerate(doc, 1):
        lines = []
        for line in iter_page_lines(page):
            matched_targets = [
                signature["target"]
                for signature in signatures
                if line_matches_signature(line, signature, scan_cfg)
            ]
            if matched_targets:
                line["matched_targets"] = matched_targets
                lines.append(line)
        page_matches.append({"page": page_index, "lines": lines})

    return page_matches


def get_unique_output_path(output_folder, input_pdf_path):
    base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
    output_path = os.path.join(output_folder, f"{base_name}_matching_lines_layered.pdf")
    if not os.path.exists(output_path):
        return output_path

    counter = 2
    while True:
        output_path = os.path.join(output_folder, f"{base_name}_matching_lines_layered_{counter}.pdf")
        if not os.path.exists(output_path):
            return output_path
        counter += 1


def get_target_color_map(targets):
    return {
        target: TARGET_COLORS[index % len(TARGET_COLORS)]
        for index, target in enumerate(sorted(set(targets)))
    }


def save_layered_matching_pdf(pdf_path, page_matches, cfg):
    output_folder = cfg["paths"]["output_folder"]
    os.makedirs(output_folder, exist_ok=True)

    matched_targets = []
    for page_match in page_matches:
        for line in page_match["lines"]:
            matched_targets.extend(line["matched_targets"])

    matched_targets = sorted(set(matched_targets))
    if not matched_targets:
        print(subject_items.color_text("\nNo matching lines to draw in output PDF.", subject_items.Ansi.RED))
        return None

    output_path = get_unique_output_path(output_folder, pdf_path)
    color_map = get_target_color_map(matched_targets)
    scan_cfg = get_scan_config(cfg)

    doc = fitz.open(pdf_path)
    layers = {
        target: doc.add_ocg(f"Matched {target}", on=True)
        for target in matched_targets
    }

    for page_match in page_matches:
        page = doc[page_match["page"] - 1]
        for line in page_match["lines"]:
            for target in sorted(set(line["matched_targets"])):
                page.draw_line(
                    line["start"],
                    line["end"],
                    color=color_map[target],
                    width=scan_cfg["output_line_width"],
                    overlay=True,
                    stroke_opacity=0.85,
                    oc=layers[target],
                )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    print(
        f"\nSaved layered matching-lines PDF to: "
        f"{subject_items.color_text(output_path, subject_items.Ansi.GREEN)}"
    )
    print("Layers created:")
    for target in matched_targets:
        print(
            f"  - {subject_items.color_text('Matched ' + target, subject_items.Ansi.CYAN)} "
            f"color {subject_items.color_text(subject_items.format_color(color_map[target]), subject_items.Ansi.MAGENTA)}"
        )

    try:
        os.startfile(output_path)
    except OSError as exc:
        print(f"Could not open output PDF automatically: {exc}")

    return output_path


def report_matching_lines(pdf_path, subject_matches, cfg):
    scan_cfg = get_scan_config(cfg)
    signatures = make_signatures(subject_matches)

    print(subject_items.color_text("\nMatching page vector lines from stamp properties:", subject_items.Ansi.BOLD))
    print(
        f"  Length tolerance: {scan_cfg['length_tolerance']} pt | "
        f"Line weight tolerance: {scan_cfg['line_weight_tolerance']} pt | "
        f"Color tolerance: {scan_cfg['color_tolerance']} | "
        f"Position tolerance: {scan_cfg['position_tolerance']} pt"
    )

    if not signatures:
        print(subject_items.color_text("  No stamp line signatures found to scan with.", subject_items.Ansi.RED))
        return []

    for signature in signatures:
        signature_weight = f"{signature['line_weight']:.2f}pt"
        match_weight = f"{signature['match_line_weight']:.2f}pt"
        print(
            f"  Signature {subject_items.color_text(signature['target'], subject_items.Ansi.CYAN)} | "
            f"stamp weight {subject_items.color_text(signature_weight, subject_items.Ansi.YELLOW)} | "
            f"matched vector weight {subject_items.color_text(match_weight, subject_items.Ansi.YELLOW)} | "
            f"color {subject_items.color_text(subject_items.format_color(signature['stroke_color']), subject_items.Ansi.MAGENTA)} | "
            f"lengths {subject_items.color_text(subject_items.format_lengths(signature['lengths']), subject_items.Ansi.GREEN)}"
        )

    page_matches = find_matching_lines(pdf_path, subject_matches, cfg)
    total_lines = 0

    for page in page_matches:
        line_count = len(page["lines"])
        total_lines += line_count
        page_label = f"Page {page['page']}"
        print(
            f"\n{subject_items.color_text(page_label, subject_items.Ansi.BLUE)} | "
            f"matching lines: {subject_items.color_text(str(line_count), subject_items.Ansi.GREEN)}"
        )
        for line in page["lines"]:
            print(format_line(line, line["matched_targets"]))

    print(
        f"\nTotal matching page lines: "
        f"{subject_items.color_text(str(total_lines), subject_items.Ansi.GREEN)}"
    )
    save_layered_matching_pdf(pdf_path, page_matches, cfg)
    return page_matches


def main():
    cfg = subject_items.load_config()
    pdf_path = subject_items.select_pdf(cfg["paths"]["input_folder"])
    if not pdf_path:
        return

    targets = cfg.get("targets", [])
    subject_matches, _ = subject_items.scan_pdf(pdf_path, targets)
    report_matching_lines(pdf_path, subject_matches, cfg)


if __name__ == "__main__":
    main()
