import requests

class SensorDataFetcher:
    def __init__(self, base_url):
        """Initialize the class with base URL and create a session"""
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        })
    
    def get_sensor_objects(self, measurement_id):
        """Fetch sensor objects for a given measurement ID"""
        url = f"{self.base_url}/m/sensor-objects-in-measurement-object/{measurement_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            json_array = response.json()
            return json_array
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except ValueError as e:
            print(f"JSON parsing failed: {e}")
            return None
    
    def process_data(self, data):
        """Process the fetched data"""
        if data is None:
            print("No data to process")
            return
        
        print(f"Fetched {len(data)} items")
        for item in data:
            print(item)
    
    def close(self):
        """Close the session"""
        self.session.close()


def main():
    # Initialize the fetcher
    base_url = "http://mysql-server-tailscale.tailb51a53.ts.net:5000"
    fetcher = SensorDataFetcher(base_url)
    
    # Fetch data
    measurement_id = 1
    data = fetcher.get_sensor_objects(measurement_id)
    
    # Process data
    fetcher.process_data(data)
    
    # Clean up
    fetcher.close()


if __name__ == "__main__":
    main()