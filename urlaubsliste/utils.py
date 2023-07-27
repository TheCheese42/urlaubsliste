from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import black
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Paragraph,
    Table,
    TableStyle,
)


def deep_merge(dict1: dict, dict2: dict):
    """
    `dict2` will be modified
    """
    for key, val in dict1.items():
        if isinstance(val, dict):
            dict2_node = dict2.setdefault(key, {})
            deep_merge(val, dict2_node)
        elif isinstance(val, list):
            dict2_node = dict2.setdefault(key, [])
            dict2_node.extend(val)
        else:
            if key not in dict2:
                dict2[key] = val

    return dict2


def create_report(list_, file):
    if not list_.categories:
        raise ValueError("List is empty")
    table_data = []
    # Set first row
    headerstyle = ParagraphStyle(
        "Tableheader",
        fontName='Helvetica-Bold',
        fontSize=12,
    )
    table_data.append(
        [Paragraph(i, style=headerstyle) for i in list_.categories]
    )
    longest_category_length = 0
    for category in list_.categories:
        category_length = list_.get_amount_of_items_for_category(
            category
        )
        if category_length > longest_category_length:
            longest_category_length = category_length
    normalstyle = ParagraphStyle(
        "Tablecontent",
        fontName='Helvetica',
        fontSize=10,
    )
    for i in range(longest_category_length):
        values = []
        for category in list_.categories:
            content = list_.get_items_for_category(category)
            try:
                value = Paragraph(content[i], style=normalstyle)
            except IndexError:
                value = Paragraph("", style=normalstyle)
            values.append(value)
        table_data.append(values)

    doc = SimpleDocTemplate(file, filesize=A4)
    style = getSampleStyleSheet()['Title']
    style.fontName = 'Helvetica-Bold'
    style.fontSize = 24
    style.textColor = black
    style.alignment = TA_CENTER
    elements = []
    label = list_.name

    available_width = doc.width
    num_columns = len(table_data[0])
    column_width = available_width / num_columns
    table = Table(table_data, colWidths=[column_width] * num_columns)
    table_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # X-Align
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # V-Align
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Table font
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # Table font size
        ('FONTSIZE', (0, 0), (-1, 0), 12),  # Header font size
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),  # Table bottom padding
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),  # Header bottom padding
        ('GRID', (0, 0), (-1, -1), 1, black),  # Visible grid
        ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable textwrap
    ])
    table.setStyle(table_style)

    elements.append(Paragraph(label, style))
    elements.append(Spacer(1, 50))
    elements.append(table)
    doc.build(elements)
