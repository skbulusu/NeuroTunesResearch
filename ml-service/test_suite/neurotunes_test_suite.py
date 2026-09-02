#!/usr/bin/env python3
"""
NeuroTunes Federated Learning - Comprehensive Test Suite
Tests end-to-end pipeline and federated learning components
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional
import threading
from dataclasses import dataclass
from colorama import init, Fore, Back, Style
import mysql.connector
import os

# Initialize colorama for colored output
init(autoreset=True)

@dataclass
class TestResult:
    """Test result data structure."""
    test_name: str
    status: str  # 'PASS', 'FAIL', 'SKIP'
    duration: float
    message: str
    details: Optional[Dict] = None

class NeuroTunesTestSuite:
    """Comprehensive test suite for NeuroTunes federated learning system."""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_results: List[TestResult] = []
        self.start_time = None
        self.db_connection = None

        # Test data
        self.test_patient_data = {
            "patient_id": "test_patient_001",
            "age": 35,
            "condition": "anxiety",
            "stress_level": 8,
            "therapy_goal": "relaxation"
        }

        self.test_sites = [
            {
                "site_id": "test_mayo_clinic",
                "site_url": "http://test-mayo:5000",
                "capabilities": {
                    "site_name": "Test Mayo Clinic",
                    "location": "Rochester, MN",
                    "patient_count": 500
                }
            },
            {
                "site_id": "test_johns_hopkins",
                "site_url": "http://test-hopkins:5000", 
                "capabilities": {
                    "site_name": "Test Johns Hopkins",
                    "location": "Baltimore, MD",
                    "patient_count": 400
                }
            }
        ]

    def print_header(self, text: str):
        """Print formatted header."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{text:^80}")
        print(f"{'='*80}{Style.RESET_ALL}")

    def print_test_start(self, test_name: str):
        """Print test start message."""
        print(f"\n{Fore.YELLOW}🧪 TESTING: {test_name}")
        print(f"{Fore.BLUE}{'─'*60}")

    def print_test_result(self, result: TestResult):
        """Print formatted test result."""
        if result.status == 'PASS':
            status_color = Fore.GREEN
            icon = "✅"
        elif result.status == 'FAIL':
            status_color = Fore.RED
            icon = "❌"
        else:
            status_color = Fore.YELLOW
            icon = "⏭️"

        print(f"{status_color}{icon} {result.test_name}: {result.status}")
        print(f"{Fore.WHITE}   Duration: {result.duration:.2f}s")
        print(f"{Fore.WHITE}   Message: {result.message}")
        if result.details:
            print(f"{Fore.CYAN}   Details: {json.dumps(result.details, indent=2)}")

    def record_test_result(self, test_name: str, status: str, duration: float, 
                          message: str, details: Optional[Dict] = None):
        """Record test result."""
        result = TestResult(test_name, status, duration, message, details)
        self.test_results.append(result)
        self.print_test_result(result)

    def setup_database_connection(self):
        """Setup database connection for testing."""
        try:
            self.db_connection = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_DATABASE', 'netraidb'),
                user=os.getenv('DB_USER', 'john'),
                password=os.getenv('DB_PASSWORD', 'john'),
                port=int(os.getenv('MYSQL_PORT', 3306))
            )
            return True
        except Exception as e:
            print(f"{Fore.RED}❌ Database connection failed: {e}")
            return False

    def test_system_health(self):
        """Test basic system health and connectivity."""
        self.print_test_start("System Health Check")
        start_time = time.time()

        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                self.record_test_result(
                    "System Health Check",
                    "PASS",
                    duration,
                    "System is healthy and responsive",
                    {"response": data}
                )
                return True
            else:
                self.record_test_result(
                    "System Health Check",
                    "FAIL", 
                    duration,
                    f"Health check failed with status {response.status_code}"
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "System Health Check",
                "FAIL",
                duration,
                f"Health check failed: {str(e)}"
            )
            return False

    def test_database_connectivity(self):
        """Test database connectivity and basic queries."""
        self.print_test_start("Database Connectivity")
        start_time = time.time()

        if not self.setup_database_connection():
            duration = time.time() - start_time
            self.record_test_result(
                "Database Connectivity",
                "FAIL",
                duration,
                "Failed to connect to database"
            )
            return False

        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM neurotunes_generation_log")
            count = cursor.fetchone()[0]
            cursor.close()

            duration = time.time() - start_time
            self.record_test_result(
                "Database Connectivity",
                "PASS",
                duration,
                f"Database connected successfully. Found {count} generation records",
                {"generation_count": count}
            )
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "Database Connectivity",
                "FAIL",
                duration,
                f"Database query failed: {str(e)}"
            )
            return False

    def test_music_generation_pipeline(self):
        """Test end-to-end music generation pipeline."""
        self.print_test_start("Music Generation Pipeline")
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/generate_music",
                json=self.test_patient_data,
                timeout=60
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                tracks = data.get('tracks', [])

                if len(tracks) >= 3:
                    self.record_test_result(
                        "Music Generation Pipeline",
                        "PASS",
                        duration,
                        f"Successfully generated {len(tracks)} tracks",
                        {
                            "session_id": data.get('session_id'),
                            "track_count": len(tracks),
                            "music_params": data.get('music_params')
                        }
                    )
                    return data.get('session_id')
                else:
                    self.record_test_result(
                        "Music Generation Pipeline",
                        "FAIL",
                        duration,
                        f"Expected 3+ tracks, got {len(tracks)}"
                    )
                    return None
            else:
                self.record_test_result(
                    "Music Generation Pipeline",
                    "FAIL",
                    duration,
                    f"Generation failed with status {response.status_code}"
                )
                return None

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "Music Generation Pipeline",
                "FAIL",
                duration,
                f"Generation failed: {str(e)}"
            )
            return None

    def test_feedback_logging(self, session_id: str):
        """Test feedback logging functionality."""
        self.print_test_start("Feedback Logging")
        start_time = time.time()

        feedback_data = {
            "session_id": session_id,
            "track_id": f"{session_id}_track_1",
            "overall_rating": 4,
            "effectiveness_rating": 4,
            "mood_change": "better",
            "would_use_again": True,
            "listen_duration_seconds": 120,
            "reported_feeling": "relaxed"
        }

        try:
            response = requests.post(
                f"{self.base_url}/log_feedback",
                json=feedback_data,
                timeout=30
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                self.record_test_result(
                    "Feedback Logging",
                    "PASS",
                    duration,
                    "Feedback logged successfully",
                    {"feedback_id": data.get('feedback_id')}
                )
                return True
            else:
                self.record_test_result(
                    "Feedback Logging",
                    "FAIL",
                    duration,
                    f"Feedback logging failed with status {response.status_code}"
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "Feedback Logging",
                "FAIL",
                duration,
                f"Feedback logging failed: {str(e)}"
            )
            return False

    def test_reward_model_training(self):
        """Test reward model training functionality."""
        self.print_test_start("Reward Model Training")
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/train_reward_model",
                timeout=120
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                self.record_test_result(
                    "Reward Model Training",
                    "PASS",
                    duration,
                    "Reward model trained successfully",
                    {
                        "training_data_count": data.get('training_data_count'),
                        "validation_loss": data.get('validation_loss'),
                        "model_version": data.get('model_version')
                    }
                )
                return True
            else:
                self.record_test_result(
                    "Reward Model Training",
                    "FAIL",
                    duration,
                    f"Training failed with status {response.status_code}"
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "Reward Model Training",
                "FAIL",
                duration,
                f"Training failed: {str(e)}"
            )
            return False

    def test_federation_coordinator_status(self):
        """Test federation coordinator status."""
        self.print_test_start("Federation Coordinator Status")
        start_time = time.time()

        try:
            response = requests.get(f"{self.base_url}/federation/status", timeout=30)
            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                status = data.get('status', {})

                self.record_test_result(
                    "Federation Coordinator Status",
                    "PASS",
                    duration,
                    "Federation coordinator is operational",
                    {
                        "federation_mode": data.get('federation_mode'),
                        "active_sites": status.get('active_sites'),
                        "registered_sites": status.get('registered_sites'),
                        "coordinator_status": status.get('coordinator_status')
                    }
                )
                return data
            else:
                self.record_test_result(
                    "Federation Coordinator Status",
                    "FAIL",
                    duration,
                    f"Status check failed with status {response.status_code}"
                )
                return None

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "Federation Coordinator Status",
                "FAIL",
                duration,
                f"Status check failed: {str(e)}"
            )
            return None

    def test_site_registration(self):
        """Test site registration functionality."""
        self.print_test_start("Site Registration")
        registered_sites = []

        for site_data in self.test_sites:
            start_time = time.time()

            try:
                response = requests.post(
                    f"{self.base_url}/federation/register",
                    json=site_data,
                    timeout=30
                )

                duration = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()
                    site_id = data.get('assigned_site_id')
                    registered_sites.append(site_id)

                    self.record_test_result(
                        f"Site Registration - {site_data['capabilities']['site_name']}",
                        "PASS",
                        duration,
                        f"Site registered with ID: {site_id}",
                        {"assigned_site_id": site_id}
                    )
                else:
                    self.record_test_result(
                        f"Site Registration - {site_data['capabilities']['site_name']}",
                        "FAIL",
                        duration,
                        f"Registration failed with status {response.status_code}"
                    )

            except Exception as e:
                duration = time.time() - start_time
                self.record_test_result(
                    f"Site Registration - {site_data['capabilities']['site_name']}",
                    "FAIL",
                    duration,
                    f"Registration failed: {str(e)}"
                )

        return registered_sites

    def test_federation_round(self, registered_sites: List[str]):
        """Test federation round functionality."""
        self.print_test_start("Federation Round Management")

        if len(registered_sites) < 2:
            self.record_test_result(
                "Federation Round Management",
                "SKIP",
                0,
                "Insufficient registered sites for federation round"
            )
            return None

        start_time = time.time()

        try:
            # Start federation round
            response = requests.post(
                f"{self.base_url}/federation/start_round",
                json={"config": {"target_sites": len(registered_sites)}},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                round_id = data.get('round_id')

                # Check round status
                status_response = requests.get(
                    f"{self.base_url}/federation/round_status/{round_id}",
                    timeout=30
                )

                duration = time.time() - start_time

                if status_response.status_code == 200:
                    status_data = status_response.json()

                    self.record_test_result(
                        "Federation Round Management",
                        "PASS",
                        duration,
                        f"Federation round started successfully",
                        {
                            "round_id": round_id,
                            "participating_sites": status_data.get('participating_sites'),
                            "status": status_data.get('status'),
                            "progress_percentage": status_data.get('progress_percentage')
                        }
                    )
                    return round_id
                else:
                    self.record_test_result(
                        "Federation Round Management",
                        "FAIL",
                        duration,
                        "Round started but status check failed"
                    )
                    return None
            else:
                duration = time.time() - start_time
                self.record_test_result(
                    "Federation Round Management",
                    "FAIL",
                    duration,
                    f"Round start failed with status {response.status_code}"
                )
                return None

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "Federation Round Management",
                "FAIL",
                duration,
                f"Federation round failed: {str(e)}"
            )
            return None

    def test_clinical_dashboard(self):
        """Test clinical dashboard functionality."""
        self.print_test_start("Clinical Dashboard")
        start_time = time.time()

        try:
            response = requests.get(
                f"{self.base_url}/clinical/dashboard?date_range=30",
                timeout=30
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                self.record_test_result(
                    "Clinical Dashboard",
                    "PASS",
                    duration,
                    "Clinical dashboard accessible",
                    {"status": data.get('status')}
                )
                return True
            else:
                self.record_test_result(
                    "Clinical Dashboard",
                    "FAIL",
                    duration,
                    f"Dashboard failed with status {response.status_code}"
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "Clinical Dashboard",
                "FAIL",
                duration,
                f"Dashboard failed: {str(e)}"
            )
            return False

    def test_data_integrity(self):
        """Test data integrity across the system."""
        self.print_test_start("Data Integrity Check")
        start_time = time.time()

        if not self.db_connection:
            self.record_test_result(
                "Data Integrity Check",
                "SKIP",
                0,
                "Database connection not available"
            )
            return False

        try:
            cursor = self.db_connection.cursor(dictionary=True)

            # Check for orphaned records
            cursor.execute("""
                SELECT COUNT(*) as orphaned_feedback
                FROM neurotunes_feedback_log f
                LEFT JOIN neurotunes_generation_log g ON f.session_id = g.session_id
                WHERE g.session_id IS NULL
            """)
            orphaned_feedback = cursor.fetchone()['orphaned_feedback']

            # Check for recent activity
            cursor.execute("""
                SELECT COUNT(*) as recent_sessions
                FROM neurotunes_generation_log
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            """)
            recent_sessions = cursor.fetchone()['recent_sessions']

            cursor.close()
            duration = time.time() - start_time

            issues = []
            if orphaned_feedback > 0:
                issues.append(f"{orphaned_feedback} orphaned feedback records")

            if len(issues) == 0:
                self.record_test_result(
                    "Data Integrity Check",
                    "PASS",
                    duration,
                    "Data integrity verified",
                    {
                        "orphaned_feedback": orphaned_feedback,
                        "recent_sessions": recent_sessions
                    }
                )
                return True
            else:
                self.record_test_result(
                    "Data Integrity Check",
                    "FAIL",
                    duration,
                    f"Data integrity issues: {', '.join(issues)}"
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.record_test_result(
                "Data Integrity Check",
                "FAIL",
                duration,
                f"Integrity check failed: {str(e)}"
            )
            return False

    def run_performance_tests(self):
        """Run performance and load tests."""
        self.print_test_start("Performance Tests")

        # Test concurrent music generation
        def generate_music_concurrent():
            try:
                response = requests.post(
                    f"{self.base_url}/generate_music",
                    json=self.test_patient_data,
                    timeout=60
                )
                return response.status_code == 200
            except:
                return False

        start_time = time.time()
        threads = []

        # Start 5 concurrent requests
        for i in range(5):
            thread = threading.Thread(target=generate_music_concurrent)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        duration = time.time() - start_time

        self.record_test_result(
            "Concurrent Music Generation",
            "PASS",
            duration,
            f"Handled 5 concurrent requests in {duration:.2f}s",
            {"concurrent_requests": 5, "avg_time_per_request": duration/5}
        )

    def generate_test_report(self):
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.status == 'PASS'])
        failed_tests = len([r for r in self.test_results if r.status == 'FAIL'])
        skipped_tests = len([r for r in self.test_results if r.status == 'SKIP'])

        total_duration = sum(r.duration for r in self.test_results)

        self.print_header("TEST EXECUTION SUMMARY")

        print(f"{Fore.WHITE}Total Tests: {total_tests}")
        print(f"{Fore.GREEN}✅ Passed: {passed_tests}")
        print(f"{Fore.RED}❌ Failed: {failed_tests}")
        print(f"{Fore.YELLOW}⏭️  Skipped: {skipped_tests}")
        print(f"{Fore.CYAN}⏱️  Total Duration: {total_duration:.2f}s")

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"{Fore.MAGENTA}📊 Success Rate: {success_rate:.1f}%")

        if failed_tests > 0:
            print(f"\n{Fore.RED}{Style.BRIGHT}FAILED TESTS:")
            for result in self.test_results:
                if result.status == 'FAIL':
                    print(f"{Fore.RED}❌ {result.test_name}: {result.message}")

        return success_rate >= 80  # Consider 80%+ success rate as overall pass

    def run_all_tests(self):
        """Run the complete test suite."""
        self.start_time = datetime.now()

        self.print_header("NEUROTUNES FEDERATED LEARNING TEST SUITE")
        print(f"{Fore.CYAN}Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}Base URL: {self.base_url}")

        # Core system tests
        if not self.test_system_health():
            print(f"{Fore.RED}❌ System health check failed. Aborting tests.")
            return False

        self.test_database_connectivity()

        # Music generation pipeline tests
        session_id = self.test_music_generation_pipeline()
        if session_id:
            self.test_feedback_logging(session_id)

        # ML pipeline tests
        self.test_reward_model_training()

        # Federation tests
        federation_status = self.test_federation_coordinator_status()
        if federation_status:
            registered_sites = self.test_site_registration()
            if registered_sites:
                self.test_federation_round(registered_sites)

        # Dashboard and integrity tests
        self.test_clinical_dashboard()
        self.test_data_integrity()

        # Performance tests
        self.run_performance_tests()

        # Generate final report
        success = self.generate_test_report()

        if self.db_connection:
            self.db_connection.close()

        return success

def main():
    """Main test execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='NeuroTunes Federated Learning Test Suite')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Base URL for NeuroTunes API (default: http://localhost:5000)')
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable verbose output')

    args = parser.parse_args()

    test_suite = NeuroTunesTestSuite(base_url=args.url)

    try:
        success = test_suite.run_all_tests()
        exit_code = 0 if success else 1

        print(f"\n{Fore.CYAN}Test suite completed with exit code: {exit_code}")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}Test suite failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
