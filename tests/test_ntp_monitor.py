import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ntp_monitor import NTPMonitor

class TestNTPMonitor(unittest.TestCase):
    
    def setUp(self):
        self.monitor = NTPMonitor("pool.ntp.org", max_points=10)
    
    @patch('ntplib.NTPClient.request')
    def test_query_server_success(self, mock_request):
        # Mock successful NTP response
        mock_response = MagicMock()
        mock_response.offset = 0.001  # 1ms offset
        mock_response.delay = 0.050   # 50ms delay
        mock_request.return_value = mock_response
        
        result = self.monitor.query_server()
        self.assertTrue(result)
        self.assertEqual(len(self.monitor.offsets), 1)
        self.assertEqual(self.monitor.offsets[0], 1.0)  # 1ms in milliseconds
    
    @patch('ntplib.NTPClient.request')
    def test_query_server_failure(self, mock_request):
        # Mock NTP request failure
        mock_request.side_effect = Exception("Network error")
        
        result = self.monitor.query_server()
        self.assertFalse(result)
        self.assertEqual(len(self.monitor.offsets), 0)
    
    def test_calculate_statistics_insufficient_data(self):
        # Test with no data
        stats = self.monitor.calculate_statistics()
        self.assertIsNone(stats)
        
        # Test with insufficient data (only 1 point)
        self.monitor.offsets.append(1.0)
        self.monitor.delays.append(50.0)
        stats = self.monitor.calculate_statistics()
        self.assertIsNone(stats)
    
    def test_calculate_statistics_with_data(self):
        # Add test data
        test_offsets = [1.0, 2.0, 1.5, 3.0, 2.5]
        test_delays = [50.0, 55.0, 52.0, 60.0, 58.0]
        
        for offset, delay in zip(test_offsets, test_delays):
            self.monitor.offsets.append(offset)
            self.monitor.delays.append(delay)
        
        stats = self.monitor.calculate_statistics()
        
        self.assertIsNotNone(stats)
        self.assertIn('offset', stats)
        self.assertIn('delay', stats)
        self.assertAlmostEqual(stats['offset']['mean'], 2.0, places=1)
        self.assertAlmostEqual(stats['delay']['mean'], 55.0, places=1)

if __name__ == '__main__':
    unittest.main()
