import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define the scope
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']

# Add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name('useful-mile-334600-ce60f5954ea9.json', scope)

# Authorize the clientsheet
client = gspread.authorize(creds)

# Open the spreadsheet
sheet = client.open('Curr Exchg Table').sheet1

# Edit the spreadsheet
sheet.update_cell(1, 1, "New Value")  # Example: update the value of cell A1
