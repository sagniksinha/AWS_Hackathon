# Sample call from terminal (Windows)
# python pdf_filler.py input_pdf="C:\Users\sagni\Documents\Personal Files\Hackathon\Form1.pdf" output_pdf="C:\Users\sagni\Documents\Personal Files\Hackathon\output.pdf" borrower_name="John Doe" authorized_signatory="Sagnik Sinha" business_day="07Sep2025" margin_amount="2,000.00" interest_rate=2

import io
import sys
from datetime import datetime
from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

def fill_pdf(
    input_pdf: str,
    output_pdf: str,
    borrower_name: str,
    authorized_signatory: str,
    business_day: str,
    margin_amount: str,
    interest_rate
):
    """
    Fills a PDF form with given text and marks an X at the correct interest_rate position.
    All coordinates are in millimeters.
    """

    # Date text for today's date in "Month DD, YYYY" format
    date_text = datetime.now().strftime("%B %d, %Y")

    # List of fields to write (x, y, text)
    text_fields = [
        (90,   65,  date_text),            # Name of MLT&C
        (140,  36,  date_text),            # Date of request
        (25,  202,  borrower_name),        # Borrower name
        (37, 215.5, authorized_signatory), # Authorized signatory
        (118, 118,  business_day),         # Business day
        (111,126.4, margin_amount),        # Margin amount
    ]

    # Interest rate position mapping (key: rate, value: (x, y) position for "X")
    rate_coords = {
        1: (51.4, 144),
        2: (51.4, 152.8),
        3: (51.4, 161.38),
        4: (51.4, 170),
    }

    # Read the original PDF and get the first page
    original = PdfReader(input_pdf)
    page0 = original.pages[0]

    # Convert PDF page size to millimeters
    w_mm = float(page0.mediabox.width) * 0.352778
    h_mm = float(page0.mediabox.height) * 0.352778

    # Create overlay PDF with same size as original
    overlay = FPDF(unit="mm", format=(w_mm, h_mm))
    overlay.add_page()
    overlay.set_font("Courier", size=11)
    overlay.set_text_color(255, 0, 0)  # Red text

    # Place all text fields
    for x, y, txt in text_fields:
        overlay.text(x, y, str(txt or ""))

    # Determine "X" position for interest rate
    coords = None
    try:
        coords = rate_coords.get(int(interest_rate))
    except (TypeError, ValueError):
        coords = None

    # Place "X" if a valid interest rate (1-4) was provided
    if coords:
        overlay.set_font("Courier", "B", size=11)  # Bold for better visibility
        overlay.text(*coords, "X")
        overlay.set_font("Courier", size=11)       # Reset font to normal

    # Convert overlay to bytes and merge with original page
    overlay_bytes = overlay.output(dest="S").encode("latin1")
    overlay_reader = PdfReader(io.BytesIO(overlay_bytes))
    page0.merge_page(overlay_reader.pages[0])

    # Save the merged PDF
    writer = PdfWriter()
    writer.add_page(page0)
    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"Wrote: {output_pdf}")


if __name__ == "__main__":
    # Parse command-line arguments of the form key=value
    args = {}
    for arg in sys.argv[1:]:
        if "=" in arg:
            key, value = arg.split("=", 1)
            args[key] = value

    # Ensure all required arguments are provided
    required_keys = [
        "input_pdf",
        "output_pdf",
        "borrower_name",
        "authorized_signatory",
        "business_day",
        "margin_amount",
        "interest_rate"
    ]
    for key in required_keys:
        if key not in args:
            print(f"Missing required argument: {key}")
            sys.exit(1)

    # Call the fill function with parsed arguments
    fill_pdf(
        input_pdf=args["input_pdf"],
        output_pdf=args["output_pdf"],
        borrower_name=args["borrower_name"],
        authorized_signatory=args["authorized_signatory"],
        business_day=args["business_day"],
        margin_amount=args["margin_amount"],
        interest_rate=args["interest_rate"]
    )
