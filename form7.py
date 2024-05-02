from datetime import datetime

import streamlit as st
import sqlite3
import pandas as pd
import base64
import gspread
from io import BytesIO


# Create SQLite database and table
conn = sqlite3.connect('data.db')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        birth_year INTEGER,
        phone_number TEXT,
        city TEXT,
        filial TEXT,
        current_date TEXT,
        selected_source TEXT
    )
''')


conn.commit()
conn.close()


# Function to authenticate with Google Sheets
def authenticate_gspread():
    # Load Google Sheets API credentials
    sa = gspread.service_account(filename='credits_mobi.json')
    return sa


# Function to duplicate data to Google Sheets
def duplicate_to_gsheet(new_row, current_date, source):
    # Authenticate with Google Sheets
    gc = authenticate_gspread()

    # Create a new Google Sheets spreadsheet
    sh = gc.open("MyTasks")

    # Select the first sheet (index 0)
    worksheet = sh.worksheet("Data")

    # Check if there's any content in the worksheet
    existing_data = worksheet.get_all_values()

    # Get existing headers if they exist
    headers = existing_data[0] if existing_data else None

    if not headers:
        headers = ['ID', 'Имя', 'Фамилия',
                   'Год рождения', 'Телефон', 'Город', "Филиал", 'Дата', 'Источник']
        worksheet.append_row(headers)
    else:
        # Insert the new row only if it's different from the last row in the sheet
        last_row = existing_data[-1]  # Get the last row
        if not last_row or last_row != new_row:
            worksheet.append_row(new_row)


def save_data():
    # Get input values
    input1 = st.empty()
    input2 = st.empty()
    input3 = st.empty()
    input4 = st.empty()
    input6 = st.empty()
    input7 = st.empty()
    input_filial = st.empty()  # Add this line for FILIAL input
    first_name = input1.text_input("ISM", key="first_name")
    last_name = input2.text_input("FAMILIYA", key="last_name")
    birth_date = input3.date_input("TUGILGAN YILI", min_value=datetime(1940, 1, 1), key="birth_date", value=None)
    phone_number = input4.text_input("TELEFON NOMERI", key="phone_number")
    city = input6.text_input("YASHASH SHAHRI", key="city")

    # Add a dropdown for FILIAL input
    filial_options = ["JOMBOY", "JUMA", "TAYLOQ", "SOGDIANA", "GAGARIN"]  # Add your list of filials here
    selected_filial = input_filial.selectbox("FILIAL", filial_options)
    # source_options = ["Флайер", "Инстаграм", "Телеграм", "Оператор", "YouTube", "Танишлардан", "Бошка"]
    # selected_source = st.selectbox("Источник данных", source_options)
    selected_source = input7.text_input("QAERDAN BILGAN", key="selected_source")
    # Save button
    if st.button("Сохранить"):
        # Check if all fields are filled
        if not first_name or not phone_number:
            st.error("Пожалуйста, заполните Имя и Телефон перед сохранением.")
            return

        # Format birth date to the specified format
        formatted_birth_date = birth_date.strftime("%d-%m-%Y")
        current_date = datetime.today().strftime('%d-%m-%Y')
        # Save data to SQLite database
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (first_name, last_name, birth_year, \
                  phone_number, city, filial, current_date, selected_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (first_name, last_name, formatted_birth_date,
                   phone_number, city, selected_filial, current_date, selected_source))
        conn.commit()

        # Fetch the last inserted data from SQLite
        c.execute("SELECT * FROM users ORDER BY ID DESC LIMIT 1")
        new_data = c.fetchone()
        conn.close()

        # Show success message
        st.success("Данные успешно сохранены.")

        # Update Google Sheets with the new data
        if new_data:
            new_row = list(new_data)

            duplicate_to_gsheet(new_row, current_date, selected_source)

        # Clear input fields after saving
        input1.text_input("ISM", key="first_name2")
        input2.text_input("FAMILIYA", key="last_name2")
        input3.date_input("TUGILGAN YILI", min_value=datetime(1940, 1, 1), key="birth_date2", value=None)
        input4.text_input("TELEFON NOMERI", key="phone_number2")
        input6.text_input("YASHASH SHAHRI", key="city2")
        input7.text_input("QAERDAN BILGAN", key="selected_source2")

        # input_filial.empty()  # Clear FILIAL input

def show_data():
    # Get data from SQLite database
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    data = c.fetchall()
    conn.close()

    # Display data with pagination
    page_num = st.experimental_get_query_params().get("page", ["1"])[0]
    page_size = 10
    start_idx = (int(page_num) - 1) * page_size
    end_idx = start_idx + page_size

    df = pd.DataFrame(data, columns=['ID', 'Имя', 'Фамилия', 'Год рождения',
                                     'Телефон', 'Город', 'Филиал', 'Дата заполнение', 'Источник'])
    paginated_data = df.iloc[start_idx:end_idx]

    st.table(paginated_data)

    # Add pagination controls
    num_pages = len(df) // page_size + (len(df) % page_size > 0)
    st.write(f"Страница {page_num} из {num_pages}")

    prev_page, next_page = st.columns(2)
    if prev_page.button("Предыдущая страница", key="prev_page"):
        new_page_num = max(1, int(page_num) - 1)
        st.experimental_set_query_params(page=str(new_page_num))
    if next_page.button("Следующая страница", key="next_page"):
        new_page_num = min(num_pages, int(page_num) + 1)
        st.experimental_set_query_params(page=str(new_page_num))

    # Define a text input for the password
    password = st.text_input("Enter Admin Password", type="password")
    if is_admin(password):
        # Add download button for Excel file
        download_button = st.button("Скачать Excel файл")
        if download_button:
            download_excel(df)

        if st.button('Delete All Data'):
            # Delete data from the SQLite database
            conn = sqlite3.connect('data.db')
            c = conn.cursor()
            c.execute('DELETE FROM users')
            conn.commit()
            conn.close()
            reset_table()
            st.success('All data deleted.')
    else:
        st.warning('You are not authorized to delete data.')


def download_excel(df):
    # Create a link for downloading the Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
    output.seek(0)

    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="data.xlsx">Скачать Excel файл</a>'
    st.markdown(href, unsafe_allow_html=True)


def is_admin(password):
    return password == "12345"

def reset_table():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("DELETE FROM SQLITE_SEQUENCE WHERE NAME = 'users'")
    conn.commit()
    conn.close()
    st.success("ID values reset.")

# Create Streamlit app
st.title("MobiCenter")

# Save data section
st.header("Сохранение данных")
save_data()

# Show data section
st.header("Просмотр данных")
show_data()
