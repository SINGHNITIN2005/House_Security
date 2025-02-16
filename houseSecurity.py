import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from io import BytesIO
import requests
import sqlite3
import time
import smtplib
from email.message import EmailMessage
import random
import subprocess
import re
import os
import cv2
import pandas as pd
import pygame 


otp_store = {}
attempts = {}
lockout_state = {} 

def get_db_connection():
    return sqlite3.connect('mew_users.db')

def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      name TEXT NOT NULL,
                      email TEXT NOT NULL UNIQUE,
                      password TEXT NOT NULL,
                      phone TEXT
                      )''')
    conn.commit()
    conn.close()

def update_table_schema():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN phone TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists or some other issue
    conn.close()

def insert_user(name, email, password, phone):
    retry_count = 5
    for _ in range(retry_count):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)',
                           (name, email, password, phone))
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError:
            time.sleep(0.5)  # Wait for a bit before retrying
    messagebox.showerror("Error", "Unable to insert user. Please try again later.")

def validate_user(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email=? AND password=?', (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

def update_password(email, new_password):
    retry_count = 5
    for _ in range(retry_count):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET password=? WHERE email=?', (new_password, email))
            conn.commit()
            conn.close()
            export_to_excel() 
            return
        except sqlite3.OperationalError:
            time.sleep(0.5)  # Wait for a bit before retrying
    messagebox.showerror("Error", "Unable to update password. Please try again later.")

def delete_user(name,email, phone, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE name =? AND email=? AND phone=? AND password=?', (name,email, phone, password))
    
    if cursor.rowcount == 0:
        print("No user found with the provided details.")
    else:
        print("Users data  deleted successfully.")
    
    conn.commit()
    conn.close()
    # After deleting the user from the database, also remove them from the Excel file
    remove_from_excel(email)

def remove_from_excel(email):
    try:
        # Load the existing Excel file
        df = pd.read_excel('users_data.xlsx')
        
        # Remove the user with the given email
        df = df[df['email'] != email]
        
        # Save the updated DataFrame back to the Excel file
        df.to_excel('users_data.xlsx', index=False)
        print(f"User with email {email} removed from Excel file.")
    except Exception as e:
        print(f"Failed to remove user from Excel: {e}")
        
def terminal_delete_user():
    print("Enter the details of the user to delete:")
    name = input("Name: ")
    email = input("Email: ")
    phone = input("Phone Number: ")
    password = input("Password: ")

    if not name or not email or not phone or not password:
        print("All fields are required.")
        return

    delete_user(name,email, phone, password)

def delete_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users')
    conn.commit()
    conn.close()
    print("All user data deleted from the database.")
    clear_excel_file()  

def clear_excel_file():
    try:
        df = pd.DataFrame(columns=['name', 'email', 'password', 'phone'])
        df.to_excel('users_data.xlsx', index=False)
        print("All user data removed from Excel file.")
    except Exception as e:
        print(f"Failed to clear Excel file: {e}")

def terminal_delete_all_users():
    print("Are you sure you want to delete all user data? (yes/no)")
    confirm = input()
    if confirm.lower() == 'yes':
        delete_all_users()
    else:
        print("Operation canceled.")  
        
           
# Add a function to send alert emails

def send_alert_email(email_address):
    msg = EmailMessage()
    msg.set_content("We noticed multiple failed login attempts for your account. If this was not you, please contact your nearby Police Station Booth.\n Thank You\n Aapka Apna House Kavachh")
    msg['Subject'] = 'Alert: Multiple Failed Login Attempts'
    msg['From'] = 'fsana112112@gmail.com'  # Replace with your email address
    msg['To'] = email_address

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:  # Replace with your SMTP server details
            server.starttls()
            server.login('fsana112112@gmail.com', 'vkld jeoh hydx qclw')  # Replace with your email credentials
            server.send_message(msg)
        print(f"Alert email sent to {email_address}")
    except Exception as e:
        print(f"Failed to send alert email: {e}")
        raise

# Additional dictionary to track lockout state
  
 
def play_alarm_sound():
    pygame.mixer.init()
    pygame.mixer.music.load(r"E:\Tkinter Login Page\Security Alarm Sound Effect.mp3")  # Update with correct path
    pygame.mixer.music.play() 
def signin():
    email = email_entry.get()
    password = password_entry.get()
    current_time = time.time()

    # Check if the user is currently locked out
    if email in lockout_state:
        lockout_end_time = lockout_state[email]
        if current_time < lockout_end_time:
            messagebox.showerror("Error", f"Too many incorrect attempts. Please wait until {time.strftime('%H:%M:%S', time.localtime(lockout_end_time))} before trying again.")
            return
        else:
            # Lockout period has expired
            del lockout_state[email]
            email_entry.config(state=tk.NORMAL)  # Re-enable the email entry if locked
            password_entry.config(state=tk.NORMAL)  # Re-enable the password entry if locked

    if email and password:
        user = validate_user(email, password)
        if user:
            attempts[email] = [0, current_time]
            messagebox.showinfo("Success", "Login successful! Now your door is open.")
            access_webcam(email)  # Open the webcam
        else:
            if email in attempts:
                attempts[email][0] += 1
                # Send an alert email if there are more than 3 failed attempts
                if attempts[email][0] >= 3:
                    try:
                        send_alert_email(email)
                        # Play alarm sound
                        play_alarm_sound()
                        access_webcam(email)
                        
                        # Set lockout period of 3 minutes
                        lockout_state[email] = current_time + 180  # 3 minutes cooldown
                        # Disable the password entry
                        password_entry.config(state=tk.DISABLED)
                        email_entry.config(state=tk.DISABLED)  # Optional: Disable email entry too
                        messagebox.showerror("Error", "Too many incorrect attempts. Please wait for 3 minutes before trying again.")
                    except Exception as e:
                        print(f"Failed to send alert email: {e}")
            else:
                attempts[email] = [1, current_time]
            messagebox.showerror("Error", "Invalid email or password.")
    else:
        messagebox.showerror("Error", "Please enter your email and password.")
def on_enter_email(e):
    email_entry.delete(0, 'end')

def on_leave_email(e):
    email = email_entry.get()
    if email == '':
        email_entry.insert(0, 'Email')

def on_enter_password(e):
    password_entry.delete(0, 'end')
    password_entry.config(show='*')

def on_leave_password(e):
    password = password_entry.get()
    if password == '':
        password_entry.config(show='')
        password_entry.insert(0, 'Password')

def toggle_password():
    if show_password_var.get():
        password_entry.config(show='')
    else:
        password_entry.config(show='*')

def open_signup():
    signup_window = tk.Toplevel(root)
    signup_window.title("Sign Up")
    signup_window.geometry("400x600")
    signup_window.config(bg="#4f4e4d")
    signup_window.resizable(False, False)

    tk.Label(signup_window, text="Sign Up", fg="white", bg="#4f4e4d", font=('yu gothic ui', 25, "bold")).pack(pady=20)

    def create_entry_with_line(parent, label_text):
        tk.Label(parent, text=label_text, fg="white", bg="#4f4e4d", font=('Microsoft YaHei UI Light', 12)).pack(anchor='w', padx=20, pady=(10, 0))
        entry = tk.Entry(parent, width=40, border=0, bg="#4f4e4d", fg="white", font=('Microsoft YaHei UI Light', 12))
        entry.pack(padx=20)
        
        canvas = tk.Canvas(parent, width=350, height=2, bg="#ffffff", highlightthickness=0)
        canvas.pack(padx=20, pady=(0, 10))
        canvas.create_line(0, 1, 350, 1, fill="#ffffff")
        
        return entry

    name_entry = create_entry_with_line(signup_window, "Name")
    email_entry = create_entry_with_line(signup_window, "Email")
    password_entry = create_entry_with_line(signup_window, "Create Password")
    confirm_password_entry = create_entry_with_line(signup_window, "Confirm Password")
    phone_entry = create_entry_with_line(signup_window, "Phone Number")

    def signup():
        name = name_entry.get()
        email = email_entry.get()
        password = password_entry.get()
        confirm_password = confirm_password_entry.get()
        phone = phone_entry.get()

        # Basic validation checks
        if not name or not email or not password or not confirm_password or not phone:
            messagebox.showerror("Error", "All fields are required.")
            return

        if password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters long.")
            return

        # Email validation (basic)
        if '@' not in email or '.' not in email:
            messagebox.showerror("Error", "Invalid email format.")
            return

        # Phone number validation
        phone_pattern = re.compile(r'^[6789]\d{9}$')
        if not phone_pattern.match(phone):
            messagebox.showerror("Error", "Please enter a correct phone number (starts with 6/7/8/9 and is 10 digits long).")
            return
        try:
            insert_user(name, email,password,phone)
            export_to_excel()
            messagebox.showinfo("Success", "Account created successfully!")
            signup_window.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Email already exists.")
        except sqlite3.OperationalError:
            messagebox.showerror("Error", "Database is locked. Please try again later.")

    tk.Button(signup_window, text="Sign Up", bg='#67a1f8', fg='white', command=signup).pack(pady=20)

def generate_otp(length=6):
    otp = ''.join([str(random.randint(0, 9)) for _ in range(length)])
    return otp

def send_otp_email(email_address, otp):
    msg = EmailMessage()
    msg.set_content(f"Your OTP is: {otp}")
    msg['Subject'] = 'Your OTP Code'
    msg['From'] = 'fsana112112@gmail.com'  # Replace with your email address
    msg['To'] = email_address

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:  # Replace with your SMTP server details
            server.starttls()
            server.login('fsana112112@gmail.com', 'vkld jeoh hydx qclw')  # Replace with your email credentials
            server.send_message(msg)
        print(f"OTP sent to {email_address}")
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        raise

def open_forgot_password():
    forgot_password_window = tk.Toplevel(root)
    forgot_password_window.title("Forgot Password")
    forgot_password_window.geometry("400x600")
    forgot_password_window.config(bg="#4f4e4d")
    forgot_password_window.resizable(False, False)

    tk.Label(forgot_password_window, text="Reset Password", fg="white", bg="#4f4e4d", font=('yu gothic ui', 25, "bold")).pack(pady=20)

    def create_entry_with_line(parent, label_text):
        tk.Label(parent, text=label_text, fg="white", bg="#4f4e4d", font=('Microsoft YaHei UI Light', 12)).pack(anchor='w', padx=20, pady=(10, 0))
        entry = tk.Entry(parent, width=40, border=0, bg="#4f4e4d", fg="white", font=('Microsoft YaHei UI Light', 12))
        entry.pack(padx=20)
        
        canvas = tk.Canvas(parent, width=350, height=2, bg="#ffffff", highlightthickness=0)
        canvas.pack(padx=20, pady=(0, 10))
        canvas.create_line(0, 1, 350, 1, fill="#ffffff")
        
        return entry

    email_entry = create_entry_with_line(forgot_password_window, "Email")
    phone_entry = create_entry_with_line(forgot_password_window, "Phone Number")

    def request_otp():
        email = email_entry.get()
        phone = phone_entry.get()
        
       # Validate inputs
        if not email or not phone:
           messagebox.showerror("Error", "Email and Phone Number are required.")
           return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT phone FROM users WHERE email=?', (email,))
        user_phone = cursor.fetchone()
        conn.close()
        # Check if the phone number matches the one in the database for the given email
        if user_phone and user_phone[0] == phone:
          otp = generate_otp()
          otp_store[phone] = otp
         
          try:
            send_otp_email(email, otp)
            messagebox.showinfo("Info", "OTP sent to your email.")
            open_reset_password_window(email, phone)
            forgot_password_window.destroy()
          except Exception as e:
            messagebox.showerror("Error", f"Failed to send OTP: {e}")  
            print(e)
        else:
          messagebox.showerror("Error", "Please! Check your email and phone number.")
    tk.Button(forgot_password_window, text="Send OTP", bg='#67a1f8', fg='white', command=request_otp).pack(pady=10)
          
def open_reset_password_window(email, phone):
    reset_password_window = tk.Toplevel(root)
    reset_password_window.title("Reset Password")
    reset_password_window.geometry("400x600")
    reset_password_window.config(bg="#4f4e4d")
    reset_password_window.resizable(False, False)

    tk.Label(reset_password_window, text="Reset Password", fg="white", bg="#4f4e4d", font=('yu gothic ui', 25, "bold")).pack(pady=20)

    def create_entry_with_line(parent, label_text):
        tk.Label(parent, text=label_text, fg="white", bg="#4f4e4d", font=('Microsoft YaHei UI Light', 12)).pack(anchor='w', padx=20, pady=(10, 0))
        entry = tk.Entry(parent, width=40, border=0, bg="#4f4e4d", fg="white", font=('Microsoft YaHei UI Light', 12))
        entry.pack(padx=20)
        
        canvas = tk.Canvas(parent, width=350, height=2, bg="#ffffff", highlightthickness=0)
        canvas.pack(padx=20, pady=(0, 10))
        canvas.create_line(0, 1, 350, 1, fill="#ffffff")
        
        return entry

    otp_entry = create_entry_with_line(reset_password_window, "OTP")
    new_password_entry = create_entry_with_line(reset_password_window, "New Password")
    confirm_password_entry = create_entry_with_line(reset_password_window, "Confirm Password")
          
    def reset_password():
        # email = email_entry.get()
        # phone = phone_entry.get()
        otp = otp_entry.get()
        new_password = new_password_entry.get()
        confirm_password = confirm_password_entry.get()

        # Verify OTP
        if otp_store.get(phone) != otp:
            messagebox.showerror("Error", "Invalid OTP. Please try again.")
            return

        if not otp or not new_password or not confirm_password:
            messagebox.showerror("Error", "All fields are required.")
            return

        if new_password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        if len(new_password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters long.")
            return
        
        # Verify OTP
        
        if otp_store.get(phone) != otp:
          messagebox.showerror("Error", "Invalid OTP. Please try again.")
          return  # Do not close the window if OTP is invalid

 
        # Update the password
        update_password(email, new_password)
        del otp_store[phone]
        messagebox.showinfo("Success", "Password updated successfully!")
        reset_password.destroy()

    # tk.Button(forgot_password_window, text="Send OTP", bg='#67a1f8', fg='white', command=request_otp).pack(pady=10)
    tk.Button(reset_password_window, text="Reset Password", bg='#67a1f8', fg='white', command=reset_password).pack(pady=20)    
    
def access_webcam(user_identifier):
    def capture_face():
        # Create the directory for saving videos if it doesn't exist
        video_dir = "saved_videos"
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)
        
        # Define the video filename using the user's identifier
        # Generate a unique filename using the current timestamp
        timestamp = int(time.time())
        video_filename = os.path.join(video_dir, f"{user_identifier}_video.avi")
        
        # Set up the video capture and writer
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open webcam.")
            return
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(video_filename, fourcc, 20.0, (640, 480))
        
        while True:
            ret, frame = cap.read()
            frame = cv2.flip(frame,1)
            if not ret:
                break
            
            # Write the frame to the video file
            out.write(frame)
            
            # Display the frame
            # cv2.imshow("Webcam", frame)
            
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

        cap.release()
        out.release()
        cv2.destroyAllWindows()
    capture_face()
def export_to_excel():
    try:
        conn = get_db_connection()
        query = "SELECT name, email,password, phone  FROM users"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        excel_file = 'users_data.xlsx'

        df.to_excel(excel_file, index=False)
        print(f"Data exported to {excel_file}")
    except Exception as e:
        print(f"Failed to export data: {e}")
     
def admin():
    subprocess.run(['python', r"C:\Users\NITIN\Desktop\Programming\finalProject\MyProject\admin_login.py"])
# Initialize the main window
root = tk.Tk()
root.title("Login")
root.geometry("1500x970")

root.config(bg='#fff')
root.resizable(False, False)

# Load and display background image
image_data = r"E:\Tkinter Login Page\images\background1.png"

# Fetch the image from the URL
# url = r"https://i.pinimg.com/564x/dd/39/1d/dd391de89a8d258213834df659278862.jpg"
# response = requests.get(url)
# image_data = BytesIO(response.content)

image = Image.open(image_data)
photo = ImageTk.PhotoImage(image)
tk.Label(root, image=photo, bg='#040405', width=1680, height=750).place(x=5, y=20)

# Create frame for login control
frame = tk.Frame(root, bg='cyan', width=850, height=600)
frame.place(x=400, y=90)

# Heading
tk.Label(frame, text="Welcome", fg="black", bg="cyan", font=('yu gothic ui', 30, "bold"), bd=5, relief=tk.FLAT).place(x=1, y=5, width=370, height=30)

# Left image

image1_data = r"E:\Tkinter Login Page\images\vector.png"

# Fetch the image from the URL
# url = "https://i.pinimg.com/564x/fe/e3/2e/fee32e44319105ce9e453e7e4323865b.jpg"
# response = requests.get(url)
# image1_data = BytesIO(response.content)

image1 = Image.open(image1_data)
photo1 = ImageTk.PhotoImage(image1)
# tk.Label(root, image=photo1, bg='#040405', width=370, height=450).place(x=400, y=180)
tk.Label(root, image=photo1, bg='cyan', width=420, height=500).place(x=400, y=180)


# Sign in label
tk.Label(frame, text="SIGN IN", bg="cyan", fg="black", font=("yu gothic ui", 30, "bold")).place(x=480, y=60)

# Entry widgets for login
email_entry = tk.Entry(frame, width=30, fg="white", border=0, bg="#4f4e4d", font=("yu gothic ui", 13, "bold"))
email_entry.place(x=460, y=200)
email_entry.insert(0, 'Email')
email_entry.bind('<FocusIn>', on_enter_email)
email_entry.bind('<FocusOut>', on_leave_email)

image2_path = r"E:\Tkinter Login Page\images\password_icon.png"
image2 = Image.open(image2_path)
photo2 = ImageTk.PhotoImage(image2)
tk.Label(root, image=photo2, bg='grey12').place(x=858, y=250)

password_entry = tk.Entry(frame, width=27, fg="white", border=0, bg="#4f4e4d", font=('Microsoft YaHei UI Light', 13, "bold"))
password_entry.place(x=460, y=237)
password_entry.insert(0, 'Password')
password_entry.bind('<FocusIn>', on_enter_password)
password_entry.bind('<FocusOut>', on_leave_password)

show_password_var = tk.IntVar()
tk.Checkbutton(frame, text="Show Password", variable=show_password_var, onvalue=1, offvalue=0, fg="white", bg="#4f4e4d", font=('Microsoft YaHei UI Light', 8, "bold"), command=toggle_password).place(x=460, y=270)

tk.Button(frame, width=35, pady=7, text="Login", bg='blue2', fg='white', border=0, command=signin).place(x=460, y=330)
tk.Label(frame, text="Don't have an account?", fg='white', bg="DodgerBlue3", font=('Microsoft YaHei UI Light', 9)).place(x=460, y=380)

tk.Button(frame, width=12, text="Sign Up", border=0, bg="DodgerBlue", cursor='hand2', fg='white', command=open_signup).place(x=610, y=380)
tk.Button(frame, width=12, text="Forgot Password", border=0, bg="DodgerBlue4", cursor='hand2', fg='white', command=open_forgot_password).place(x=560, y=420)

# # Add "Admin Login" button
# tk.Button(frame, width=12, text="Admin Login", border=0, bg="#4f4e4d", cursor='hand2', fg='white', command=admin).place(x=560, y=450)

# # New button to export data to Excel
# tk.Button(root, text="Export Data to Excel", bg='#67a1f8', fg='white', command=export_to_excel).pack(pady=10)


terminal_delete_user()
terminal_delete_all_users()
create_table()
update_table_schema()
countdown_active = False

root.mainloop()

