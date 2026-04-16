"""
Applied Jobs Tracker - Prevents duplicate applications.
"""
import json
from pathlib import Path
from datetime import datetime
from config import APPLIED_JOBS_PATH


def load_applied_jobs() -> dict:
    """Load the applied jobs database."""
    if APPLIED_JOBS_PATH.exists():
        with open(APPLIED_JOBS_PATH, 'r') as f:
            return json.load(f)
    return {"jobs": [], "stats": {"total": 0, "successful": 0, "failed": 0}}


def save_applied_jobs(data: dict):
    """Save the applied jobs database."""
    with open(APPLIED_JOBS_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def is_already_applied(url: str) -> bool:
    """Check if we've already applied to this job."""
    data = load_applied_jobs()
    applied_urls = {job["url"] for job in data["jobs"]}
    return url in applied_urls


def record_application(
    url: str,
    job_title: str,
    company: str,
    platform: str,
    success: bool,
    message: str = ""
):
    """Record a job application attempt."""
    data = load_applied_jobs()
    
    job_record = {
        "url": url,
        "job_title": job_title,
        "company": company,
        "platform": platform,
        "success": success,
        "message": message,
        "applied_at": datetime.now().isoformat()
    }
    
    data["jobs"].append(job_record)
    data["stats"]["total"] += 1
    if success:
        data["stats"]["successful"] += 1
    else:
        data["stats"]["failed"] += 1
    
    save_applied_jobs(data)
    
    status = "✓" if success else "✗"
    print(f"{status} {job_title} at {company} - {message}")


def get_applied_urls() -> set:
    """Get set of all URLs we've applied to."""
    data = load_applied_jobs()
    return {job["url"] for job in data["jobs"]}


def get_stats() -> dict:
    """Get application statistics."""
    data = load_applied_jobs()
    return data["stats"]


def print_summary():
    """Print a summary of applications."""
    data = load_applied_jobs()
    stats = data["stats"]
    
    print("\n" + "=" * 50)
    print("APPLICATION SUMMARY")
    print("=" * 50)
    print(f"Total Applications: {stats['total']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    
    if stats['total'] > 0:
        success_rate = (stats['successful'] / stats['total']) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    
    print("=" * 50)
    
    # Recent applications
    if data["jobs"]:
        print("\nRecent Applications:")
        for job in data["jobs"][-5:]:
            status = "✓" if job["success"] else "✗"
            print(f"  {status} {job['job_title']} at {job['company']}")


if __name__ == "__main__":
    print_summary()
