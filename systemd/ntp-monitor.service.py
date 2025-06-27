#!/usr/bin/env python3
import ntplib
import time
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
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
import sys
import signal
from typing import Optional, Dict, Any

# Import configuration
try:
    from config import *
except ImportError:
    print("Error: config.py not found. Please create configuration file.")
    sys.exit(1)

class NTPMonitorService:
    def __init__(self):
        self.server = NTP_SERVER
        self.client = ntplib.NTPClient()
        self.timestamps = deque(maxlen=MAX_POINTS)
        self.offsets = deque(maxlen=MAX_POINTS)
        self.delays = deque(maxlen=MAX_POINTS)
        self.csv_file = CSV_FILE
        self.plot_file = PLOT_FILE
        self.running = True
        
        # Setup logging
        self._setup_logging()
        
        # InfluxDB configuration
        self.influx_client = None
        self.write_api = None
        self.influx_config = INFLUX_CONFIG
        
        # Initialize InfluxDB connection
        if self.influx_config and self.influx_config.get('token'):
            self._setup_influxdb()
        else:
            self.logger.warning("InfluxDB configuration not found, running in CSV-only mode")
        
        # Initialize CSV file
        self._initialize_csv()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _setup_logging(self):
        """Configure logging for the service"""
        # Create logger
        self.logger = logging.getLogger('ntp-monitor')
        self.logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler for systemd journal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

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

    def _initialize_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            try:
                with open(self.csv_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'offset', 'delay'])
                self.logger.info(f"Created new CSV file: {self.csv_file}")
            except Exception as e:
                self.logger.error(f"Failed to create CSV file: {e}")

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
        """Query NTP server and collect metrics"""
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
            try:
                with open(self.csv_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, offset_ms, delay_ms])
            except Exception as e:
                self.logger.error(f"Failed to write to CSV: {e}")
            
            # Calculate statistics if we have enough data
            stats = None
            if len(self.offsets) >= 2:
                stats = self.calculate_statistics()
            
            # Write to InfluxDB
            if self.influx_client:
                success = self._write_to_influxdb(timestamp, offset_ms, delay_ms, stats)
                if not success:
                    self.logger.warning("Failed to write metrics to InfluxDB")
            
            self.logger.info(f"NTP query successful - Offset: {offset_ms:.3f}ms, Delay: {delay_ms:.3f}ms")
            return True
            
        except Exception as e:
            self.logger.error(f"Error querying NTP server {self.server}: {e}")
            return False

    def calculate_statistics(self):
        """Calculate statistics for collected metrics"""
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

    def generate_plot(self):
        """Generate metrics plot (less frequently than data collection)"""
        if len(self.timestamps) < 2:
            return

        try:
            plt.figure(figsize=(15, 8))
            
            timestamps_list = list(self.timestamps)
            offsets_list = list(self.offsets)
            delays_list = list(self.delays)
            
            # Plot offset
            plt.subplot(2, 1, 1)
            plt.plot(timestamps_list, offsets_list, 'b-', label='Offset')
            plt.title('NTP Server Performance Metrics')
            plt.ylabel('Offset (ms)')
            plt.grid(True)
            plt.legend()
            
            # Plot delay
            plt.subplot(2, 1, 2)
            plt.plot(timestamps_list, delays_list, 'g-', label='Delay')
            plt.ylabel('Delay (ms)')
            plt.xlabel('Time')
            plt.grid(True)
            plt.legend()
            
            plt.tight_layout()
            plt.savefig(self.plot_file)
            plt.close()
            
        except Exception as e:
            self.logger.error(f"Failed to generate plot: {e}")

    def run(self):
        """Main service loop"""
        self.logger.info(f"Starting NTP monitoring service for {self.server}")
        
        plot_counter = 0
        plot_interval = 10  # Generate plot every 10 measurements
        
        while self.running:
            try:
                if self.query_server():
                    plot_counter += 1
                    
                    # Generate plot periodically
                    if plot_counter >= plot_interval:
                        self.generate_plot()
                        plot_counter = 0
                        
                time.sleep(POLLING_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(POLLING_INTERVAL)
                
        self.logger.info("NTP monitoring service stopped")

    def close(self):
        """Clean up resources"""
        if self.influx_client:
            self.influx_client.close()

def main():
    monitor = NTPMonitorService()
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.logger.info("Service interrupted by user")
    finally:
        monitor.close()

if __name__ == "__main__":
    main()
