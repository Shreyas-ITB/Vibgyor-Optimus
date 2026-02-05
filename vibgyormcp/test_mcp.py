import pyodbc
import sys

def test_connection():
    """Test SQL Server connection with different methods"""
    
    print("=" * 60)
    print("SQL Server Connection Test")
    print("=" * 60)
    
    # First, show available ODBC drivers
    print("\n📦 Available ODBC Drivers:")
    drivers = pyodbc.drivers()
    for i, driver in enumerate(drivers, 1):
        print(f"  {i}. {driver}")
    
    if not drivers:
        print("  ⚠️  No ODBC drivers found! Please install ODBC Driver for SQL Server")
        print("  Download from: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
        return
    
    print("\n" + "=" * 60)
    print("Enter your SQL Server connection details:")
    print("=" * 60)
    
    # Get connection details
    server = input("\n🖥️  Server (e.g., localhost\\SQLEXPRESS or 192.168.1.100): ").strip()
    if not server:
        server = "localhost\\SQLEXPRESS"
        print(f"   Using default: {server}")
    
    auth_type = input("🔐 Authentication (1=Windows, 2=SQL): ").strip()
    
    if auth_type == "2":
        username = input("👤 Username: ").strip()
        password = input("🔑 Password: ").strip()
        use_windows_auth = False
    else:
        username = ""
        password = ""
        use_windows_auth = True
        print("   Using Windows Authentication")
    
    # Choose driver
    if len(drivers) > 1:
        print(f"\n🔧 Select ODBC Driver (1-{len(drivers)}): ")
        for i, driver in enumerate(drivers, 1):
            print(f"  {i}. {driver}")
        driver_choice = input("Choice (press Enter for first): ").strip()
        if driver_choice and driver_choice.isdigit():
            driver = drivers[int(driver_choice) - 1]
        else:
            driver = drivers[0]
    else:
        driver = drivers[0]
    
    print(f"   Using driver: {driver}")
    
    # First connect to master to list databases
    print("\n" + "=" * 60)
    print("🔄 Connecting to list available databases...")
    print("=" * 60)
    
    # Build temporary connection string to master
    if use_windows_auth:
        temp_conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE=master;"
            f"Trusted_Connection=yes;"
            f"Encrypt=optional;"
        )
    else:
        temp_conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE=master;"
            f"UID={username};"
            f"PWD={password};"
            f"Encrypt=optional;"
        )
    
    try:
        # Connect to list databases
        temp_conn = pyodbc.connect(temp_conn_str, timeout=10)
        cursor = temp_conn.cursor()
        
        # Get all databases
        cursor.execute("""
            SELECT name, database_id, create_date, state_desc
            FROM sys.databases
            ORDER BY name
        """)
        
        all_databases = cursor.fetchall()
        
        print("\n📚 Available Databases:")
        print("=" * 60)
        for i, db in enumerate(all_databases, 1):
            db_name = db[0]
            db_id = db[1]
            created = db[2]
            state = db[3]
            
            # Mark system databases
            if db_id <= 4:
                print(f"  {i}. {db_name} [{state}] (System Database)")
            else:
                print(f"  {i}. {db_name} [{state}] (Created: {created})")
        
        cursor.close()
        temp_conn.close()
        
        print("=" * 60)
        
        # Let user select database
        db_choice = input(f"\n💾 Select database number (1-{len(all_databases)}) or press Enter for 'master': ").strip()
        
        if db_choice and db_choice.isdigit():
            db_index = int(db_choice) - 1
            if 0 <= db_index < len(all_databases):
                database = all_databases[db_index][0]
                print(f"   Selected: {database}")
            else:
                database = "master"
                print(f"   Invalid selection. Using default: {database}")
        else:
            database = "master"
            print(f"   Using default: {database}")
            
    except Exception as e:
        print(f"\n⚠️  Could not list databases: {e}")
        print("   Proceeding with manual database entry...")
        database = input("💾 Database (default: master): ").strip()
        if not database:
            database = "master"
    
    # Build connection string
    if use_windows_auth:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"Encrypt=optional;"
        )
    else:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"Encrypt=optional;"
        )
    
    print("\n" + "=" * 60)
    print("🔄 Attempting connection...")
    print("=" * 60)
    
    try:
        # Attempt connection
        conn = pyodbc.connect(conn_str, timeout=10)
        
        print("\n✅ CONNECTION SUCCESSFUL! 🎉\n")
        
        # Get SQL Server info
        cursor = conn.cursor()
        
        # Server version
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"📊 SQL Server Version:")
        print(f"   {version.split(chr(10))[0]}\n")
        
        # Current database
        cursor.execute("SELECT DB_NAME()")
        current_db = cursor.fetchone()[0]
        print(f"💾 Current Database: {current_db}\n")
        
        # List all databases
        cursor.execute("""
            SELECT name, database_id, create_date 
            FROM sys.databases 
            WHERE database_id > 4
            ORDER BY name
        """)
        
        print("📚 Available Databases:")
        user_databases = cursor.fetchall()
        if user_databases:
            for db in user_databases:
                print(f"   - {db[0]} (ID: {db[1]}, Created: {db[2]})")
        else:
            print("   No user databases found")
        
        # Count tables in current database
        cursor.execute("SELECT COUNT(*) FROM sys.tables")
        table_count = cursor.fetchone()[0]
        print(f"\n📋 Tables in '{current_db}': {table_count}")
        
        # Count views
        cursor.execute("SELECT COUNT(*) FROM sys.views")
        view_count = cursor.fetchone()[0]
        print(f"👁️  Views in '{current_db}': {view_count}")
        
        # Count stored procedures
        cursor.execute("SELECT COUNT(*) FROM sys.procedures")
        proc_count = cursor.fetchone()[0]
        print(f"⚙️  Stored Procedures in '{current_db}': {proc_count}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Connection test completed successfully!")
        print("=" * 60)
        print("\n💡 Use these connection details in your MCP:")
        print(f"   Server: {server}")
        print(f"   Database: {database}")
        print(f"   Authentication: {'Windows' if use_windows_auth else 'SQL Server'}")
        print(f"   Driver: {driver}")
        
        return True
        
    except pyodbc.Error as e:
        print("\n❌ CONNECTION FAILED!\n")
        print(f"Error: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Verify SQL Server is running on the target machine")
        print("   2. Check server name/IP address is correct")
        print("   3. Ensure TCP/IP protocol is enabled in SQL Server Configuration Manager")
        print("   4. Verify firewall allows connections on port 1433 (or your SQL Server port)")
        print("   5. For remote connections, ensure SQL Server Browser service is running")
        print("   6. Check username and password are correct (for SQL auth)")
        print("   7. Verify the database exists and you have access to it")
        print("\n   Try connecting with SSMS first to isolate the issue.")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("\n🚀 SQL Server Connection Tester\n")
    test_connection()
    print("\n")