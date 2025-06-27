import ntplib
import time
import matplotlib.pyplot as plt
from datetime import datetime
import csv
from collections import deque
import os
import numpy as np
from scipy import stats
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import logging
from typing import Optional, Dict, Any

class NTPMonitor:
    def __init__(self, server, max_points=1000, influx_config=None):
        self.server = server
        self.client = ntplib.NTPClient()
        self.timestamps = deque(maxlen=max_points)
        self.offsets = deque(maxlen=max_points)
        self.delays = deque(maxlen=max_points)
        self.csv_file = 'ntp_metrics.csv'
        
        # InfluxDB configuration
        self.influx_client = None
        self.write_api = None
        self.influx_config = influx_config
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize InfluxDB connection if config provided
        if influx_config:
            self._setup_influxdb()
        
        # Initialize CSV file
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'offset', 'delay'])

    def _setup_influxdb(self):
        """Initialize InfluxDB connection"""
        try:
            self.influx_client = InfluxDBClient(
                url=self.influx_config['url'],
                token=self.influx_config['token'],
                org=self.influx_config['org']
            )
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            self.logger.info("InfluxDB connection established")
            
            # Test connection
            health = self.influx_client.health()
            if health.status == "pass":
                self.logger.info("InfluxDB health check passed")
            else:
                self.logger.warning("InfluxDB health check failed")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to InfluxDB: {e}")
            self.influx_client = None
            self.write_api = None

    def _write_to_influxdb(self, timestamp: datetime, offset: float, delay: float, stats: Optional[Dict] = None):
        """Write metrics to InfluxDB"""
        if not self.write_api:
            return False
            
        try:
            # Basic metrics point
            point = Point("ntp_metrics") \
                .tag("server", self.server) \
                .field("offset_ms", offset) \
                .field("delay_ms", delay) \
                .time(timestamp, WritePrecision.MS)
            
            points = [point]
            
            # Add statistical metrics if available
            if stats:
                for metric_type in ['offset', 'delay']:
                    stats_point = Point(f"ntp_{metric_type}_stats") \
                        .tag("server", self.server) \
                        .field("mean", stats[metric_type]['mean']) \
                        .field("median", stats[metric_type]['median']) \
                        .field("std", stats[metric_type]['std']) \
                        .field("min", stats[metric_type]['min']) \
                        .field("max", stats[metric_type]['max']) \
                        .field("percentile_95", stats[metric_type]['95th_percentile']) \
                        .field("skewness", stats[metric_type]['skewness']) \
                        .field("kurtosis", stats[metric_type]['kurtosis']) \
                        .field("stability", stats[metric_type]['stability']) \
                        .time(timestamp, WritePrecision.MS)
                    points.append(stats_point)
            
            # Write all points
            self.write_api.write(
                bucket=self.influx_config['bucket'],
                record=points
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write to InfluxDB: {e}")
            return False

    def query_server(self):
        try:
            response = self.client.request(self.server)
            timestamp = datetime.now()
            offset_ms = response.offset * 1000
            delay_ms = response.delay * 1000
            
            # Store in memory
            self.timestamps.append(timestamp)
            self.offsets.append(offset_ms)
            self.delays.append(delay_ms)
            
            # Write to CSV
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, offset_ms, delay_ms])
            
            # Calculate statistics if we have enough data
            stats = None
            if len(self.offsets) >= 2:
                stats = self.calculate_statistics()
            
            # Write to InfluxDB
            if self.influx_client:
                success = self._write_to_influxdb(timestamp, offset_ms, delay_ms, stats)
                if success:
                    self.logger.debug("Successfully wrote metrics to InfluxDB")
                else:
                    self.logger.warning("Failed to write metrics to InfluxDB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error querying NTP server: {e}")
            return False

    def calculate_statistics(self):
        if len(self.offsets) < 2:
            return None

        offset_array = np.array(list(self.offsets))
        delay_array = np.array(list(self.delays))

        stats_dict = {
            'offset': {
                'mean': np.mean(offset_array),
                'median': np.median(offset_array),
                'std': np.std(offset_array),
                'min': np.min(offset_array),
                'max': np.max(offset_array),
                '95th_percentile': np.percentile(offset_array, 95),
                'skewness': stats.skew(offset_array),
                'kurtosis': stats.kurtosis(offset_array)
            },
            'delay': {
                'mean': np.mean(delay_array),
                'median': np.median(delay_array),
                'std': np.std(delay_array),
                'min': np.min(delay_array),
                'max': np.max(delay_array),
                '95th_percentile': np.percentile(delay_array, 95),
                'skewness': stats.skew(delay_array),
                'kurtosis': stats.kurtosis(delay_array)
            }
        }

        stats_dict['offset']['stability'] = np.std(np.diff(offset_array))
        stats_dict['delay']['stability'] = np.std(np.diff(delay_array))

        return stats_dict

    def plot_metrics(self):
        if len(self.timestamps) < 2:
            print("Collecting data... Please wait for more data points.")
            return

        plt.figure(figsize=(15, 12))
        stats_dict = self.calculate_statistics()
        
        timestamps_list = list(self.timestamps)
        offsets_list = list(self.offsets)
        delays_list = list(self.delays)
        
        # Plot offset
        plt.subplot(3, 1, 1)
        plt.plot(timestamps_list, offsets_list, 'b-', label='Offset')
        plt.axhline(y=stats_dict['offset']['mean'], color='r', linestyle='--', label='Mean')
        plt.axhline(y=stats_dict['offset']['mean'] + stats_dict['offset']['std'], 
                   color='r', linestyle=':', label='+1 STD')
        plt.axhline(y=stats_dict['offset']['mean'] - stats_dict['offset']['std'], 
                   color='r', linestyle=':', label='-1 STD')
        
        plt.title('NTP Server Performance Metrics')
        plt.ylabel('Offset (ms)')
        plt.grid(True)
        plt.legend()
        
        # Plot delay
        plt.subplot(3, 1, 2)
        plt.plot(timestamps_list, delays_list, 'g-', label='Delay')
        plt.axhline(y=stats_dict['delay']['mean'], color='r', linestyle='--', label='Mean')
        plt.axhline(y=stats_dict['delay']['mean'] + stats_dict['delay']['std'], 
                   color='r', linestyle=':', label='+1 STD')
        plt.axhline(y=stats_dict['delay']['mean'] - stats_dict['delay']['std'], 
                   color='r', linestyle=':', label='-1 STD')
        
        plt.ylabel('Delay (ms)')
        plt.grid(True)
        plt.legend()

        # Plot histograms if we have enough data
        if len(self.offsets) >= 5:
            plt.subplot(3, 2, 5)
            plt.hist(offsets_list, bins=min(30, len(offsets_list)), alpha=0.7, color='b')
            plt.axvline(x=stats_dict['offset']['mean'], color='r', linestyle='--', label='Mean')
            plt.title('Offset Distribution')
            plt.xlabel('Offset (ms)')
            plt.ylabel('Frequency')
            plt.grid(True)
            plt.legend()

            plt.subplot(3, 2, 6)
            plt.hist(delays_list, bins=min(30, len(delays_list)), alpha=0.7, color='g')
            plt.axvline(x=stats_dict['delay']['mean'], color='r', linestyle='--', label='Mean')
            plt.title('Delay Distribution')
            plt.xlabel('Delay (ms)')
            plt.ylabel('Frequency')
            plt.grid(True)
            plt.legend()
        
        plt.tight_layout()
        plt.savefig('ntp_metrics.png')
        plt.close()

    def print_statistics(self):
        if len(self.offsets) < 2:
            print("Collecting data... Please wait for more data points.")
            return

        stats_dict = self.calculate_statistics()
        print("\n=== NTP Server Statistics ===")
        for metric in ['offset', 'delay']:
            print(f"\n{metric.upper()} STATISTICS:")
            print(f"Mean: {stats_dict[metric]['mean']:.3f} ms")
            print(f"Median: {stats_dict[metric]['median']:.3f} ms")
            print(f"Standard Deviation: {stats_dict[metric]['std']:.3f} ms")
            print(f"Min: {stats_dict[metric]['min']:.3f} ms")
            print(f"Max: {stats_dict[metric]['max']:.3f} ms")
            print(f"95th Percentile: {stats_dict[metric]['95th_percentile']:.3f} ms")
            print(f"Skewness: {stats_dict[metric]['skewness']:.3f}")
            print(f"Kurtosis: {stats_dict[metric]['kurtosis']:.3f}")
            print(f"Stability (STD of differences): {stats_dict[metric]['stability']:.3f} ms")

    def close(self):
        """Clean up resources"""
        if self.influx_client:
            self.influx_client.close()

def main():
    # NTP server configuration
    ntp_server = "10.20.40.123"
    
    # InfluxDB configuration - update these values for your setup
    influx_config = {
        'url': 'http://10.20.20.1:8086',  # Your InfluxDB URL
        'token': 'dys5mS_yoeWQy3NJ0CthdDLhHJ1DQUJxd7sUFiIzl0PDG4_6Sur5uqFjiWXZUnTaA0EZFpfTKRepvntt7M7ArQ==',    # Your InfluxDB token
        'org': 'schillingway',               # Your InfluxDB organization
        'bucket': 'ntp-monitoring'       # Your InfluxDB bucket
    }
    
    # Set to None to disable InfluxDB integration
    # influx_config = None
    
    monitor = NTPMonitor(ntp_server, influx_config=influx_config)
    
    print(f"Starting NTP monitoring for {ntp_server}")
    if influx_config:
        print(f"InfluxDB integration enabled - sending data to {influx_config['url']}")
    print("Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            if monitor.query_server():
                monitor.plot_metrics()
                monitor.print_statistics()
                print(f"\nUpdated metrics at {datetime.now()}")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
    finally:
        monitor.close()

if __name__ == "__main__":
    main()
