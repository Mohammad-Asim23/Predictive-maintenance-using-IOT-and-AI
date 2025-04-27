import sqlite3
import os
import json
from datetime import datetime

class Database:
    def __init__(self, db_path=None):
        """Initialize database connection"""
        if db_path is None:
            # Create database in the project directory
            self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'water_plant_data.db')
        else:
            self.db_path = db_path
        
        self.conn = None
        self.cursor = None
        self.initialize_db()
    
    def connect(self):
        """Connect to the SQLite database."""
        try:
            # Always create a new connection in the current thread
            self.conn = sqlite3.connect(self.db_path)
            # Enable dictionary access to rows
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return False
    
    def close(self):
        """Close the database connection."""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except Exception as e:
                print(f"Error closing database connection: {e}")
            self.conn = None
            self.cursor = None
    
    def initialize_db(self):
        """Create database tables if they don't exist"""
        self.connect()
        
        # Create sensor data table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            sensor_type TEXT NOT NULL,
            sensor_name TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT
        )
        ''')
        
        # Create separate tables for air temperature and humidity
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS air_temperature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS air_humidity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT
        )
        ''')
        
        # Create predictions table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            failure_probability REAL NOT NULL,
            failure_predicted INTEGER NOT NULL
        )
        ''')
        
        self.conn.commit()
        self.close()
    
    def store_sensor_data(self, data):
        """Store sensor data in the database."""
        try:
            # Determine which table to use based on sensor type and name
            if data['sensor_type'] == 'DHT11' and data['sensor_name'] == 'temperature':
                self.cursor.execute(
                    'INSERT INTO air_temperature (timestamp, asset_id, value) VALUES (?, ?, ?)',
                    (data['timestamp'], data['asset_id'], data['value'])
                )
            elif data['sensor_type'] == 'DHT11' and data['sensor_name'] == 'humidity':
                self.cursor.execute(
                    'INSERT INTO air_humidity (timestamp, asset_id, value) VALUES (?, ?, ?)',
                    (data['timestamp'], data['asset_id'], data['value'])
                )
            else:
                # For other sensors, use the general sensor_data table
                self.cursor.execute(
                    'INSERT INTO sensor_data (timestamp, asset_id, sensor_type, sensor_name, value, unit) VALUES (?, ?, ?, ?, ?, ?)',
                    (data['timestamp'], data['asset_id'], data['sensor_type'], data['sensor_name'], data['value'], data['unit'])
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error storing sensor data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def store_prediction(self, data):
        """Store prediction data in the database"""
        try:
            self.cursor.execute(
                'INSERT INTO predictions (timestamp, asset_id, failure_probability, failure_predicted) VALUES (?, ?, ?, ?)',
                (data['timestamp'], data['asset_id'], data['failure_probability'], data['failure_predicted'])
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error storing prediction: {e}")
            return False
    
    def get_recent_sensor_data(self, asset_id=None, limit=100):
        """Get recent sensor data from the database"""
        self.connect()
        
        try:
            if asset_id:
                self.cursor.execute(
                    'SELECT * FROM sensor_data WHERE asset_id = ? ORDER BY timestamp DESC LIMIT ?',
                    (asset_id, limit)
                )
            else:
                self.cursor.execute(
                    'SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                )
            
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.close()
    
    def get_prediction_history(self, asset_id=None, limit=100):
        """Get prediction history from the database"""
        self.connect()
        
        try:
            if asset_id:
                self.cursor.execute(
                    'SELECT * FROM predictions WHERE asset_id = ? ORDER BY timestamp DESC LIMIT ?',
                    (asset_id, limit)
                )
            else:
                self.cursor.execute(
                    'SELECT * FROM predictions ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                )
            
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.close()
    
    def get_sensor_data_by_asset(self, asset_id, limit=50):
        """Get sensor data for a specific asset"""
        self.connect()
        try:
            self.cursor.execute('''
                SELECT * FROM sensor_data 
                WHERE asset_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (asset_id, limit))
            data = [dict(row) for row in self.cursor.fetchall()]
            return data
        finally:
            self.close()
    
    def get_predictions_by_asset(self, asset_id, limit=50):
        """Get prediction history for a specific asset"""
        self.connect()
        try:
            self.cursor.execute('''
                SELECT * FROM predictions 
                WHERE asset_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (asset_id, limit))
            data = [dict(row) for row in self.cursor.fetchall()]
            return data
        finally:
            self.close()
    
    def get_failure_count(self):
        """Get count of failures by asset"""
        try:
            self.connect()
            self.cursor.execute('''
                SELECT asset_id, COUNT(*) as count
                FROM predictions
                WHERE failure_predicted = 1
                GROUP BY asset_id
            ''')
            data = [dict(row) for row in self.cursor.fetchall()]
            return data
        except Exception as e:
            print(f"Error getting failure count: {e}")
            return []
        finally:
            self.close()
    
    def get_tables(self):
        """Get list of tables in the database"""
        self.connect()
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in self.cursor.fetchall()]
            return tables
        except Exception as e:
            print(f"Error getting tables: {e}")
            return []
        finally:
            self.close()