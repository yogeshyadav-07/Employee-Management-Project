import mysql.connector

db_config = {
    'host': "localhost",
    'port': 3300,
    'user': "root",
    'password': "password",
    'database': "staff_system"
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

print("Updating Database...")

# 1. Employees table mein Photo ka column add karein
try:
    cursor.execute("ALTER TABLE employees ADD COLUMN profile_pic VARCHAR(255) DEFAULT NULL")
    print("✅ Added 'profile_pic' column.")
except Exception as e:
    print(f"ℹ️  Profile Pic column skip: {e}")

# 2. Attendance Table banayein
try:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        employee_id INT,
        date DATE,
        status VARCHAR(20),
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )
    """)
    print("✅ Created 'attendance' table.")
except Exception as e:
    print(f"❌ Error creating attendance table: {e}")

conn.commit()
conn.close()
print("Database Updated Successfully!")