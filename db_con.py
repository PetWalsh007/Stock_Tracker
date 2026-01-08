# main file to open connections, execute queries, and close connections

# This is taken from my FYP 2025 code and will be adapted for this project as needed


import pyodbc

# class for the connections to postgresql

class connectcls_postgres:

    def __init__(self, driver_name, server_name, db_name, connection_username, connection_password, port=5432):
        self.driver_name = driver_name
        self.server_name = server_name
        self.db_name = db_name
        self.connection_username = connection_username
        self.connection_password = connection_password
        self.port = port


        self.conn, self.cursor, self.con_err = self.make_connection()

    def __str__(self):
        return f'Driver Name: {self.driver_name}, Server Name: {self.server_name}, Database Name: {self.db_name}, Port: {self.port}, Connection Username: {self.connection_username}, Connection Password: {self.connection_password}'

    def connect_str(self):
        # connection string 
        return  f"DRIVER={{{self.driver_name}}};SERVER={self.server_name};DATABASE={self.db_name};PORT={self.port};UID={self.connection_username};PWD={self.connection_password};"
    
    def make_connection(self):
        
        try:
            conn = pyodbc.connect(self.connect_str())
            print("Connection to PostgreSQL is successful")
            cursor = conn.cursor()
            return conn, cursor, None
        except pyodbc.OperationalError as e:
            return None, None, [{"error": "Operational error - Check database connection and server status"}]
        except pyodbc.IntegrityError as e:
            return None, None, [{"error": "Integrity error - Check data integrity constraints"}]
        except pyodbc.ProgrammingError as e:
            return None, None, [{"error": "Programming error - Check SQL syntax and table/column names"}]
        except pyodbc.DatabaseError as e:
            return None, None, [{"error": "Database error - General database error occurred"}]
        except pyodbc.Error as e:
            return None, None, [{"error": f"General error - {str(e)}"}]


    def query(self, query):
        try: 
            
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return [dict(zip([column[0] for column in self.cursor.description], row)) for row in rows]
        except pyodbc.ProgrammingError as e:
            print(f"Query failed: {e}")
            return [{"error": "Query failure - Check SQL syntax"}]
        except pyodbc.DatabaseError as e:
            print(f"Database failure: {e}")
            return [{"error": "Database failure - Check database connection and query"}]
        except pyodbc.Error as e:
            print(f"Query failed: {e}")
            return [{"error": f"General error - {str(e)}"}]


    
    def close_connection(self):
        self.conn.close()
        print("Connection closed")