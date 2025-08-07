import pandas as pd

def read_first_credit_agreement(csv_path = r'C:\Users\sagni\Documents\Personal Files\Hackathon\populated_credit_agreements.csv'):
    """
    Reads the first row of a credit agreement CSV and returns selected fields.

    Parameters:
        csv_path (str): Path to the CSV file.

    Returns:
        tuple: (client_name, loan_amount, generation_date)
    """
    try:
        df = pd.read_csv(csv_path)
        first_row = df.iloc[0]

        client_name = first_row['client_name']
        loan_amount = first_row['loan_amount']
        generation_date = first_row['generation_date']

        return client_name, loan_amount, generation_date

    except Exception as e:
        print(f"Error reading the file: {e}")
        return None, None, None

if __name__ == "__main__":
    client_name, loan_amount, generation_date = read_first_credit_agreement()

    print("Client Name:", client_name)
    print("Loan Amount:", loan_amount)
    print("Generation Date:", generation_date)