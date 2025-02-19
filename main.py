import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib

def initialize_database():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Balapavi03",
        database="stock"
    )
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stock_name VARCHAR(255) NOT NULL,
            percentage FLOAT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_shares (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id VARCHAR(255) NOT NULL,
            total_percentage FLOAT NOT NULL,
            stock_name VARCHAR(255) NOT NULL,
            allocated_percentage FLOAT NOT NULL
        )
    """)
    return cursor, db


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def signup(cursor, db):
    st.write("Signup")
    with st.form("signup_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Signup")
        if submitted:
            if password == confirm_password:
                try:
                    password_hash = hash_password(password)
                    cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
                    db.commit()
                    st.success("Signup successful! Please login.")
                except mysql.connector.Error as err:
                    st.error(f"Error: {err}")
            else:
                st.error("Passwords do not match.")


def login(cursor):
    st.write("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            password_hash = hash_password(password)
            cursor.execute("SELECT * FROM users WHERE username = %s AND password_hash = %s", (username, password_hash))
            user = cursor.fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful!")
            else:
                st.error("Invalid username or password.")


def stock_manager(cursor, db):
    st.title("Stock Manager")

    if st.button("Add Stock"):
        st.session_state.page = "add_stock"
    if st.button("Edit Stock"):
        st.session_state.page = "edit_stock"
    if st.button("Delete Stock"):
        st.session_state.page = "delete_stock"
    if st.button("Allocate Shares"):
        st.session_state.page = "allocate_shares"
    if st.button("View Allocated Shares"):
        st.session_state.page = "view_allocated_shares"


    if "page" in st.session_state:
        if st.session_state.page == "add_stock":
            add_data(cursor, db)
        elif st.session_state.page == "edit_stock":
            edit_data(cursor, db)
        elif st.session_state.page == "delete_stock":
            delete_data(cursor, db)
        elif st.session_state.page == "allocate_shares":
            allocate_shares(cursor, db)
        elif st.session_state.page == "view_allocated_shares":
            view_allocated_shares(cursor)


    st.write("Current Stock Data")
    data = fetch_data(cursor)
    if data:
        st.table(data)
    else:
        st.write("No stock data found.")


def fetch_data(cursor):
    cursor.execute("SELECT stock_name, percentage FROM stock_data")
    return cursor.fetchall()


def fetch_allocated_shares(cursor):
    cursor.execute("SELECT customer_id, total_percentage, stock_name, allocated_percentage FROM customer_shares")
    return cursor.fetchall()


def add_data(cursor, db):
    st.write("Add Stock")
    with st.form("add_stock_form"):
        stock_name = st.text_input("Stock Name")
        percentage = st.number_input("Percentage", min_value=0.0, max_value=100.0, step=0.1)
        submitted = st.form_submit_button("Add")
        if submitted:
            if stock_name and percentage:
                cursor.execute("INSERT INTO stock_data (stock_name, percentage) VALUES (%s, %s)", (stock_name, float(percentage)))
                db.commit()
                st.success("Stock added successfully!")


def edit_data(cursor, db):
    st.write("Edit Stock")
    data = fetch_data(cursor)
    if data:
        stock_names = [row[0] for row in data]
        selected_stock = st.selectbox("Select Stock to Edit", stock_names)
        selected_data = next(row for row in data if row[0] == selected_stock)
        
        with st.form("edit_stock_form"):
            new_stock_name = st.text_input("Stock Name", value=selected_data[0])
            new_percentage = st.number_input("Percentage", value=selected_data[1], min_value=0.0, max_value=100.0, step=0.1)
            submitted = st.form_submit_button("Save")
            if submitted:
                if new_stock_name and new_percentage:
                    cursor.execute("UPDATE stock_data SET stock_name=%s, percentage=%s WHERE stock_name=%s AND percentage=%s",
                                (new_stock_name, float(new_percentage), selected_data[0], selected_data[1]))
                    db.commit()
                    st.success("Stock updated successfully!")


def delete_data(cursor, db):
    st.write("Delete Stock")
    data = fetch_data(cursor)
    if data:
        stock_names = [row[0] for row in data]
        selected_stock = st.selectbox("Select Stock to Delete", stock_names)
        selected_data = next(row for row in data if row[0] == selected_stock)
        
        if st.button("Delete"):
            cursor.execute("DELETE FROM stock_data WHERE stock_name=%s AND percentage=%s", (selected_data[0], selected_data[1]))
            db.commit()
            st.success("Stock deleted successfully!")


def allocate_shares(cursor, db):
    st.write("Allocate Shares")
    with st.form("allocate_shares_form"):
        total_percentage = st.number_input("Total Percentage", min_value=0.0, max_value=100.0, step=0.1)
        submitted = st.form_submit_button("Allocate")
        if submitted:
            if total_percentage:
                cursor.execute("SELECT stock_name, percentage FROM stock_data")
                stocks = cursor.fetchall()
                total_stock_percentage = sum(stock[1] for stock in stocks)
                if total_percentage > total_stock_percentage:
                    st.error("Not enough shares available to allocate.")
                    return
                
                allocations = []
                for stock in stocks:
                    stock_name, stock_percentage = stock
                    allocated_percentage = (stock_percentage / total_stock_percentage) * float(total_percentage)
                    if allocated_percentage > stock_percentage:
                        allocated_percentage = stock_percentage  # Ensure we don't allocate more than available
                    allocations.append((st.session_state.username, total_percentage, stock_name, allocated_percentage))
                    cursor.execute("UPDATE stock_data SET percentage = percentage - %s WHERE stock_name = %s", (allocated_percentage, stock_name))
                
                cursor.executemany("""
                    INSERT INTO customer_shares (customer_id, total_percentage, stock_name, allocated_percentage)
                    VALUES (%s, %s, %s, %s)
                """, allocations)
                db.commit()
                st.success("Shares allocated successfully!")


def view_allocated_shares(cursor):
    st.write("Allocated Shares")
    allocated_shares = fetch_allocated_shares(cursor)
    if allocated_shares:
        st.table(allocated_shares)
    else:
        st.write("No allocated shares found.")

def main():
    st.title("Stock Management System")

    cursor, db = initialize_database()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.sidebar.write("Login or Signup")
        if st.sidebar.button("Login"):
            st.session_state.page = "login"
        if st.sidebar.button("Signup"):
            st.session_state.page = "signup"

        if "page" in st.session_state:
            if st.session_state.page == "login":
                login(cursor)
            elif st.session_state.page == "signup":
                signup(cursor, db)
    else:
        st.sidebar.write(f"Welcome, {st.session_state.username}!")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.page = None
            st.rerun()
        stock_manager(cursor, db)

if __name__ == "__main__":
    main()