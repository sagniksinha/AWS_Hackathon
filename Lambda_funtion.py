import json
import boto3
import pandas as pd
import io
import sys
from datetime import datetime
from fpdf import FPDF
import pypdf
import cryptography
from pypdf import PdfReader, PdfWriter
# print("cryptography version:", cryptography.__version__)
# print("cryptography path:", cryptography.__file__)

s3_client = boto3.client("s3")
sns_client = boto3.client("sns")
TopicArn = "arn:aws:sns:us-east-1:255327957732:Automation_Alchemists"

def read_data(df):
    """
    Reads the first row of a credit agreement CSV and returns selected fields.

    Parameters:
        csv_path (str): Path to the CSV file.

    Returns:
        tuple: (client_name, loan_amount, generation_date)
    """
    try:
        first_row = df.iloc[0]
        client_name = first_row['client_name']
        loan_amount = first_row['loan_amount']
        generation_date = first_row['generation_date']
        return client_name, loan_amount, generation_date
    except Exception as e:
        print(f"Error reading the file: {e}")
        return None, None, None

def send_mail_sns(sns_client=sns_client, TopicArn=TopicArn, subject="Test", message="Test"):
    """
    Sends an email using SNS.
    """
    try:
        resp = sns_client.publish(
            TopicArn=TopicArn,
            Subject=subject,
            Message=message,
            MessageStructure="string"
        )
        return {"status": "ok", "messageId": resp["MessageId"]}
    except Exception as e:
        print(f"Error publishing to sns : {e}")
        raise

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
    # Merge overlay with original page
    page0.merge_page(overlay_reader.pages[0])

    # **Write the merged page to a new PDF file**
    writer = PdfWriter()
    writer.add_page(page0)
    with open(output_pdf, "wb") as f:
        writer.write(f)
    print(f"Wrote filled PDF to: {output_pdf}")


def lambda_handler(event, context):
    # TODO implement
    response = s3_client.get_object(Bucket='automation-alchemist-final', Key="Input/populated_credit_agreements.csv")

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 get_object response. Status - {status}")
        books_df = pd.read_csv(response.get("Body"))

        # Loop through each row in the CSV
        for idx, row in books_df.iterrows():
            client_name = row['client_name']
            loan_amount = row['loan_amount']
            generation_date = row['generation_date']
            agreement_id = row['application_id']
            client_id = row['client_id']

            # Download PDF from S3 for each row
            pdf_object = s3_client.get_object(
                Bucket='automation-alchemist-final',
                Key="Input/Form1.pdf"
            )
            pdf_bytes = pdf_object['Body'].read()
            input_pdf_path = "/tmp/Form1.pdf"
            with open(input_pdf_path, "wb") as f:
                f.write(pdf_bytes)

            # Create timestamp for uniqueness
            timestamp = datetime.now().strftime('%d%b%Y_%H-%M-%S')

            # Build output file name with agreement_id, client_id, and timestamp
            output_pdf_path = f"/tmp/{agreement_id}_{client_id}_{timestamp}.pdf"

            # Fill PDF for this row
            fill_pdf(
                input_pdf=input_pdf_path,
                output_pdf=output_pdf_path,
                borrower_name=client_name,
                authorized_signatory="Sagnik Sinha",
                business_day=generation_date,
                margin_amount=loan_amount,
                interest_rate=2
            )

            # Upload to S3
            output_bucket = "automation-alchemist-final"
            output_key = f"Output/{agreement_id}_{client_id}_{timestamp}.pdf"
            s3_client.upload_file(output_pdf_path, output_bucket, output_key)
            print(f"Uploaded: s3://{output_bucket}/{output_key}")

        s3_client.upload_file(output_pdf_path, output_bucket, output_key)
        print(f"Uploaded the filled PDF to s3://{output_bucket}/{output_key}")
        subject = f"Notification: Form is Ready"
        message = "Dear Sir/Madam,\nForm is ready for your review.\nPlease do not reply to this message, this is an automated email.\nRegards,\nAutomation Alchemist"
        send_mail_sns(subject = subject, message = message)
        
    else:
        print(f"Unsuccessful S3 get_object response. Status - {status}")
    # print(event)
    return {
        'statusCode': 200,
        'body': json.dumps('Completed')
    }

    
