import time
import urllib.request
def check_bandwidth(url="http://ipv4.download.thinkbroadband.com/5MB.zip", file_size_bytes=5 * 1024 * 1024):
    
        """  
        Measures the download speed (Mbps) by downloading a test file.

        Args:
            url (str): URL of the file to download for speed test.
            file_size_bytes (int): Size of the test file in bytes.

        Returns:
            float: Download speed in Mbps. Returns 0.0 if an error occurs.
        """
        start_time = time.time()
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                _ = response.read()
            end_time = time.time()
            duration = end_time - start_time
            if duration == 0:
                raise ValueError("Duration is zero, cannot calculate speed.")
            speed_mbps = (file_size_bytes * 8) / (duration * 1_000_000)
            return speed_mbps
        except Exception as e:
            print(f"Error while checking bandwidth: {e}")
            return 0.0

    def run_agent():
        # Your agent code here
        print("✅ Running agent online...")

    def routine(threshold_mbps=2.0):
        """
        Runs agent only if bandwidth is above threshold.
        If bandwidth is below threshold, agent will NOT run.
        """
        speed = check_bandwidth()
        print(f"Current bandwidth: {speed:.2f} Mbps")
        
        if speed >= threshold_mbps:
            run_agent()
        elif speed > 0:
            print("⚠️ Bandwidth too low. Agent not started.")
        else:
            print("❌ No internet connection. Agent not started.")

if __name__ == "__main__":
    routine()